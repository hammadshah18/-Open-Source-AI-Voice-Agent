"""
Call Manager - Handles call lifecycle and AI pipeline integration
Manages active calls, audio streaming, and conversation flow with barge-in support
"""
import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path

from ..stt.whisper_stt import transcribe_audio
from ..llm.dialog_manager import generate_response
from ..tts.coqui_tts import synthesize_speech
from ..config import ACTIVE_COMPANY
from .audio_stream import AudioStreamHandler

logger = logging.getLogger(__name__)


@dataclass
class CallSession:
    """Represents an active call session"""
    channel_id: str
    caller_number: str
    direction: str  # "inbound" or "outbound"
    start_time: datetime = field(default_factory=datetime.now)
    status: str = "active"  # active, speaking, listening, ended
    bridge_id: Optional[str] = None
    conversation_history: list = field(default_factory=list)
    current_playback_id: Optional[str] = None
    current_recording_name: Optional[str] = None
    is_speaking: bool = False
    audio_stream: Optional[AudioStreamHandler] = None


class CallManager:
    """
    Manages call lifecycle and AI voice pipeline integration
    Handles audio streaming, transcription, LLM responses, and TTS playback
    """
    
    def __init__(self):
        self.active_calls: Dict[str, CallSession] = {}
        self.company = ACTIVE_COMPANY
        
        # Audio storage
        self.audio_dir = Path("logs/call_audio")
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("Call Manager initialized")
    
    def get_call(self, channel_id: str) -> Optional[CallSession]:
        """Get call session by channel ID"""
        return self.active_calls.get(channel_id)
    
    async def handle_incoming_call(self, channel_id: str, caller_number: str, ari_client):
        """Handle new incoming call"""
        try:
            logger.info(f"📞 Handling incoming call: {channel_id} from {caller_number}")
            
            # Create call session
            call_session = CallSession(
                channel_id=channel_id,
                caller_number=caller_number,
                direction="inbound"
            )
            
            # Create bridge for the call
            bridge_id = await ari_client.create_bridge()
            if not bridge_id:
                logger.error("Failed to create bridge")
                await ari_client.hangup_channel(channel_id)
                return
            
            call_session.bridge_id = bridge_id
            
            # Add channel to bridge
            await ari_client.add_channel_to_bridge(bridge_id, channel_id)
            
            # Store call session
            self.active_calls[channel_id] = call_session
            
            # Initialize audio stream handler
            call_session.audio_stream = AudioStreamHandler(
                channel_id=channel_id,
                audio_dir=self.audio_dir
            )
            
            # Start the conversation with greeting
            await self._start_conversation(call_session, ari_client)
            
        except Exception as e:
            logger.error(f"Error handling incoming call: {e}", exc_info=True)
            if channel_id in self.active_calls:
                del self.active_calls[channel_id]
    
    async def handle_outbound_call(self, channel_id: str, destination: str, ari_client):
        """Handle outbound call"""
        try:
            logger.info(f"📱 Handling outbound call: {channel_id} to {destination}")
            
            # Create call session
            call_session = CallSession(
                channel_id=channel_id,
                caller_number=destination,
                direction="outbound"
            )
            
            # Create bridge
            bridge_id = await ari_client.create_bridge()
            if not bridge_id:
                logger.error("Failed to create bridge for outbound call")
                return
            
            call_session.bridge_id = bridge_id
            await ari_client.add_channel_to_bridge(bridge_id, channel_id)
            
            # Store call session
            self.active_calls[channel_id] = call_session
            
            # Initialize audio stream
            call_session.audio_stream = AudioStreamHandler(
                channel_id=channel_id,
                audio_dir=self.audio_dir
            )
            
            # Wait for answer, then start conversation
            # (StasisStart will trigger when answered)
            
        except Exception as e:
            logger.error(f"Error handling outbound call: {e}", exc_info=True)
    
    async def _start_conversation(self, call_session: CallSession, ari_client):
        """Start conversation with initial greeting"""
        try:
            # Initial greeting
            greeting = f"Hello! This is {self.company} AI assistant. How can I help you today?"
            
            logger.info(f"🤖 Greeting: {greeting}")
            
            # Add to conversation history
            call_session.conversation_history.append({
                "role": "assistant",
                "text": greeting,
                "timestamp": datetime.now().isoformat()
            })
            
            # Generate TTS audio
            audio_file = await self._generate_tts(greeting, call_session.channel_id)
            
            if audio_file:
                # Play greeting
                await self._play_audio(call_session, ari_client, audio_file)
                
                # Start listening for user response
                await self._start_listening(call_session, ari_client)
            else:
                logger.error("Failed to generate greeting audio")
                await ari_client.hangup_channel(call_session.channel_id)
                
        except Exception as e:
            logger.error(f"Error starting conversation: {e}", exc_info=True)
    
    async def _start_listening(self, call_session: CallSession, ari_client):
        """Start listening for user speech"""
        try:
            call_session.status = "listening"
            call_session.is_speaking = False
            
            logger.info(f"👂 Listening on channel {call_session.channel_id}...")
            
            # Start recording user audio
            recording_name = f"user_{call_session.channel_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Store recording name for this session
            call_session.current_recording_name = recording_name
            
            await ari_client.start_recording(call_session.channel_id, recording_name)
            
            # In production, use VAD or DTMF to detect end of speech
            # For now, use shorter timeout for lower latency
            await asyncio.sleep(3)  # Reduced from 8s for responsiveness
            
            # Stop recording
            await ari_client.stop_recording(recording_name)
            
            # Process the recorded audio
            audio_file = self.audio_dir / f"{recording_name}.wav"
            
            if audio_file.exists():
                await self._process_user_speech(call_session, ari_client, str(audio_file))
            else:
                logger.warning(f"Recording file not found: {audio_file}")
                # Continue listening
                await self._start_listening(call_session, ari_client)
                
        except Exception as e:
            logger.error(f"Error in listening: {e}", exc_info=True)
    
    async def _process_user_speech(self, call_session: CallSession, ari_client, audio_file: str):
        """Process user speech through STT -> LLM -> TTS pipeline"""
        try:
            logger.info(f"🔄 Processing user speech from {audio_file}")
            
            # STT: Transcribe audio
            user_text = await asyncio.to_thread(transcribe_audio, audio_file)
            
            if not user_text or user_text.strip() == "":
                logger.info("No speech detected, continuing to listen...")
                await self._start_listening(call_session, ari_client)
                return
            
            logger.info(f"👤 User said: {user_text}")
            
            # Add to conversation history
            call_session.conversation_history.append({
                "role": "user",
                "text": user_text,
                "timestamp": datetime.now().isoformat()
            })
            
            # LLM: Generate response
            # Build conversation context for system prompt
            conversation_context = "\n".join([
                f"{msg['role'].upper()}: {msg['text']}" 
                for msg in call_session.conversation_history[-6:]  # Last 6 messages for context
            ])
            
            system_prompt = f"Previous conversation:\n{conversation_context}" if conversation_context else None
            
            ai_response = await asyncio.to_thread(
                generate_response,
                user_text,
                system_prompt,
                self.company
            )
            
            logger.info(f"🤖 AI response: {ai_response}")
            
            # Add to conversation history
            call_session.conversation_history.append({
                "role": "assistant",
                "text": ai_response,
                "timestamp": datetime.now().isoformat()
            })
            
            # TTS: Generate speech
            response_audio = await self._generate_tts(ai_response, call_session.channel_id)
            
            if response_audio:
                # Play response
                await self._play_audio(call_session, ari_client, response_audio)
                
                # Continue listening after playback
                await self._start_listening(call_session, ari_client)
            else:
                logger.error("Failed to generate TTS audio")
                await self._start_listening(call_session, ari_client)
                
        except Exception as e:
            logger.error(f"Error processing user speech: {e}", exc_info=True)
            # Continue listening on error
            await self._start_listening(call_session, ari_client)
    
    async def _generate_tts(self, text: str, channel_id: str) -> Optional[str]:
        """Generate TTS audio file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.audio_dir / f"response_{channel_id}_{timestamp}.wav"
            
            # Generate TTS (run in thread pool to avoid blocking)
            await asyncio.to_thread(synthesize_speech, text, str(output_file))
            
            if output_file.exists():
                logger.info(f"✓ TTS generated: {output_file}")
                return str(output_file)
            else:
                logger.error(f"TTS file not created: {output_file}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating TTS: {e}", exc_info=True)
            return None
    
    async def _play_audio(self, call_session: CallSession, ari_client, audio_file: str):
        """Play audio file to caller"""
        try:
            call_session.status = "speaking"
            call_session.is_speaking = True
            
            # For production: copy to Asterisk sounds directory or use HTTP server
            # Simplified: use recording scheme (requires file in Asterisk recording dir)
            filename = Path(audio_file).stem
            media_uri = f"sound:{filename}"
            
            # Note: In production, implement proper audio file serving
            # Options: 1) Copy to /var/lib/asterisk/sounds/
            #          2) HTTP server for audio files
            #          3) Stream via external media channel
            
            playback_id = await ari_client.play_audio(call_session.channel_id, media_uri)
            
            if playback_id:
                call_session.current_playback_id = playback_id
                logger.info(f"🔊 Playing audio: {playback_id}")
            else:
                logger.warning("Failed to start playback")
                call_session.is_speaking = False
                
        except Exception as e:
            logger.error(f"Error playing audio: {e}", exc_info=True)
            call_session.is_speaking = False
    
    async def handle_barge_in(self, channel_id: str, ari_client):
        """Handle barge-in (user interrupts AI)"""
        call_session = self.get_call(channel_id)
        if not call_session:
            return
        
        if call_session.is_speaking and call_session.current_playback_id:
            logger.info(f"⚠️ Barge-in detected on channel {channel_id}")
            
            # Stop current playback
            await ari_client.stop_playback(call_session.current_playback_id)
            call_session.current_playback_id = None
            call_session.is_speaking = False
            
            # Start listening immediately
            await self._start_listening(call_session, ari_client)
    
    async def handle_playback_finished(self, channel_id: str):
        """Handle playback finished event"""
        call_session = self.get_call(channel_id)
        if call_session:
            call_session.is_speaking = False
            call_session.current_playback_id = None
            logger.info(f"✓ Playback finished on channel {channel_id}")
    
    async def handle_dtmf(self, channel_id: str, digit: str):
        """Handle DTMF input"""
        call_session = self.get_call(channel_id)
        if call_session:
            logger.info(f"DTMF {digit} received on channel {channel_id}")
            # Handle DTMF if needed (e.g., menu navigation)
    
    async def handle_call_end(self, channel_id: str):
        """Handle call termination"""
        call_session = self.get_call(channel_id)
        if not call_session:
            return
        
        try:
            call_session.status = "ended"
            duration = (datetime.now() - call_session.start_time).total_seconds()
            
            logger.info(f"📴 Call ended: {channel_id} (duration: {duration:.1f}s, turns: {len(call_session.conversation_history)})")
            
            # Cleanup
            if call_session.audio_stream:
                await call_session.audio_stream.cleanup()
            
            # Remove from active calls
            del self.active_calls[channel_id]
            
        except Exception as e:
            logger.error(f"Error handling call end: {e}", exc_info=True)
    
    async def hangup_call(self, channel_id: str):
        """Hangup an active call"""
        call_session = self.get_call(channel_id)
        if call_session:
            # The hangup will trigger StasisEnd event
            logger.info(f"Hanging up call: {channel_id}")
    
    async def mute_call(self, channel_id: str, muted: bool):
        """Mute/unmute a call"""
        call_session = self.get_call(channel_id)
        if call_session:
            logger.info(f"{'Muting' if muted else 'Unmuting'} call: {channel_id}")
            # Mute/unmute logic would be handled via ARI
    
    async def cleanup(self):
        """Cleanup all active calls"""
        logger.info("Cleaning up all active calls...")
        
        for channel_id in list(self.active_calls.keys()):
            await self.handle_call_end(channel_id)
        
        logger.info("✓ Call manager cleanup complete")
