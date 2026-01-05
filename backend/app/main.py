import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from .api.routes import router
from .telephony.telephony_service import router as telephony_router
from .api.websocket import router as websocket_router
from .telephony.ari_websocket import ARIWebSocketClient
from .telephony.realtime_call_manager import RealtimeCallManager
from .logger import logger
from typing import Optional


# Global instances for telephony
ari_client: Optional[ARIWebSocketClient] = None
call_manager: Optional[RealtimeCallManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global ari_client, call_manager
    
    # Startup
    logger.info("Starting real-time telephony service...")
    
    try:
        # Initialize real-time call manager
        call_manager = RealtimeCallManager()
        await call_manager.initialize()  # Load AI models
        
        # Initialize ARI WebSocket client
        ari_client = ARIWebSocketClient(
            host="localhost",
            port=8088,
            username="aiagent",
            password="strongpassword",
            app_name="ai_voice_agent",
            call_manager=call_manager
        )
        
        # Connect to ARI WebSocket in background
        asyncio.create_task(ari_client.connect())
        
        logger.info("✓ Real-time telephony service started")
    except Exception as e:
        logger.error(f"Failed to start telephony service: {e}")
        raise
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("Shutting down telephony service...")
    
    if ari_client:
        await ari_client.disconnect()
    
    if call_manager:
        await call_manager.cleanup()
    
    logger.info("✓ Telephony service shut down")


app = FastAPI(
    title="AI Voice Agent",
    description="Open-source AI Voice Agent for Customer Service with Telephony Support",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/")
def root():
    return {
        "message": "AI Voice Agent backend is running",
        "docs": "/docs",
        "health": "/health",
        "telephony": "/telephony/status"
    }


@app.get("/health")
def health_check():
    logger.info("Health check endpoint called")
    return {"status": "ok"}


# Include API routes
app.include_router(router)

# Include WebSocket routes
app.include_router(websocket_router)

# Include telephony routes  
app.include_router(telephony_router)

# Mount static files for web UI
static_path = Path(__file__).parent.parent / "static"
static_path.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

@app.get("/ui")
async def serve_ui():
    """Serve the web UI"""
    return FileResponse(str(static_path / "index.html"))

logger.info("FastAPI application initialized with telephony support")
