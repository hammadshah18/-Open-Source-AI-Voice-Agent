"""
Asterisk ARI WebSocket Client
Handles real-time communication with Asterisk via WebSocket
"""
import asyncio
import json
import logging
from typing import Optional, Callable, Dict
import websockets
from datetime import datetime
import aiohttp

logger = logging.getLogger(__name__)


class ARIWebSocketClient:
    """
    WebSocket client for Asterisk ARI (Asterisk REST Interface)
    Manages connection, event handling, and call control
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8088,
        username: str = "aiagent",
        password: str = "strongpassword",
        app_name: str = "ai_voice_agent",
        call_manager=None
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.app_name = app_name
        self.call_manager = call_manager
        
        # WebSocket connection
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.reconnect_delay = 5
        
        # HTTP session for REST API calls
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = f"http://{host}:{port}/ari"
        self.auth = aiohttp.BasicAuth(username, password)
        
        logger.info(f"ARI Client initialized: {self.base_url}, app={app_name}")
    
    async def connect(self):
        """Connect to ARI WebSocket and handle events"""
        while True:
            try:
                if not self.session:
                    self.session = aiohttp.ClientSession()
                
                # WebSocket URL for events
                ws_url = f"ws://{self.host}:{self.port}/ari/events?app={self.app_name}&api_key={self.username}:{self.password}"
                
                logger.info(f"Connecting to ARI WebSocket: ws://{self.host}:{self.port}/ari/events")
                
                async with websockets.connect(ws_url) as websocket:
                    self.ws = websocket
                    self.connected = True
                    logger.info(f"✓ Connected to Asterisk ARI - Stasis app '{self.app_name}' registered")
                    
                    # Listen for events
                    async for message in websocket:
                        await self._handle_event(message)
                        
            except Exception as e:
                self.connected = False
                logger.error(f"ARI WebSocket error: {e}")
                logger.info(f"Reconnecting in {self.reconnect_delay} seconds...")
                await asyncio.sleep(self.reconnect_delay)
    
    async def disconnect(self):
        """Disconnect from ARI WebSocket"""
        self.connected = False
        
        if self.ws:
            await self.ws.close()
            self.ws = None
        
        if self.session:
            await self.session.close()
            self.session = None
        
        logger.info("Disconnected from ARI WebSocket")
    
    async def _handle_event(self, message: str):
        """Handle incoming ARI events"""
        try:
            event = json.loads(message)
            event_type = event.get("type")
            
            logger.debug(f"ARI Event: {event_type}")
            
            # Route events to appropriate handlers
            if event_type == "StasisStart":
                await self._on_stasis_start(event)
            elif event_type == "StasisEnd":
                await self._on_stasis_end(event)
            elif event_type == "ChannelDtmfReceived":
                await self._on_dtmf_received(event)
            elif event_type == "ChannelHangupRequest":
                await self._on_hangup_request(event)
            elif event_type == "PlaybackFinished":
                await self._on_playback_finished(event)
            elif event_type == "ChannelStateChange":
                await self._on_channel_state_change(event)
            else:
                logger.debug(f"Unhandled event type: {event_type}")
                
        except Exception as e:
            logger.error(f"Error handling ARI event: {e}", exc_info=True)
    
    async def _on_stasis_start(self, event: Dict):
        """Handle incoming call (StasisStart event) - Answer immediately"""
        try:
            channel = event.get("channel", {})
            channel_id = channel.get("id")
            caller_number = channel.get("caller", {}).get("number", "Unknown")
            
            logger.info(f"📞 StasisStart: {caller_number} → {channel_id}")
            
            # Answer immediately - no delays
            await self.answer_channel(channel_id)
            
            # Hand off to call manager asynchronously
            if self.call_manager:
                asyncio.create_task(
                    self.call_manager.handle_incoming_call(
                        channel_id=channel_id,
                        caller_number=caller_number,
                        ari_client=self
                    )
                )
            
        except Exception as e:
            logger.error(f"Error handling StasisStart: {e}", exc_info=True)
    
    async def _on_stasis_end(self, event: Dict):
        """Handle call end (StasisEnd event)"""
        try:
            channel = event.get("channel", {})
            channel_id = channel.get("id")
            
            logger.info(f"📴 Call ended: {channel_id}")
            
            if self.call_manager:
                await self.call_manager.handle_call_end(channel_id)
                
        except Exception as e:
            logger.error(f"Error handling StasisEnd: {e}", exc_info=True)
    
    async def _on_dtmf_received(self, event: Dict):
        """Handle DTMF input"""
        try:
            channel_id = event.get("channel", {}).get("id")
            digit = event.get("digit")
            
            logger.info(f"🔢 DTMF received: {digit} on channel {channel_id}")
            
            if self.call_manager:
                await self.call_manager.handle_dtmf(channel_id, digit)
                
        except Exception as e:
            logger.error(f"Error handling DTMF: {e}")
    
    async def _on_hangup_request(self, event: Dict):
        """Handle hangup request"""
        channel_id = event.get("channel", {}).get("id")
        logger.info(f"Hangup requested for channel: {channel_id}")
    
    async def _on_playback_finished(self, event: Dict):
        """Handle playback finished event"""
        playback_id = event.get("playback", {}).get("id")
        channel_id = event.get("playback", {}).get("target_uri", "").split("/")[-1]
        
        logger.info(f"Playback finished: {playback_id}")
        
        if self.call_manager:
            await self.call_manager.handle_playback_finished(channel_id)
    
    async def _on_channel_state_change(self, event: Dict):
        """Handle channel state changes"""
        channel = event.get("channel", {})
        channel_id = channel.get("id")
        state = channel.get("state")
        
        logger.debug(f"Channel {channel_id} state: {state}")
    
    # ============= ARI REST API Methods =============
    
    async def _ari_request(self, method: str, endpoint: str, **kwargs):
        """Make an ARI REST API request"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            async with self.session.request(
                method,
                url,
                auth=self.auth,
                **kwargs
            ) as response:
                if response.status >= 400:
                    text = await response.text()
                    logger.error(f"ARI API error: {response.status} - {text}")
                    return None
                
                if response.content_type == 'application/json':
                    return await response.json()
                return await response.text()
                
        except Exception as e:
            logger.error(f"ARI request failed: {method} {endpoint} - {e}")
            return None
    
    async def answer_channel(self, channel_id: str):
        """Answer an incoming call"""
        logger.info(f"Answering channel: {channel_id}")
        return await self._ari_request("POST", f"channels/{channel_id}/answer")
    
    async def hangup_channel(self, channel_id: str):
        """Hangup a channel"""
        logger.info(f"Hanging up channel: {channel_id}")
        return await self._ari_request("DELETE", f"channels/{channel_id}")
    
    async def create_bridge(self, bridge_type: str = "mixing"):
        """Create a new bridge"""
        result = await self._ari_request(
            "POST",
            "bridges",
            params={"type": bridge_type}
        )
        if result and isinstance(result, dict):
            bridge_id = result.get("id")
            logger.info(f"Bridge created: {bridge_id}")
            return bridge_id
        return None
    
    async def add_channel_to_bridge(self, bridge_id: str, channel_id: str):
        """Add a channel to a bridge"""
        logger.info(f"Adding channel {channel_id} to bridge {bridge_id}")
        return await self._ari_request(
            "POST",
            f"bridges/{bridge_id}/addChannel",
            params={"channel": channel_id}
        )
    
    async def remove_channel_from_bridge(self, bridge_id: str, channel_id: str):
        """Remove a channel from a bridge"""
        logger.info(f"Removing channel {channel_id} from bridge {bridge_id}")
        return await self._ari_request(
            "POST",
            f"bridges/{bridge_id}/removeChannel",
            params={"channel": channel_id}
        )
    
    async def delete_bridge(self, bridge_id: str):
        """Delete a bridge"""
        logger.info(f"Deleting bridge: {bridge_id}")
        return await self._ari_request("DELETE", f"bridges/{bridge_id}")
    
    async def play_audio(self, channel_id: str, media_uri: str) -> Optional[str]:
        """
        Play audio to a channel
        media_uri: sound:filename or recording:name
        Returns playback_id
        """
        result = await self._ari_request(
            "POST",
            f"channels/{channel_id}/play",
            params={"media": media_uri}
        )
        if result and isinstance(result, dict):
            playback_id = result.get("id")
            logger.info(f"Started playback {playback_id} on channel {channel_id}")
            return playback_id
        return None
    
    async def stop_playback(self, playback_id: str):
        """Stop audio playback"""
        logger.info(f"Stopping playback: {playback_id}")
        return await self._ari_request("DELETE", f"playbacks/{playback_id}")
    
    async def start_recording(self, channel_id: str, name: str, format: str = "wav"):
        """Start recording a channel"""
        return await self._ari_request(
            "POST",
            f"channels/{channel_id}/record",
            params={
                "name": name,
                "format": format,
                "maxDurationSeconds": 0,
                "maxSilenceSeconds": 0,
                "ifExists": "overwrite",
                "beep": False,
                "terminateOn": "none"
            }
        )
    
    async def stop_recording(self, recording_name: str):
        """Stop an active recording"""
        return await self._ari_request(
            "POST",
            f"recordings/live/{recording_name}/stop"
        )
    
    async def start_external_media(self, channel_id: str, app: str, external_host: str):
        """Start external media stream (for raw audio)"""
        return await self._ari_request(
            "POST",
            "channels/externalMedia",
            params={
                "app": app,
                "external_host": external_host,
                "format": "slin16",
                "channelId": channel_id
            }
        )
    
    async def originate_call(
        self,
        endpoint: str,
        caller_id: str = "AI Agent",
        context: str = "default",
        extension: str = "s",
        priority: int = 1
    ) -> Optional[str]:
        """
        Originate an outbound call
        endpoint: Channel endpoint (format depends on trunk config)
        Returns channel_id
        """
        result = await self._ari_request(
            "POST",
            "channels",
            params={
                "endpoint": endpoint,
                "app": self.app_name,
                "callerId": caller_id,
                "timeout": 30
            }
        )
        
        if result and isinstance(result, dict):
            channel_id = result.get("id")
            logger.info(f"✓ Outbound call originated: {channel_id} to {endpoint}")
            return channel_id
        
        return None
    
    async def mute_channel(self, channel_id: str, direction: str = "in"):
        """Mute a channel (in/out/both)"""
        return await self._ari_request(
            "POST",
            f"channels/{channel_id}/mute",
            params={"direction": direction}
        )
    
    async def unmute_channel(self, channel_id: str, direction: str = "in"):
        """Unmute a channel"""
        return await self._ari_request(
            "DELETE",
            f"channels/{channel_id}/mute",
            params={"direction": direction}
        )
    
    async def get_channel_info(self, channel_id: str):
        """Get channel information"""
        return await self._ari_request("GET", f"channels/{channel_id}")
