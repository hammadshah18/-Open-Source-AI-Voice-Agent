from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import shutil
import os
from datetime import datetime
from fastapi import UploadFile, File
from fastapi.responses import FileResponse
from ..stt.whisper_stt import transcribe_audio
from ..llm.dialog_manager import generate_response
from ..tts.coqui_tts import synthesize_speech
from ..pipelines.voice_pipeline import get_pipeline
from ..config import LOG_DIR, ACTIVE_COMPANY
from ..logger import logger
from ..telephony.session_manager import get_session_manager


router = APIRouter()

class TestRequest(BaseModel):
    text: str

class TestResponse(BaseModel):
    response: str

@router.post("/test", response_model=TestResponse)
def test_endpoint(payload: TestRequest):
    logger.info(f"Incoming request text: {payload.text}")

    reply = "Hello, this is your AI customer support agent."

    logger.info(f"Outgoing response text: {reply}")

    return {"response": reply}


@router.post("/stt")
def speech_to_text(file: UploadFile = File(...)):
    """
    Accepts an audio file and returns transcribed text.
    """
    
    # Create timestamped filename and save in logs folder
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_filename = f"voice_{timestamp}_{file.filename}"
    audio_path = LOG_DIR / audio_filename
    
    with open(audio_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    logger.info(f"Audio file saved: {audio_path}")
    
    text = transcribe_audio(str(audio_path))
    
    return {
        "transcript": text,
        "audio_file": audio_filename
    }


@router.post("/voice-to-answer")
def voice_to_answer(file: UploadFile = File(...)):
    """
    Complete flow: Speech → Text → LLM → Answer
    Accepts an audio file, transcribes it, sends to LLM, and returns the answer.
    """
    
    # Step 1: Save audio file in logs folder with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_filename = f"voice_{timestamp}_{file.filename}"
    audio_path = LOG_DIR / audio_filename
    
    with open(audio_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    logger.info(f"[FLOW] Audio file saved: {audio_path}")
    
    # Step 2: Speech to Text
    transcribed_text = transcribe_audio(str(audio_path))
    logger.info(f"[FLOW] Transcribed text: {transcribed_text}")
    
    # Step 3: Text to LLM - Generate Answer
    llm_response = generate_response(transcribed_text)
    logger.info(f"[FLOW] LLM generated answer: {llm_response}")
    
    # Return the complete flow result
    return {
        "transcript": transcribed_text,
        "llm_response": llm_response,
        "audio_file": audio_filename,
        "flow": "speech → text → llm → answer"
    }


@router.post("/voice-conversation")
def voice_conversation(file: UploadFile = File(...), company_id: str = ACTIVE_COMPANY):
    """
    COMPLETE AI VOICE AGENT PIPELINE
    
    Flow: Audio Input → STT → RAG → LLM → TTS → Audio Output
    
    This is the main endpoint for the full voice agent experience.
    Accepts audio, returns audio response with company knowledge.
    
    Args:
        file: Audio file (WAV, MP3, etc.)
        company_id: Company to use for knowledge base (default: ACTIVE_COMPANY)
    
    Returns:
        JSON with transcript, response text, and audio file path
    """
    logger.info(f"=" * 80)
    logger.info(f"NEW VOICE CONVERSATION REQUEST - Company: {company_id}")
    logger.info(f"=" * 80)
    
    # Save uploaded audio file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_filename = f"input_{timestamp}_{file.filename}"
    audio_path = LOG_DIR / audio_filename
    
    with open(audio_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    logger.info(f"Input audio saved: {audio_path}")
    
    # Run complete pipeline
    pipeline = get_pipeline(company_id=company_id)
    result = pipeline.process_audio_to_audio(str(audio_path))
    
    # Add input file info
    result["input_audio_file"] = audio_filename
    
    return result


@router.post("/voice-conversation-download")
def voice_conversation_download(file: UploadFile = File(...), company_id: str = ACTIVE_COMPANY):
    """
    Same as /voice-conversation but returns the audio file directly for download/playback
    
    Returns:
        Audio file (WAV format)
    """
    logger.info(f"Voice conversation with audio download - Company: {company_id}")
    
    # Save input audio
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audio_filename = f"input_{timestamp}_{file.filename}"
    audio_path = LOG_DIR / audio_filename
    
    with open(audio_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Run pipeline
    pipeline = get_pipeline(company_id=company_id)
    result = pipeline.process_audio_to_audio(str(audio_path))
    
    if result["success"] and result["response_audio_path"]:
        # Return audio file
        return FileResponse(
            result["response_audio_path"],
            media_type="audio/wav",
            filename="response.wav"
        )
    else:
        return {
            "error": "Failed to generate audio response",
            "details": result
        }


@router.post("/text-to-speech")
def text_to_speech_endpoint(payload: TestRequest):
    """
    Convert text to speech using TTS
    
    Args:
        payload: {"text": "text to convert"}
    
    Returns:
        Path to generated audio file
    """
    logger.info(f"TTS request for text: {payload.text}")
    
    try:
        audio_path = synthesize_speech(payload.text)
        
        return {
            "success": True,
            "text": payload.text,
            "audio_file": audio_path.name,
            "audio_path": str(audio_path)
        }
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/download-audio/{filename}")
def download_audio(filename: str):
    """
    Download audio file from logs directory
    
    Args:
        filename: Name of the audio file
    
    Returns:
        Audio file for download
    """
    file_path = LOG_DIR / filename
    
    if not file_path.exists():
        return {"error": "File not found"}
    
    return FileResponse(
        file_path,
        media_type="audio/wav",
        filename=filename
    )


@router.get("/companies")
def list_companies():
    """
    List available companies in the knowledge base
    """
    from ..rag.kb_loader import KnowledgeBaseLoader
    from ..config import COMPANIES_DIR
    
    try:
        loader = KnowledgeBaseLoader(COMPANIES_DIR)
        companies = loader.get_available_companies()
        
        return {
            "companies": companies,
            "active_company": ACTIVE_COMPANY
        }
    except Exception as e:
        logger.error(f"Error listing companies: {e}")
        return {"error": str(e)}


@router.post("/switch-company/{company_id}")
def switch_company(company_id: str):
    """
    Switch active company for RAG system
    
    Args:
        company_id: Company identifier
    
    Returns:
        Success status
    """
    try:
        pipeline = get_pipeline(company_id=company_id)
        
        return {
            "success": True,
            "company_id": company_id,
            "message": f"Switched to {company_id}"
        }
    except Exception as e:
        logger.error(f"Error switching company: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.websocket("/ws/telephony/{channel_id}")
async def telephony_websocket(websocket: WebSocket, channel_id: str):
    """
    WebSocket endpoint for real-time telephony audio streaming
    
    This endpoint handles:
    - Incoming audio frames from Asterisk ARI
    - STT processing
    - RAG + LLM response generation
    - TTS audio streaming back to Asterisk
    - Barge-in detection and handling
    """
    await websocket.accept()
    logger.info(f"📞 WebSocket connection established for channel: {channel_id}")
    
    session_manager = get_session_manager()
    session = None
    
    try:
        # Wait for session metadata
        data = await websocket.receive_json()
        
        if data.get("type") == "session_start":
            caller_number = data.get("caller_number", "Unknown")
            company_id = data.get("company_id", ACTIVE_COMPANY)
            
            logger.info(f"Starting telephony session: {channel_id} (Caller: {caller_number}, Company: {company_id})")
            
            # Create session
            session = await session_manager.create_session(
                channel_id=channel_id,
                caller_number=caller_number,
                company_id=company_id,
                websocket=websocket
            )
            
            # Main loop: handle audio frames
            while True:
                try:
                    # Receive audio frame or control message
                    message = await websocket.receive()
                    
                    if "bytes" in message:
                        # Audio frame from Asterisk
                        audio_data = message["bytes"]
                        await session.handle_audio_frame(audio_data)
                    
                    elif "text" in message:
                        # Control message
                        import json
                        control = json.loads(message["text"])
                        
                        if control.get("type") == "stop_playback":
                            await session.handle_barge_in()
                        
                        elif control.get("type") == "end_session":
                            logger.info(f"Session end requested for {channel_id}")
                            break
                
                except WebSocketDisconnect:
                    logger.info(f"WebSocket disconnected for {channel_id}")
                    break
        
        else:
            logger.warning(f"Invalid session start message for {channel_id}")
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for {channel_id}")
    
    except Exception as e:
        logger.error(f"Error in telephony WebSocket: {e}")
    
    finally:
        # Cleanup session
        if session:
            await session_manager.end_session(channel_id)
        
        logger.info(f"📴 Telephony WebSocket closed for {channel_id}")


@router.get("/telephony/status")
def get_telephony_status():
    """
    Get telephony system status
    """
    session_manager = get_session_manager()
    
    return {
        "status": "operational",
        "active_calls": session_manager.get_active_sessions_count(),
        "timestamp": datetime.now().isoformat()
    }

