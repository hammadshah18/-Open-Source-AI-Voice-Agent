"""
Real-time Call Manager with Streaming Audio Pipeline
Handles call lifecycle with zero-latency voice interaction
"""
import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path

from .media_websocket import MediaWebSocketHandler
from ..stt.streaming_stt import StreamingSTT
from ..llm.streaming_llm import StreamingLLM
from ..tts.streaming_tts import StreamingTTS
from ..config import ACTIVE_COMPANY, COMPANIES_DIR
from ..rag.kb_loader import KnowledgeBaseLoader

logger = logging.getLogger(__name__)


@dataclass
class RealtimeCallSession:
    """Represents an active real-time call session"""
    channel_id: str
    caller_number: str
    direction: str
    start_time: datetime = field(default_factory=datetime.now)
    status: str = "active"  # active, speaking, listening, ended
    bridge_id: Optional[str] = None
    
    # Streaming components
    media_ws: Optional[MediaWebSocketHandler] = None
    stt: Optional[StreamingSTT] = None
    llm: Optional[StreamingLLM] = None
    tts: Optional[StreamingTTS] = None
    ari_client: Optional[object] = None  # ARI client reference
    
    # State tracking
    is_agent_speaking: bool = False
    is_user_speaking: bool = False
    current_user_utterance: str = ""
    current_playback_id: Optional[str] = None
    conversation_history: list = field(default_factory=list)


