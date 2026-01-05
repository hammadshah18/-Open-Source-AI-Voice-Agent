"""
Audio Stream Handler
Manages audio streaming, buffering, and silence detection for calls
"""
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


class AudioStreamHandler:
    """
    Handles audio streaming for a call
    Manages buffering, silence detection, and audio file storage
    """
    
    def __init__(self, channel_id: str, audio_dir: Path):
        self.channel_id = channel_id
        self.audio_dir = audio_dir
        
        # Audio parameters (matching Asterisk slin16 format)
        self.sample_rate = 16000  # 16kHz
        self.channels = 1  # Mono
        self.sample_width = 2  # 16-bit
        
        # Buffering
        self.audio_buffer = []
        self.is_recording = False
        
        # Silence detection
        self.silence_threshold = 0.02
        self.silence_duration = 2.0  # seconds
        self.silence_frames = 0
        
        logger.debug(f"AudioStreamHandler initialized for channel {channel_id}")
    
    async def start_capture(self):
        """Start capturing audio from the channel"""
        self.is_recording = True
        self.audio_buffer = []
        self.silence_frames = 0
        logger.info(f"Started audio capture for channel {self.channel_id}")
    
    async def stop_capture(self) -> Optional[str]:
        """Stop capturing and save audio file"""
        self.is_recording = False
        
        if not self.audio_buffer:
            logger.warning("No audio data captured")
            return None
        
        try:
            # Save buffer to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.audio_dir / f"captured_{self.channel_id}_{timestamp}.wav"
            
            # Convert buffer to audio file
            audio_data = np.concatenate(self.audio_buffer)
            
            # Save as WAV
            import soundfile as sf
            sf.write(
                str(filename),
                audio_data,
                self.sample_rate,
                subtype='PCM_16'
            )
            
            logger.info(f"✓ Audio saved: {filename} ({len(audio_data)/self.sample_rate:.1f}s)")
            
            # Clear buffer
            self.audio_buffer = []
            
            return str(filename)
            
        except Exception as e:
            logger.error(f"Error saving audio: {e}", exc_info=True)
            return None
    
    async def process_audio_frame(self, audio_data: bytes):
        """Process incoming audio frame from Asterisk"""
        if not self.is_recording:
            return
        
        try:
            # Convert bytes to numpy array (16-bit PCM)
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            
            # Add to buffer
            self.audio_buffer.append(audio_array)
            
            # Check for silence
            if self._is_silence(audio_array):
                self.silence_frames += 1
            else:
                self.silence_frames = 0
            
            # Calculate silence duration
            frames_per_second = self.sample_rate / len(audio_array)
            silence_duration = self.silence_frames / frames_per_second
            
            # If silence detected for configured duration, stop recording
            if silence_duration >= self.silence_duration:
                logger.info(f"Silence detected ({silence_duration:.1f}s), stopping capture")
                audio_file = await self.stop_capture()
                return audio_file
            
        except Exception as e:
            logger.error(f"Error processing audio frame: {e}")
        
        return None
    
    def _is_silence(self, audio_data: np.ndarray) -> bool:
        """Check if audio frame is silence"""
        return np.abs(audio_data).mean() < self.silence_threshold
    
    async def cleanup(self):
        """Cleanup resources"""
        self.is_recording = False
        self.audio_buffer = []
        logger.debug(f"AudioStreamHandler cleaned up for channel {self.channel_id}")


class AudioFileConverter:
    """
    Utility for converting audio files between formats
    Ensures compatibility with Asterisk and TTS/STT engines
    """
    
    @staticmethod
    async def convert_to_asterisk_format(input_file: str, output_file: str):
        """
        Convert audio file to Asterisk-compatible format
        Output: 16kHz, 16-bit, mono WAV (slin16)
        """
        try:
            import soundfile as sf
            import numpy as np
            from scipy import signal
            
            # Read input file
            audio_data, sample_rate = sf.read(input_file)
            
            # Convert to mono if stereo
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)
            
            # Resample to 16kHz if needed
            if sample_rate != 16000:
                num_samples = int(len(audio_data) * 16000 / sample_rate)
                audio_data = signal.resample(audio_data, num_samples)
            
            # Normalize to prevent clipping
            audio_data = audio_data / np.abs(audio_data).max() if np.abs(audio_data).max() > 0 else audio_data
            
            # Save in Asterisk format
            sf.write(
                output_file,
                audio_data,
                16000,
                subtype='PCM_16',
                format='WAV'
            )
            
            logger.info(f"✓ Converted audio to Asterisk format: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error converting audio: {e}", exc_info=True)
            return False
    
    @staticmethod
    async def convert_tts_to_asterisk(tts_file: str, output_file: str):
        """
        Convert TTS output (22kHz) to Asterisk format (16kHz)
        """
        return await AudioFileConverter.convert_to_asterisk_format(tts_file, output_file)
