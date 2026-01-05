"""
Coqui TTS Integration for Text-to-Speech
Uses XTTS v2 model for natural speech synthesis
Audio output is compatible with Asterisk/Freeswitch telephony systems
"""

from TTS.api import TTS
from pathlib import Path
from typing import Optional, List
import torch
from ..logger import logger
from ..config import LOG_DIR
import os

# Allow loading TTS models (we trust Coqui official models)
os.environ['TORCH_FORCE_WEIGHTS_ONLY_LOAD'] = '0'

# Check if GPU is available
device = "cuda" if torch.cuda.is_available() else "cpu"

# Initialize TTS model once at startup (singleton pattern)
# Using XTTS v2 for high-quality multilingual speech
_tts_model = None

def get_tts_model():
    """
    Lazy load TTS model to avoid startup delay if not needed
    """
    global _tts_model
    if _tts_model is None:
        logger.info("Loading Coqui TTS model...")
        try:
            # Use Tacotron2-DDC - single speaker, no voice cloning needed, English only
            # Simpler and faster for basic TTS without multilingual support
            _tts_model = TTS("tts_models/en/ljspeech/tacotron2-DDC").to(device)
            logger.info(f"TTS model (Tacotron2-DDC English) loaded successfully on {device}")
        except Exception as e:
            logger.error(f"Failed to load TTS model: {e}")
            raise
    return _tts_model


def synthesize_speech(
    text: str, 
    output_filename: Optional[str] = None,
    speaker_wav: Optional[str] = None,
    language: str = "en"
) -> Path:
    """
    Convert text to speech and save as audio file.
    
    Args:
        text (str): Text to convert to speech
        output_filename (str): Custom filename for output audio (optional)
        speaker_wav (str): Path to reference speaker audio for voice cloning (optional)
        language (str): Language code (default: "en" for English)
        
    Returns:
        Path: Path to the generated audio file
        
    Audio format: WAV, 22050Hz, mono (compatible with Asterisk)
    """
    logger.info(f"Starting TTS synthesis for text: {text[:50]}...")
    
    try:
        # Get TTS model
        tts = get_tts_model()
        
        # Generate output filename if not provided
        if output_filename is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"tts_output_{timestamp}.wav"
        
        # Ensure it has .wav extension for Asterisk compatibility
        if not output_filename.endswith('.wav'):
            output_filename += '.wav'
        
        # Handle absolute vs relative paths
        output_path = Path(output_filename)
        if not output_path.is_absolute():
            # Save to logs directory if relative path
            output_path = LOG_DIR / output_filename
        
        # Create parent directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate speech (single speaker model)
        logger.info(f"Generating speech...")
        tts.tts_to_file(
            text=text,
            file_path=str(output_path)
        )
        
        logger.info(f"TTS synthesis completed. Audio saved to: {output_path}")
        
        # Verify file was created
        if not output_path.exists():
            raise FileNotFoundError(f"TTS output file was not created: {output_path}")
        
        file_size = output_path.stat().st_size
        logger.info(f"Audio file size: {file_size} bytes")
        
        return output_path
        
    except Exception as e:
        logger.error(f"Error during TTS synthesis: {e}")
        raise Exception(f"TTS synthesis failed: {str(e)}")


def text_to_audio_stream(text: str, speaker_wav: Optional[str] = None, language: str = "en"):
    """
    Convert text to audio and return as bytes for streaming.
    Useful for real-time applications and telephony.
    
    Args:
        text (str): Text to convert to speech
        speaker_wav (str): Path to reference speaker audio (optional)
        language (str): Language code
        
    Returns:
        bytes: Audio data in WAV format
    """
    try:
        # Generate audio file
        audio_path = synthesize_speech(text, speaker_wav=speaker_wav, language=language)
        
        # Read file as bytes
        with open(audio_path, 'rb') as audio_file:
            audio_bytes = audio_file.read()
        
        logger.info(f"Audio converted to bytes stream: {len(audio_bytes)} bytes")
        
        return audio_bytes
        
    except Exception as e:
        logger.error(f"Error creating audio stream: {e}")
        raise


def batch_synthesize(texts: List[str], output_dir: Optional[Path] = None) -> List[Path]:
    """
    Synthesize multiple texts in batch.
    Useful for pre-generating common responses.
    
    Args:
        texts (list): List of text strings to synthesize
        output_dir (Path): Directory to save audio files (default: LOG_DIR)
        
    Returns:
        list: List of Paths to generated audio files
    """
    if output_dir is None:
        output_dir = LOG_DIR
    
    output_files = []
    logger.info(f"Starting batch TTS synthesis for {len(texts)} texts")
    
    for idx, text in enumerate(texts):
        try:
            filename = f"batch_tts_{idx+1}.wav"
            audio_path = synthesize_speech(text, output_filename=filename)
            output_files.append(audio_path)
        except Exception as e:
            logger.error(f"Failed to synthesize text {idx+1}: {e}")
            output_files.append(None)
    
    logger.info(f"Batch synthesis completed. {len([f for f in output_files if f])} successful")
    
    return output_files


# Preload model on import if environment variable is set
if os.getenv("PRELOAD_TTS", "false").lower() == "true":
    logger.info("Preloading TTS model as per PRELOAD_TTS environment variable")
    get_tts_model()