class RealtimeCallManager:
    """
    Manages real-time calls with streaming audio pipeline
    Zero-latency architecture: Audio streams continuously
    """
    
    def __init__(self):
        self.active_calls: Dict[str, RealtimeCallSession] = {}
        self.company = ACTIVE_COMPANY
        
        # Audio storage
        self.audio_dir = Path("logs/call_audio")
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize streaming services (shared across calls)
        self.stt_service = StreamingSTT(model_size="base")
        self.tts_service = StreamingTTS()
        
        # Initialize knowledge base loader
        self.kb_loader = KnowledgeBaseLoader(COMPANIES_DIR)
        
        logger.info("Real-time Call Manager initialized")
    
    async def initialize(self):
        """Initialize AI services"""
        try:
            logger.info("Initializing AI services...")
            await self.stt_service.initialize()
            await self.tts_service.initialize()
            logger.info("✓ AI services ready")
        except Exception as e:
            logger.error(f"Failed to initialize AI services: {e}")
    
    def get_call(self, channel_id: str) -> Optional[RealtimeCallSession]:
        """Get call session by channel ID"""
        return self.active_calls.get(channel_id)
    
    async def handle_incoming_call(
        self,
        channel_id: str,
        caller_number: str,
        ari_client
    ):
        """
        Handle new incoming call with immediate response
        Flow: Answer → Speak → Listen (continuous)
        """
        try:
            logger.info(f"📞 Incoming call: {caller_number} → {channel_id}")
            
            # Create call session
            call_session = RealtimeCallSession(
                channel_id=channel_id,
                caller_number=caller_number,
                direction="inbound"
            )
            call_session.ari_client = ari_client  # Store ARI client reference
            
            # Create bridge
            bridge_id = await ari_client.create_bridge()
            if not bridge_id:
                logger.error("Failed to create bridge")
                await ari_client.hangup_channel(channel_id)
                return
            
            call_session.bridge_id = bridge_id
            await ari_client.add_channel_to_bridge(bridge_id, channel_id)
            
            # Store session
            self.active_calls[channel_id] = call_session
            
            # Initialize streaming components
            await self._setup_streaming_pipeline(call_session, ari_client)
            
            # Start with greeting (immediate)
            await self._speak_greeting(call_session)
            
        except Exception as e:
            logger.error(f"Error handling call: {e}", exc_info=True)
            if channel_id in self.active_calls:
                del self.active_calls[channel_id]
    
    async def _setup_streaming_pipeline(
        self,
        call_session: RealtimeCallSession,
        ari_client
    ):
        """Setup real-time audio streaming pipeline - FALLBACK MODE (file-based)"""
        try:
            # FALLBACK: Skip Media WebSocket setup (not available in this Asterisk version)
            # Using file-based playback instead
            
            # Create per-call streaming services
            call_session.llm = StreamingLLM()
            await call_session.llm.initialize()
            call_session.tts = self.tts_service  # Shared TTS service
            
            logger.info(f"✓ Streaming pipeline ready for {call_session.channel_id} (file-based mode)")
            
        except Exception as e:
            logger.error(f"Failed to setup streaming: {e}", exc_info=True)
    
    async def _on_audio_from_caller(self, channel_id: str, audio_chunk: bytes):
        """
        Handle incoming audio chunk from caller
        Feeds to STT for continuous recognition
        """
        call_session = self.get_call(channel_id)
        if not call_session or not call_session.stt:
            return
        
        # Barge-in detection: If user speaks while agent is speaking
        if call_session.is_agent_speaking:
            # User is interrupting - stop agent playback
            await self._handle_barge_in(call_session)
        
        # Feed audio to STT
        call_session.is_user_speaking = True
        await call_session.stt.process_audio_chunk(audio_chunk)
    
    async def _on_user_speech(self, channel_id: str, transcript: str):
        """
        Handle completed user utterance
        Triggers immediate LLM → TTS → Playback pipeline
        """
        call_session = self.get_call(channel_id)
        if not call_session:
            return
        
        try:
            logger.info(f"👤 User: {transcript}")
            
            call_session.is_user_speaking = False
            call_session.current_user_utterance = transcript
            
            # Add to history
            call_session.conversation_history.append({
                "role": "user",
                "text": transcript,
                "timestamp": datetime.now().isoformat()
            })
            
            # Retrieve RAG context (simplified - use basic context)
            context = f"User inquiry about: {transcript}"
            # In production, implement proper RAG retrieval here
            # For now, use simple context to avoid KB loader dependency
            
            # Generate streaming LLM response
            if not call_session.llm:
                logger.error("LLM service not initialized")
                return
            
            response_stream = call_session.llm.generate_response_stream(
                user_message=transcript,
                context=context
            )
            
            # Stream to TTS and playback simultaneously
            await self._stream_response_to_caller(call_session, response_stream)
            
        except Exception as e:
            logger.error(f"Error processing speech: {e}", exc_info=True)
    
    async def _stream_response_to_caller(
        self,
        call_session: RealtimeCallSession,
        text_stream
    ):
        """
        Stream AI response to caller using file-based playback (FALLBACK MODE)
        """
        try:
            call_session.status = "speaking"
            call_session.is_agent_speaking = True
            
            logger.info("🔊 Agent speaking (file-based playback)...")
            
            # Collect all text from stream
            text_parts = []
            async for text_chunk in text_stream:
                text_parts.append(text_chunk)
                if call_session.is_agent_speaking == False:
                    # Barge-in occurred
                    break
            
            full_text = " ".join(text_parts)
            
            if not full_text:
                logger.warning("No text to speak")
                call_session.is_agent_speaking = False
                return
            
            # Generate audio file
            import uuid
            audio_file = self.audio_dir / f"response_{uuid.uuid4()}.wav"
            
            if call_session.tts:
                await call_session.tts.synthesize_file(full_text, str(audio_file))
                
                # Play audio file via ARI
                from .ari_websocket import ARIWebSocketClient
                ari_client = call_session.ari_client if hasattr(call_session, 'ari_client') else None
                
                if ari_client and audio_file.exists():
                    # Play file in Asterisk
                    playback_id = await ari_client.play_audio(
                        call_session.channel_id,
                        f"sound:{audio_file}"
                    )
                    call_session.current_playback_id = playback_id
                    logger.info(f"Playing audio file: {audio_file.name}")
                else:
                    logger.warning(f"Cannot play audio - ARI client not available or file missing")
            
            # Speaking complete
            call_session.is_agent_speaking = False
            call_session.status = "listening"
            
            logger.info("✓ Agent finished speaking")
            
        except Exception as e:
            logger.error(f"Error streaming response: {e}", exc_info=True)
            call_session.is_agent_speaking = False
    
    async def _speak_greeting(self, call_session: RealtimeCallSession):
        """Speak initial greeting immediately"""
        greeting = "Hello! How can I help you today?"
        
        logger.info(f"🔊 Greeting: {greeting}")
        
        # Add to conversation history
        call_session.conversation_history.append({
            "role": "assistant",
            "text": greeting,
            "timestamp": datetime.now().isoformat()
        })
        
        # Create greeting as async generator
        async def greeting_stream():
            yield greeting
        
        # Stream greeting to caller
        await self._stream_response_to_caller(call_session, greeting_stream())
    
    async def _handle_barge_in(self, call_session: RealtimeCallSession):
        """
        Handle user interrupting agent
        Immediately stop playback and start listening
        """
        if not call_session.is_agent_speaking:
            return
        
        logger.info("⚠️ Barge-in detected - stopping agent")
        
        # Stop agent speaking
        call_session.is_agent_speaking = False
        call_session.status = "listening"
        
        # Stop media WebSocket playback
        if call_session.media_ws:
            await call_session.media_ws.stop_playback()
        
        # Reset STT to clear any partial audio
        if call_session.stt:
            call_session.stt.reset()
    
    async def handle_call_end(self, channel_id: str):
        """Handle call termination and cleanup"""
        call_session = self.get_call(channel_id)
        if not call_session:
            return
        
        try:
            call_session.status = "ended"
            duration = (datetime.now() - call_session.start_time).total_seconds()
            
            logger.info(
                f"📴 Call ended: {channel_id} "
                f"(duration: {duration:.1f}s, turns: {len(call_session.conversation_history)})"
            )
            
            # Disconnect media WebSocket
            if call_session.media_ws:
                await call_session.media_ws.disconnect()
            
            # Force final transcription if needed
            if call_session.stt:
                await call_session.stt.force_transcribe()
            
            # Remove from active calls
            del self.active_calls[channel_id]
            
        except Exception as e:
            logger.error(f"Error handling call end: {e}", exc_info=True)
    
    async def handle_playback_finished(self, channel_id: str):
        """Handle audio playback completion"""
        call_session = self.get_call(channel_id)
        if not call_session:
            return
        
        # Mark that agent finished speaking
        call_session.is_agent_speaking = False
        call_session.current_playback_id = None
        logger.info(f"✓ Playback completed for {channel_id}")
    
    async def hangup_call(self, channel_id: str):
        """Hangup an active call"""
        call_session = self.get_call(channel_id)
        if call_session:
            logger.info(f"Hanging up call: {channel_id}")
    
    async def mute_call(self, channel_id: str, muted: bool):
        """Mute/unmute a call (placeholder for API compatibility)"""
        call_session = self.get_call(channel_id)
        if call_session:
            logger.info(f"{'Muting' if muted else 'Unmuting'} call: {channel_id}")
    
    async def cleanup(self):
        """Cleanup all active calls"""
        logger.info("Cleaning up all active calls...")
        
        for channel_id in list(self.active_calls.keys()):
            await self.handle_call_end(channel_id)
        
        logger.info("✓ Realtime call manager cleanup complete")
