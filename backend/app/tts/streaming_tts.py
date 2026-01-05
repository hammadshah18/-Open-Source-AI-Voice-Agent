"""
Streaming TTS Service with Coqui TTS
Converts text to speech in real-time with chunked output
"""
import asyncio
import logging
from typing import Optional, Callable
from pathlib import Path
import io
import wave
import numpy as np
try:
    from TTS.api import TTS
except ImportError:
    TTS = None  # TTS optional for testing

logger = logging.getLogger(__name__)


class StreamingTTS:
    """
    Real-time Text-to-Speech with streaming output
    Generates audio as text arrives from LLM
    """
    
    def __init__(
        self,
        model_name: str = "tts_models/en/ljspeech/tacotron2-DDC",
        on_audio_chunk: Optional[Callable] = None
    ):
        self.model_name = model_name
        self.on_audio_chunk = on_audio_chunk
        self.tts = None
        
        # Audio output settings
        self.sample_rate = 16000  # Match media WebSocket
        
        logger.info(f"Streaming TTS initialized with model: {model_name}")
    
    async def initialize(self):
        """Load TTS model (do this once at startup)"""
        try:
            if TTS is None:
                raise ImportError("TTS library not installed")
            
            logger.info("Loading TTS model...")
            self.tts = TTS(self.model_name)
            logger.info("✓ TTS model loaded")
        except Exception as e:
            logger.error(f"Failed to load TTS model: {e}")
            logger.warning("TTS will use mock audio")
    
    async def synthesize_stream(
        self,
        text_stream,
        output_dir: Optional[Path] = None
    ):
        """
        Synthesize speech from streaming text
        Yields audio chunks as they're generated
        
        Args:
            text_stream: Async iterator of text chunks
            output_dir: Optional directory to save audio files
        """
        # Buffer text until we have a complete sentence or clause
        text_buffer = ""
        sentence_enders = ['.', '!', '?', '\n']
        
        try:
            async for text_chunk in text_stream:
                text_buffer += text_chunk
                
                # Check if we have a complete sentence
                should_synthesize = any(
                    ender in text_buffer for ender in sentence_enders
                )
                
                if should_synthesize or len(text_buffer) > 100:
                    # Synthesize accumulated text
                    audio_data = await self._synthesize_chunk(text_buffer.strip())
                    
                    if audio_data and self.on_audio_chunk:
                        await self.on_audio_chunk(audio_data)
                    
                    # Save to file if requested
                    if output_dir and audio_data:
                        await self._save_audio(audio_data, output_dir, text_buffer[:30])
                    
                    # Clear buffer
                    text_buffer = ""
            
            # Synthesize any remaining text
            if text_buffer.strip():
                audio_data = await self._synthesize_chunk(text_buffer.strip())
                if audio_data and self.on_audio_chunk:
                    await self.on_audio_chunk(audio_data)
                    
        except Exception as e:
            logger.error(f"TTS streaming error: {e}", exc_info=True)
    
    async def _synthesize_chunk(self, text: str) -> Optional[bytes]:
        """
        Synthesize a single text chunk to audio
        Returns raw audio bytes (16kHz, 16-bit, mono PCM)
        """
        if not text:
            return None
        
        try:
            if not self.tts:
                # Mock audio for testing (silence)
                return self._generate_silence(duration=1.0)
            
            # Run TTS in thread pool (blocking operation)
            audio_array = await asyncio.to_thread(
                self.tts.tts,
                text=text
            )
            
            # Convert to bytes (16-bit PCM)
            if isinstance(audio_array, list):
                audio_array = np.array(audio_array)
            audio_int16 = (audio_array * 32767).astype(np.int16)
            audio_bytes = audio_int16.tobytes()
            
            logger.debug(f"Synthesized: {text[:50]}...")
            return audio_bytes
            
        except Exception as e:
            logger.error(f"TTS synthesis error: {e}", exc_info=True)
            return None
    
    def _generate_silence(self, duration: float) -> bytes:
        """Generate silence for given duration"""
        import numpy as np
        num_samples = int(self.sample_rate * duration)
        silence = np.zeros(num_samples, dtype=np.int16)
        return silence.tobytes()
    
    async def _save_audio(self, audio_data: bytes, output_dir: Path, prefix: str):
        """Save audio data to WAV file"""
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create filename from prefix
            safe_prefix = "".join(c for c in prefix if c.isalnum() or c in (' ', '_'))
            filename = output_dir / f"tts_{safe_prefix[:30]}.wav"
            
            # Write WAV file
            with wave.open(str(filename), 'wb') as wav:
                wav.setnchannels(1)  # Mono
                wav.setsampwidth(2)  # 16-bit
                wav.setframerate(self.sample_rate)
                wav.writeframes(audio_data)
            
            logger.debug(f"Saved TTS audio: {filename}")
            
        except Exception as e:
            logger.error(f"Error saving TTS audio: {e}")
    
    async def synthesize_file(self, text: str, output_path: str) -> bool:
        """
        Synthesize text to a complete WAV file (non-streaming)
        For backwards compatibility with existing code
        """
        try:
            if not self.tts:
                logger.warning("TTS model not loaded")
                return False
            
            # Run TTS
            audio_array = await asyncio.to_thread(
                self.tts.tts,
                text=text
            )
            
            # Save to file
            if isinstance(audio_array, list):
                audio_array = np.array(audio_array)
            audio_int16 = (audio_array * 32767).astype(np.int16)
            
            with wave.open(output_path, 'wb') as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(self.sample_rate)
                wav.writeframes(audio_int16.tobytes())
            
            logger.info(f"✓ TTS saved: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"TTS file generation error: {e}", exc_info=True)
            return False
