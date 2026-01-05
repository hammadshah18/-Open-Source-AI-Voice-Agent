"""
Telephony Session Manager
Manages real-time call sessions, audio streaming, and barge-in
"""
import asyncio
import numpy as np
from typing import Optional, Dict, Any, List
from datetime import datetime
from fastapi import WebSocket
from ..logger import logger
from ..stt.whisper_stt import transcribe_audio
from ..llm.dialog_manager import generate_response
from ..tts.coqui_tts import get_tts_model
from ..rag.vector_store import RAGSystem
from ..config import COMPANIES_DIR, RAG_ENABLED
from pathlib import Path
import io
import wave
import struct


class TelephonySession:
    """
    Manages a single phone call session with real-time audio processing
    """
    
    def __init__(
        self,
        channel_id: str,
        caller_number: str,
        company_id: str,
        websocket: WebSocket
    ):
        self.channel_id = channel_id
        self.caller_number = caller_number
        self.company_id = company_id
        self.websocket = websocket
        
        # Session state
        self.start_time = datetime.now()
        self.conversation_history: List[Dict[str, str]] = []
        self.is_playing = False
        self.should_stop_playback = False
        
        # Audio buffers
        self.incoming_audio_buffer = bytearray()
        self.sample_rate = 8000  # Asterisk default for slin
        self.chunk_duration_ms = 20  # 20ms chunks
        self.samples_per_chunk = int(self.sample_rate * self.chunk_duration_ms / 1000)
        
        # Voice Activity Detection (VAD) for barge-in
        self.vad_threshold = 500  # Energy threshold for detecting speech
        self.silence_frames = 0
        self.speech_frames = 0
        self.min_speech_frames = 3  # Require 3 consecutive frames to detect speech
        
        # TTS streaming
        self.tts_queue = asyncio.Queue()
        self.tts_task: Optional[asyncio.Task] = None
        
        logger.info(f"📞 Created telephony session: {channel_id} (Caller: {caller_number}, Company: {company_id})")
    
    async def start(self):
        """
        Start the telephony session tasks
        """
        # Send welcome message
        await self.speak("Hello! Welcome to our AI voice assistant. How can I help you today?")
        
        # Start TTS playback task
        self.tts_task = asyncio.create_task(self.tts_playback_loop())
    
    async def handle_audio_frame(self, audio_data: bytes):
        """
        Process incoming audio frame from caller
        
        Args:
            audio_data: Raw PCM audio bytes (16-bit signed linear, 8kHz)
        """
        # Add to buffer
        self.incoming_audio_buffer.extend(audio_data)
        
        # Check for voice activity (barge-in detection)
        if self.is_playing:
            energy = self.calculate_audio_energy(audio_data)
            
            if energy > self.vad_threshold:
                self.speech_frames += 1
                self.silence_frames = 0
                
                # Barge-in detected!
                if self.speech_frames >= self.min_speech_frames:
                    await self.handle_barge_in()
            else:
                self.silence_frames += 1
                if self.silence_frames > 5:
                    self.speech_frames = 0
        
        # Process buffer when we have enough audio (e.g., 3 seconds)
        buffer_duration = len(self.incoming_audio_buffer) / (self.sample_rate * 2)  # 2 bytes per sample
        
        if buffer_duration >= 3.0:
            await self.process_speech_buffer()
    
    def calculate_audio_energy(self, audio_data: bytes) -> float:
        """
        Calculate audio energy for VAD
        """
        # Convert bytes to numpy array
        samples = np.frombuffer(audio_data, dtype=np.int16)
        
        # Calculate RMS energy
        energy = np.sqrt(np.mean(samples.astype(np.float32) ** 2))
        
        return energy
    
    async def handle_barge_in(self):
        """
        Handle caller interruption (barge-in)
        """
        if not self.is_playing:
            return
        
        logger.info(f"🛑 Barge-in detected on {self.channel_id}")
        
        # Stop current playback immediately
        self.should_stop_playback = True
        self.is_playing = False
        
        # Clear TTS queue
        while not self.tts_queue.empty():
            try:
                self.tts_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        # Send stop signal to client
        await self.websocket.send_json({
            "type": "stop_playback",
            "reason": "barge_in"
        })
        
        # Reset speech detection
        self.speech_frames = 0
        self.silence_frames = 0
    
    async def process_speech_buffer(self):
        """
        Process accumulated speech buffer through STT → LLM → TTS
        """
        if len(self.incoming_audio_buffer) == 0:
            return
        
        try:
            # Convert buffer to WAV format for Whisper
            audio_wav = self.buffer_to_wav(self.incoming_audio_buffer)
            
            # Save temporarily for STT
            temp_audio_path = f"/tmp/call_{self.channel_id}_{datetime.now().timestamp()}.wav"
            with open(temp_audio_path, "wb") as f:
                f.write(audio_wav)
            
            logger.info(f"🎤 Processing speech from {self.caller_number}")
            
            # STT: Transcribe
            transcript = transcribe_audio(temp_audio_path)
            
            if not transcript or len(transcript.strip()) < 3:
                logger.info("No speech detected in buffer")
                self.incoming_audio_buffer.clear()
                return
            
            logger.info(f"📝 Transcript: {transcript}")
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": transcript,
                "timestamp": datetime.now().isoformat()
            })
            
            # LLM: Generate response (with RAG)
            response_text = generate_response(
                user_text=transcript,
                company_id=self.company_id
            )
            
            logger.info(f"🤖 AI Response: {response_text}")
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.now().isoformat()
            })
            
            # TTS: Speak response
            await self.speak(response_text)
            
            # Clear buffer
            self.incoming_audio_buffer.clear()
        
        except Exception as e:
            logger.error(f"Error processing speech buffer: {e}")
            await self.speak("I'm sorry, I didn't catch that. Could you please repeat?")
            self.incoming_audio_buffer.clear()
    
    def buffer_to_wav(self, audio_buffer: bytearray) -> bytes:
        """
        Convert PCM buffer to WAV format
        """
        wav_buffer = io.BytesIO()
        
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(bytes(audio_buffer))
        
        return wav_buffer.getvalue()
    
    async def speak(self, text: str):
        """
        Generate speech and queue for playback
        
        Args:
            text: Text to convert to speech
        """
        try:
            logger.info(f"🔊 Generating TTS: {text[:50]}...")
            
            # Get TTS model
            tts = get_tts_model()
            
            # Generate speech
            # For XTTS v2, we need speaker audio. Using default for now.
            audio_result = tts.tts(text=text)
            
            # Convert to numpy array if it's a list
            if isinstance(audio_result, list):
                audio_array = np.array(audio_result, dtype=np.float32)
            else:
                audio_array = audio_result
            
            # Get sample rate from TTS
            tts_sample_rate = getattr(tts.synthesizer, 'output_sample_rate', 22050)
            
            # Convert to 8kHz (Asterisk requirement) and 16-bit PCM
            audio_resampled = self.resample_audio(audio_array, tts_sample_rate, self.sample_rate)
            
            # Convert to bytes
            audio_bytes = self.numpy_to_pcm_bytes(audio_resampled)
            
            # Queue for streaming
            await self.tts_queue.put(audio_bytes)
            
        except Exception as e:
            logger.error(f"Error generating TTS: {e}")
    
    def resample_audio(self, audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """
        Resample audio to target sample rate
        """
        from scipy import signal
        
        # Calculate resampling ratio
        ratio = target_sr / orig_sr
        
        # Resample
        num_samples = int(len(audio) * ratio)
        resampled = signal.resample(audio, num_samples)
        
        # Ensure it's a numpy array
        if isinstance(resampled, tuple):
            resampled = resampled[0]
        
        return np.asarray(resampled, dtype=np.float32)
    
    def numpy_to_pcm_bytes(self, audio: np.ndarray) -> bytes:
        """
        Convert numpy array to 16-bit PCM bytes
        """
        # Normalize to int16 range
        audio_normalized = np.clip(audio, -1.0, 1.0)
        audio_int16 = (audio_normalized * 32767).astype(np.int16)
        
        return audio_int16.tobytes()
    
    async def tts_playback_loop(self):
        """
        Continuously stream TTS audio to caller
        """
        try:
            while True:
                # Wait for audio in queue
                audio_bytes = await self.tts_queue.get()
                
                # Mark as playing
                self.is_playing = True
                self.should_stop_playback = False
                
                # Stream in chunks
                chunk_size = self.samples_per_chunk * 2  # 2 bytes per sample
                
                for i in range(0, len(audio_bytes), chunk_size):
                    # Check if we should stop (barge-in)
                    if self.should_stop_playback:
                        logger.info("⏹️ TTS playback stopped (barge-in)")
                        break
                    
                    chunk = audio_bytes[i:i + chunk_size]
                    
                    # Send chunk to WebSocket
                    await self.websocket.send_bytes(chunk)
                    
                    # Small delay to match real-time playback
                    await asyncio.sleep(self.chunk_duration_ms / 1000.0)
                
                # Mark as not playing
                self.is_playing = False
        
        except asyncio.CancelledError:
            logger.info(f"TTS playback loop cancelled for {self.channel_id}")
        except Exception as e:
            logger.error(f"Error in TTS playback loop: {e}")
    
    async def stop(self):
        """
        Stop the session and cleanup
        """
        logger.info(f"🛑 Stopping telephony session: {self.channel_id}")
        
        # Cancel TTS task
        if self.tts_task:
            self.tts_task.cancel()
            try:
                await self.tts_task
            except asyncio.CancelledError:
                pass
        
        # Calculate session duration
        duration = (datetime.now() - self.start_time).total_seconds()
        
        # Log session summary
        logger.info(f"📊 Session Summary:")
        logger.info(f"  - Channel: {self.channel_id}")
        logger.info(f"  - Caller: {self.caller_number}")
        logger.info(f"  - Company: {self.company_id}")
        logger.info(f"  - Duration: {duration:.2f}s")
        logger.info(f"  - Exchanges: {len(self.conversation_history) // 2}")


class SessionManager:
    """
    Manages all active telephony sessions
    """
    
    def __init__(self):
        self.sessions: Dict[str, TelephonySession] = {}
    
    async def create_session(
        self,
        channel_id: str,
        caller_number: str,
        company_id: str,
        websocket: WebSocket
    ) -> TelephonySession:
        """
        Create a new telephony session
        """
        session = TelephonySession(
            channel_id=channel_id,
            caller_number=caller_number,
            company_id=company_id,
            websocket=websocket
        )
        
        self.sessions[channel_id] = session
        await session.start()
        
        return session
    
    def get_session(self, channel_id: str) -> Optional[TelephonySession]:
        """
        Get an existing session
        """
        return self.sessions.get(channel_id)
    
    async def end_session(self, channel_id: str):
        """
        End and cleanup a session
        """
        session = self.sessions.get(channel_id)
        if session:
            await session.stop()
            del self.sessions[channel_id]
    
    def get_active_sessions_count(self) -> int:
        """
        Get count of active sessions
        """
        return len(self.sessions)


# Singleton instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """
    Get or create session manager instance
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
