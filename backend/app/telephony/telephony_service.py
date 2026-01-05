"""
FastAPI Telephony Service for AI Voice Agent
Production-ready service for handling calls via Asterisk ARI
"""
import logging
from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Create FastAPI router
router = APIRouter(prefix="/telephony", tags=["telephony"])


class OutboundCallRequest(BaseModel):
    """Request model for outbound calls"""
    phone_number: str
    caller_id: Optional[str] = "AI Agent"


class CallStatusResponse(BaseModel):
    """Response model for call status"""
    call_id: str
    status: str
    started_at: Optional[str]
    duration: Optional[float]


def get_instances():
    """Get global ARI client and call manager instances from main app"""
    from ..main import ari_client, call_manager
    return ari_client, call_manager


@router.get("/status")
async def get_service_status():
    """Get telephony service status"""
    ari_client, call_manager = get_instances()
    
    return {
        "status": "running" if ari_client and ari_client.connected else "disconnected",
        "ari_connected": ari_client.connected if ari_client else False,
        "active_calls": len(call_manager.active_calls) if call_manager else 0,
        "app_name": "ai_voice_agent",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/calls")
async def get_active_calls():
    """Get list of active calls"""
    ari_client, call_manager = get_instances()
    
    if not call_manager:
        raise HTTPException(status_code=503, detail="Call manager not initialized")
    
    calls = []
    for call_id, call_session in call_manager.active_calls.items():
        calls.append({
            "call_id": call_id,
            "channel_id": call_session.channel_id,
            "direction": call_session.direction,
            "status": call_session.status,
            "started_at": call_session.start_time.isoformat(),
            "duration": (datetime.now() - call_session.start_time).total_seconds()
        })
    
    return {"active_calls": len(calls), "calls": calls}


@router.get("/calls/{call_id}")
async def get_call_status(call_id: str):
    """Get specific call status"""
    ari_client, call_manager = get_instances()
    
    if not call_manager:
        raise HTTPException(status_code=503, detail="Call manager not initialized")
    
    call_session = call_manager.get_call(call_id)
    if not call_session:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return {
        "call_id": call_id,
        "channel_id": call_session.channel_id,
        "direction": call_session.direction,
        "status": call_session.status,
        "started_at": call_session.start_time.isoformat(),
        "duration": (datetime.now() - call_session.start_time).total_seconds(),
        "conversation_turns": len(call_session.conversation_history)
    }


@router.post("/calls/outbound", response_model=CallStatusResponse)
async def make_outbound_call(
    request: OutboundCallRequest,
    background_tasks: BackgroundTasks
):
    """Initiate an outbound call"""
    ari_client, call_manager = get_instances()
    
    if not ari_client or not ari_client.connected:
        raise HTTPException(status_code=503, detail="ARI not connected")
    
    if not call_manager:
        raise HTTPException(status_code=503, detail="Call manager not initialized")
    
    try:
        logger.info(f"Initiating outbound call to {request.phone_number}")
        
        # Originate call via ARI (endpoint format depends on your trunk configuration)
        call_id = await ari_client.originate_call(
            endpoint=request.phone_number,
            caller_id=request.caller_id or "AI Agent"
        )
        
        if not call_id:
            raise HTTPException(status_code=500, detail="Failed to originate call")
        
        return CallStatusResponse(
            call_id=call_id,
            status="dialing",
            started_at=datetime.now().isoformat(),
            duration=0
        )
        
    except Exception as e:
        logger.error(f"Failed to originate call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calls/{call_id}/hangup")
async def hangup_call(call_id: str):
    """Hangup an active call"""
    ari_client, call_manager = get_instances()
    
    if not call_manager:
        raise HTTPException(status_code=503, detail="Call manager not initialized")
    
    call_session = call_manager.get_call(call_id)
    if not call_session:
        raise HTTPException(status_code=404, detail="Call not found")
    
    try:
        await call_manager.hangup_call(call_id)
        return {"status": "success", "message": f"Call {call_id} terminated"}
    except Exception as e:
        logger.error(f"Failed to hangup call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calls/{call_id}/mute")
async def mute_call(call_id: str, muted: bool = True):
    """Mute/unmute a call"""
    ari_client, call_manager = get_instances()
    
    if not call_manager:
        raise HTTPException(status_code=503, detail="Call manager not initialized")
    
    call_session = call_manager.get_call(call_id)
    if not call_session:
        raise HTTPException(status_code=404, detail="Call not found")
    
    try:
        await call_manager.mute_call(call_id, muted)
        return {
            "status": "success",
            "call_id": call_id,
            "muted": muted
        }
    except Exception as e:
        logger.error(f"Failed to mute/unmute call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    ari_client, call_manager = get_instances()
    
    healthy = (
        ari_client is not None and
        ari_client.connected and
        call_manager is not None
    )
    
    return {
        "status": "healthy" if healthy else "unhealthy",
        "components": {
            "ari_websocket": "connected" if (ari_client and ari_client.connected) else "disconnected",
            "call_manager": "ready" if call_manager else "not initialized"
        }
    }
