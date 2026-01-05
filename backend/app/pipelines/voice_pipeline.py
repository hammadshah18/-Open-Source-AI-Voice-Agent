"""
Complete Voice Pipeline
Orchestrates the full AI Voice Agent flow:
User Speech → STT → RAG → LLM → TTS → Audio Response
"""

from pathlib import Path
from typing import Optional
from ..stt.whisper_stt import transcribe_audio
from ..llm.dialog_manager import generate_response
from ..tts.coqui_tts import synthesize_speech
from ..logger import logger
from ..config import ACTIVE_COMPANY, TTS_ENABLED, RAG_ENABLED

class VoicePipeline:
    """
    Complete voice interaction pipeline
    """
    
    def __init__(self, company_id: Optional[str] = None):
        """
        Initialize pipeline with optional company specification
        
        Args:
            company_id (str): Company ID for knowledge base (uses ACTIVE_COMPANY if not provided)
        """
        self.company_id = company_id or ACTIVE_COMPANY
        logger.info(f"Initialized VoicePipeline for company: {self.company_id}")
    
    def process_audio_to_audio(self, audio_input_path: str, output_filename: Optional[str] = None) -> dict:
        """
        Complete pipeline: Audio input → Audio output with text responses
        
        Args:
            audio_input_path (str): Path to input audio file
            output_filename (str): Custom output filename (optional)
            
        Returns:
            dict: Pipeline results with transcript, response text, and audio path
        """
        logger.info("=" * 60)
        logger.info("Starting Complete Voice Pipeline")
        logger.info("=" * 60)
        
        result = {
            "success": False,
            "transcript": "",
            "response_text": "",
            "response_audio_path": None,
            "company_id": self.company_id,
            "rag_enabled": RAG_ENABLED,
            "tts_enabled": TTS_ENABLED,
            "stages_completed": []
        }
        
        try:
            # Stage 1: Speech-to-Text
            logger.info("[STAGE 1] Speech-to-Text (STT)")
            transcript = transcribe_audio(audio_input_path)
            result["transcript"] = transcript
            result["stages_completed"].append("stt")
            logger.info(f"[STAGE 1] ✓ Transcribed: {transcript}")
            
            if not transcript:
                logger.warning("Empty transcript received")
                result["response_text"] = "I didn't catch that. Could you please repeat?"
            else:
                # Stage 2: Retrieval (RAG)
                if RAG_ENABLED:
                    logger.info("[STAGE 2] Retrieval-Augmented Generation (RAG)")
                    logger.info(f"[STAGE 2] Searching knowledge base for: {transcript}")
                    # RAG is handled internally in generate_response
                    result["stages_completed"].append("rag")
                    logger.info("[STAGE 2] ✓ Context retrieved")
                
                # Stage 3: Language Model (LLM)
                logger.info("[STAGE 3] Language Model (LLM)")
                response_text = generate_response(transcript, company_id=self.company_id)
                result["response_text"] = response_text
                result["stages_completed"].append("llm")
                logger.info(f"[STAGE 3] ✓ Generated response: {response_text}")
            
            # Stage 4: Text-to-Speech
            if TTS_ENABLED and result["response_text"]:
                logger.info("[STAGE 4] Text-to-Speech (TTS)")
                audio_path = synthesize_speech(
                    text=result["response_text"],
                    output_filename=output_filename
                )
                result["response_audio_path"] = str(audio_path)
                result["stages_completed"].append("tts")
                logger.info(f"[STAGE 4] ✓ Audio generated: {audio_path}")
            else:
                logger.info("[STAGE 4] TTS disabled or no response text")
            
            result["success"] = True
            logger.info("=" * 60)
            logger.info("Voice Pipeline Completed Successfully")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            result["error"] = str(e)
            result["response_text"] = "I'm sorry, I encountered an error processing your request."
        
        return result
    
    def process_text_to_audio(self, text: str, output_filename: Optional[str] = None) -> dict:
        """
        Text input → RAG → LLM → TTS → Audio output
        
        Args:
            text (str): Input text
            output_filename (str): Custom output filename (optional)
            
        Returns:
            dict: Pipeline results
        """
        logger.info("=" * 60)
        logger.info("Starting Text-to-Audio Pipeline")
        logger.info("=" * 60)
        
        result = {
            "success": False,
            "input_text": text,
            "response_text": "",
            "response_audio_path": None,
            "company_id": self.company_id,
            "stages_completed": []
        }
        
        try:
            # Stage 1: Language Model with RAG
            logger.info("[STAGE 1] RAG + LLM")
            response_text = generate_response(text, company_id=self.company_id)
            result["response_text"] = response_text
            result["stages_completed"].append("llm")
            logger.info(f"[STAGE 1] ✓ Response: {response_text}")
            
            # Stage 2: Text-to-Speech
            if TTS_ENABLED and response_text:
                logger.info("[STAGE 2] Text-to-Speech (TTS)")
                audio_path = synthesize_speech(
                    text=response_text,
                    output_filename=output_filename
                )
                result["response_audio_path"] = str(audio_path)
                result["stages_completed"].append("tts")
                logger.info(f"[STAGE 2] ✓ Audio: {audio_path}")
            
            result["success"] = True
            logger.info("=" * 60)
            logger.info("Text-to-Audio Pipeline Completed")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            result["error"] = str(e)
        
        return result
    
    def process_audio_to_text(self, audio_input_path: str) -> dict:
        """
        Audio input → STT → RAG → LLM → Text output (no TTS)
        
        Args:
            audio_input_path (str): Path to input audio file
            
        Returns:
            dict: Pipeline results
        """
        logger.info("Starting Audio-to-Text Pipeline")
        
        result = {
            "success": False,
            "transcript": "",
            "response_text": "",
            "company_id": self.company_id,
            "stages_completed": []
        }
        
        try:
            # STT
            transcript = transcribe_audio(audio_input_path)
            result["transcript"] = transcript
            result["stages_completed"].append("stt")
            
            # LLM with RAG
            if transcript:
                response_text = generate_response(transcript, company_id=self.company_id)
                result["response_text"] = response_text
                result["stages_completed"].append("llm")
            
            result["success"] = True
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            result["error"] = str(e)
        
        return result


# Singleton instance
_pipeline_instance = None

def get_pipeline(company_id: Optional[str] = None) -> VoicePipeline:
    """
    Get or create pipeline instance
    
    Args:
        company_id (str): Company ID (optional)
        
    Returns:
        VoicePipeline: Pipeline instance
    """
    global _pipeline_instance
    
    if _pipeline_instance is None or (_pipeline_instance.company_id != company_id and company_id is not None):
        _pipeline_instance = VoicePipeline(company_id=company_id)
    
    return _pipeline_instance
