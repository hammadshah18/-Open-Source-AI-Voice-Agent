from faster_whisper import WhisperModel
from ..logger import logger

# Load model once at startup
model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"  # reduces RAM usage
)

def transcribe_audio(audio_path: str) -> str:
    """
    Transcribes an audio file and returns text.
    """
    logger.info(f"Starting transcription for file: {audio_path}")

    segments, info = model.transcribe(audio_path)

    transcript = ""
    for segment in segments:
        transcript += segment.text.strip() + " "

    transcript = transcript.strip()

    logger.info(f"Transcription completed: {transcript}")

    return transcript
