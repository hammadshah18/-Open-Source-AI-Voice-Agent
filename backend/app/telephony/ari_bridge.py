"""
Asterisk ARI Bridge for Real-Time Voice Agent
Handles call control, audio streaming, and barge-in detection
"""
import asyncio
import aiohttp
import json
from typing import Optional, Dict, Any
from datetime import datetime
from ..logger import logger
from ..config import (
    ARI_URL, ARI_USERNAME, ARI_PASSWORD,
    ARI_APP_NAME, WEBSOCKET_URL
)


class ARIBridge:
    """
    Manages Asterisk ARI connection and call handling
    """
    
    def __init__(self):
        self.ari_url = ARI_URL
        self.username = ARI_USERNAME
        self.password = ARI_PASSWORD
        self.app_name = ARI_APP_NAME
        self.websocket_url = WEBSOCKET_URL
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self.active_calls: Dict[str, Dict[str, Any]] = {}
        
        # WebSocket connections to FastAPI
        self.audio_websockets: Dict[str, aiohttp.ClientWebSocketResponse] = {}
        
    async def connect(self):
        """
        Establish ARI WebSocket connection
        """
        if self.session is None:
            self.session = aiohttp.ClientSession(
                auth=aiohttp.BasicAuth(self.username, self.password)
            )
        
        try:
            ws_url = f"{self.ari_url}/events?app={self.app_name}&subscribeAll=true"
            logger.info(f"Connecting to ARI WebSocket: {ws_url}")
            
            self.ws = await self.session.ws_connect(ws_url)
            logger.info("✓ ARI WebSocket connected")
            
        except Exception as e:
            logger.error(f"Failed to connect to ARI: {e}")
            raise
    
    async def handle_events(self):
        """
        Main event loop - processes ARI events
        """
        if not self.ws:
            raise RuntimeError("WebSocket not connected")
        
        logger.info("Starting ARI event handler...")
        
        async for msg in self.ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    event = json.loads(msg.data)
                    await self.process_event(event)
                except Exception as e:
                    logger.error(f"Error processing ARI event: {e}")
            
            elif msg.type == aiohttp.WSMsgType.ERROR:
                logger.error(f"WebSocket error: {self.ws.exception()}")
                break
    
    async def process_event(self, event: Dict[str, Any]):
        """
        Process individual ARI events
        """
        event_type = event.get("type")
        
        if event_type == "StasisStart":
            await self.handle_stasis_start(event)
        
        elif event_type == "StasisEnd":
            await self.handle_stasis_end(event)
        
        elif event_type == "ChannelDtmfReceived":
            await self.handle_dtmf(event)
        
        elif event_type == "PlaybackFinished":
            await self.handle_playback_finished(event)
        
        else:
            logger.debug(f"ARI Event: {event_type}")
    
    async def handle_stasis_start(self, event: Dict[str, Any]):
        """
        Handle incoming call (StasisStart event)
        """
        channel = event.get("channel", {})
        channel_id = channel.get("id")
        caller_number = channel.get("caller", {}).get("number", "Unknown")
        
        logger.info(f"📞 Incoming call from {caller_number} (Channel: {channel_id})")
        
        # Store call metadata
        self.active_calls[channel_id] = {
            "channel_id": channel_id,
            "caller_number": caller_number,
            "start_time": datetime.now(),
            "company_id": "healthplus",  # Default, can be determined by DID
            "conversation_history": [],
            "is_playing": False,
            "external_media_channel": None
        }
        
        # Answer the call
        await self.answer_channel(channel_id)
        
        # Create external media channel for audio streaming
        await self.create_external_media(channel_id)
        
        # Start audio streaming session
        await self.start_audio_session(channel_id)
    
    async def handle_stasis_end(self, event: Dict[str, Any]):
        """
        Handle call hangup
        """
        channel = event.get("channel", {})
        channel_id = channel.get("id")
        
        logger.info(f"📴 Call ended: {channel_id}")
        
        # Cleanup
        if channel_id in self.active_calls:
            call_info = self.active_calls[channel_id]
            duration = (datetime.now() - call_info["start_time"]).total_seconds()
            
            logger.info(f"Call duration: {duration:.2f} seconds")
            
            # Close audio WebSocket
            if channel_id in self.audio_websockets:
                await self.audio_websockets[channel_id].close()
                del self.audio_websockets[channel_id]
            
            del self.active_calls[channel_id]
    
    async def handle_dtmf(self, event: Dict[str, Any]):
        """
        Handle DTMF (dial tones) input
        """
        digit = event.get("digit")
        channel_id = event.get("channel", {}).get("id")
        
        logger.info(f"DTMF received: {digit} on channel {channel_id}")
        
        # Could be used for menu navigation or triggering actions
    
    async def handle_playback_finished(self, event: Dict[str, Any]):
        """
        Handle playback completion
        """
        playback_id = event.get("playback", {}).get("id")
        logger.debug(f"Playback finished: {playback_id}")
    
    async def answer_channel(self, channel_id: str):
        """
        Answer the incoming call
        """
        if not self.session:
            logger.error("Session not initialized")
            return
        url = f"{self.ari_url}/channels/{channel_id}/answer"
        
        try:
            async with self.session.post(url) as resp:
                if resp.status == 204:
                    logger.info(f"✓ Answered channel {channel_id}")
                else:
                    logger.error(f"Failed to answer channel: {resp.status}")
        except Exception as e:
            logger.error(f"Error answering channel: {e}")
    
    async def create_external_media(self, channel_id: str):
        """
        Create external media channel for audio streaming
        """
        if not self.session:
            logger.error("Session not initialized")
            return
        url = f"{self.ari_url}/channels/externalMedia"
        
        # External media configuration
        payload = {
            "app": self.app_name,
            "external_host": f"{self.websocket_url}/ws/telephony/{channel_id}",
            "format": "slin16",  # 16-bit PCM, 8kHz
            "channelId": f"external-{channel_id}",
            "variables": {
                "CHANNEL_ID": channel_id
            }
        }
        
        try:
            async with self.session.post(url, json=payload) as resp:
                if resp.status in [200, 201]:
                    data = await resp.json()
                    external_id = data.get("id")
                    
                    logger.info(f"✓ Created external media channel: {external_id}")
                    
                    # Store external media channel ID
                    if channel_id in self.active_calls:
                        self.active_calls[channel_id]["external_media_channel"] = external_id
                    
                    # Bridge the channels
                    await self.bridge_channels(channel_id, external_id)
                else:
                    logger.error(f"Failed to create external media: {resp.status}")
                    error_text = await resp.text()
                    logger.error(f"Error details: {error_text}")
        
        except Exception as e:
            logger.error(f"Error creating external media: {e}")
    
    async def bridge_channels(self, channel1_id: str, channel2_id: str):
        """
        Bridge two channels together for audio flow
        """
        if not self.session:
            logger.error("Session not initialized")
            return None
        url = f"{self.ari_url}/bridges"
        
        # Create bridge
        payload = {
            "type": "mixing",
            "name": f"bridge-{channel1_id}"
        }
        
        try:
            async with self.session.post(url, json=payload) as resp:
                if resp.status in [200, 201]:
                    data = await resp.json()
                    bridge_id = data.get("id")
                    
                    logger.info(f"✓ Created bridge: {bridge_id}")
                    
                    # Add both channels to bridge
                    await self.add_channel_to_bridge(bridge_id, channel1_id)
                    await self.add_channel_to_bridge(bridge_id, channel2_id)
                    
                    return bridge_id
                else:
                    logger.error(f"Failed to create bridge: {resp.status}")
        
        except Exception as e:
            logger.error(f"Error creating bridge: {e}")
    
    async def add_channel_to_bridge(self, bridge_id: str, channel_id: str):
        """
        Add a channel to an existing bridge
        """
        if not self.session:
            logger.error("Session not initialized")
            return
        url = f"{self.ari_url}/bridges/{bridge_id}/addChannel"
        
        params = {"channel": channel_id}
        
        try:
            async with self.session.post(url, params=params) as resp:
                if resp.status == 204:
                    logger.info(f"✓ Added channel {channel_id} to bridge {bridge_id}")
                else:
                    logger.error(f"Failed to add channel to bridge: {resp.status}")
        except Exception as e:
            logger.error(f"Error adding channel to bridge: {e}")
    
    async def start_audio_session(self, channel_id: str):
        """
        Start audio streaming session with FastAPI
        """
        if not self.session:
            logger.error("Session not initialized")
            return
        ws_url = f"{self.websocket_url}/ws/telephony/{channel_id}"
        
        try:
            # Connect to FastAPI WebSocket
            ws = await self.session.ws_connect(ws_url)
            self.audio_websockets[channel_id] = ws
            
            logger.info(f"✓ Audio streaming session started for {channel_id}")
            
            # Send initial metadata
            metadata = {
                "type": "session_start",
                "channel_id": channel_id,
                "caller_number": self.active_calls[channel_id]["caller_number"],
                "company_id": self.active_calls[channel_id]["company_id"]
            }
            
            await ws.send_json(metadata)
            
        except Exception as e:
            logger.error(f"Error starting audio session: {e}")
    
    async def stop_playback(self, channel_id: str):
        """
        Stop any active audio playback (for barge-in)
        """
        if channel_id not in self.active_calls:
            return
        
        call_info = self.active_calls[channel_id]
        
        if call_info.get("is_playing"):
            # Signal to FastAPI to stop TTS
            if channel_id in self.audio_websockets:
                ws = self.audio_websockets[channel_id]
                await ws.send_json({
                    "type": "stop_playback",
                    "reason": "barge_in"
                })
            
            call_info["is_playing"] = False
            logger.info(f"⏹️ Stopped playback on {channel_id} (barge-in)")
    
    async def hangup_channel(self, channel_id: str):
        """
        Hangup a channel
        """
        if not self.session:
            logger.error("Session not initialized")
            return
        url = f"{self.ari_url}/channels/{channel_id}"
        
        try:
            async with self.session.delete(url) as resp:
                if resp.status == 204:
                    logger.info(f"✓ Hung up channel {channel_id}")
                else:
                    logger.error(f"Failed to hangup channel: {resp.status}")
        except Exception as e:
            logger.error(f"Error hanging up channel: {e}")
    
    async def disconnect(self):
        """
        Cleanup and disconnect
        """
        logger.info("Disconnecting ARI bridge...")
        
        # Close all audio WebSockets
        for ws in self.audio_websockets.values():
            await ws.close()
        
        # Close main WebSocket
        if self.ws:
            await self.ws.close()
        
        # Close session
        if self.session:
            await self.session.close()
        
        logger.info("✓ ARI bridge disconnected")


# Singleton instance
_ari_bridge: Optional[ARIBridge] = None


def get_ari_bridge() -> ARIBridge:
    """
    Get or create ARI bridge instance
    """
    global _ari_bridge
    if _ari_bridge is None:
        _ari_bridge = ARIBridge()
    return _ari_bridge
