"""
Streaming STT Service using faster-whisper
Processes audio chunks in real-time for low-latency transcription
"""
import asyncio
import logging
from typing import Optional, Callable
import numpy as np
from faster_whisper import WhisperModel
import io
import wave

logger = logging.getLogger(__name__)


class StreamingSTT:
    """
    Real-time Speech-to-Text using faster-whisper
    Processes audio streams with voice activity detection
    """
    
    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        on_transcript: Optional[Callable] = None,
        vad_threshold: float = 0.5,
        silence_duration: float = 1.0
    ):
        self.model = None
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.on_transcript = on_transcript
        self.vad_threshold = vad_threshold
        self.silence_duration = silence_duration
        
        # Audio buffer (slin16: 16kHz, 16-bit, mono)
        self.audio_buffer = bytearray()
        self.sample_rate = 16000
        self.is_speaking = False
        self.silence_start = None
        
        # Processing state
        self.processing = False
        self.last_transcript = ""
        
        logger.info(f"Streaming STT initialized with model: {model_size}")
    
    async def initialize(self):
        """Load Whisper model (do this once at startup)"""
        try:
            logger.info("Loading Whisper model (this may take a moment on first run)...")
            # Use tiny model for faster startup - you can change to 'base' or 'small' later
            self.model = WhisperModel(
                "tiny",  # Fast startup, adequate for testing
                device=self.device,
                compute_type=self.compute_type
            )
            logger.info("✓ Whisper model loaded")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            logger.warning("STT will use mock transcription")
            self.model = None  # Graceful degradation
    
    async def process_audio_chunk(self, audio_chunk: bytes):
        """
        Process incoming audio chunk
        Detects speech and triggers transcription when silence is detected
        """
        # Add chunk to buffer
        self.audio_buffer.extend(audio_chunk)
        
        # Simple VAD: detect if audio has energy
        audio_energy = self._calculate_energy(audio_chunk)
        
        if audio_energy > self.vad_threshold:
            # Speech detected
            if not self.is_speaking:
                logger.debug("Speech started")
                self.is_speaking = True
            self.silence_start = None
        else:
            # Silence detected
            if self.is_speaking:
                if self.silence_start is None:
                    self.silence_start = asyncio.get_event_loop().time()
                else:
                    # Check if silence duration exceeded
                    silence_elapsed = asyncio.get_event_loop().time() - self.silence_start
                    if silence_elapsed >= self.silence_duration:
                        # End of utterance - transcribe
                        await self._transcribe_buffer()
                        self.is_speaking = False
                        self.silence_start = None
    
    def _calculate_energy(self, audio_chunk: bytes) -> float:
        """Calculate audio energy for simple VAD"""
        try:
            # Convert bytes to numpy array (16-bit PCM)
            audio_array = np.frombuffer(audio_chunk, dtype=np.int16)
            # Calculate RMS energy
            energy = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
            # Normalize to 0-1 range
            return min(energy / 3000.0, 1.0)
        except Exception as e:
            logger.error(f"Error calculating energy: {e}")
            return 0.0
    
    async def _transcribe_buffer(self):
        """Transcribe accumulated audio buffer"""
        if self.processing or len(self.audio_buffer) < 16000:  # Min 1 second
            return
        
        self.processing = True
        
        try:
            if not self.model:
                logger.warning("STT model not loaded")
                return
            
            # Convert buffer to numpy array
            audio_array = np.frombuffer(bytes(self.audio_buffer), dtype=np.int16)
            audio_float = audio_array.astype(np.float32) / 32768.0  # Normalize to [-1, 1]
            
            # Run transcription in thread pool
            segments, info = await asyncio.to_thread(
                self.model.transcribe,
                audio_float,
                beam_size=1,  # Faster but less accurate
                language="en",
                vad_filter=True,
                vad_parameters=dict(
                    threshold=self.vad_threshold,
                    min_speech_duration_ms=250,
                    min_silence_duration_ms=500
                )
            )
            
            # Collect transcript
            transcript_parts = []
            for segment in segments:
                text = segment.text.strip()
                if text:
                    transcript_parts.append(text)
            
            transcript = " ".join(transcript_parts)
            
            if transcript and transcript != self.last_transcript:
                logger.info(f"👤 Transcribed: {transcript}")
                self.last_transcript = transcript
                
                # Trigger callback
                if self.on_transcript:
                    await self.on_transcript(transcript)
            
            # Clear buffer after transcription
            self.audio_buffer.clear()
            
        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
        finally:
            self.processing = False
    
    async def force_transcribe(self):
        """Force transcription of current buffer (e.g., on call end)"""
        if len(self.audio_buffer) > 0:
            await self._transcribe_buffer()
    
    def reset(self):
        """Reset STT state for new conversation"""
        self.audio_buffer.clear()
        self.is_speaking = False
        self.silence_start = None
        self.last_transcript = ""
        logger.debug("STT state reset")
