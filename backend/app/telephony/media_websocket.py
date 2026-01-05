"""
Real-time Media WebSocket Handler for ARI
Streams audio bidirectionally for low-latency voice interaction
"""
import asyncio
import websockets
import json
import base64
import logging
from typing import Optional, Callable, Any
import wave
import io

logger = logging.getLogger(__name__)


class MediaWebSocketHandler:
    """
    Handles ARI Media WebSocket for real-time audio streaming
    Bidirectional audio: Asterisk ↔ Agent
    """
    
    def __init__(
        self,
        channel_id: str,
        media_url: str,
        on_audio_chunk: Optional[Callable] = None,
        sample_rate: int = 16000,
        format: str = "slin16"
    ):
        self.channel_id = channel_id
        self.media_url = media_url
        self.on_audio_chunk = on_audio_chunk
        self.sample_rate = sample_rate
        self.format = format
        
        self.ws: Optional[Any] = None
        self.connected = False
        self.running = False
        
        # Audio buffers
        self.inbound_buffer = bytearray()
        self.outbound_queue = asyncio.Queue()
        
        logger.info(f"Media WebSocket handler created for channel {channel_id}")
    
    async def connect(self):
        """Connect to ARI Media WebSocket"""
        try:
            logger.info(f"Connecting to media WebSocket: {self.media_url}")
            
            async with websockets.connect(self.media_url) as websocket:
                self.ws = websocket
                self.connected = True
                self.running = True
                
                logger.info(f"✓ Media WebSocket connected for {self.channel_id}")
                
                # Run send and receive concurrently
                await asyncio.gather(
                    self._receive_audio(),
                    self._send_audio(),
                    return_exceptions=True
                )
                
        except Exception as e:
            logger.error(f"Media WebSocket error: {e}", exc_info=True)
        finally:
            self.connected = False
            self.running = False
            logger.info(f"Media WebSocket closed for {self.channel_id}")
    
    async def _receive_audio(self):
        """Receive audio frames from Asterisk"""
        try:
            while self.running and self.ws:
                message = await self.ws.recv()
                
                if isinstance(message, bytes):
                    # Raw audio frame (slin16 format - 16-bit PCM)
                    await self._process_inbound_audio(message)
                elif isinstance(message, str):
                    # Control message (JSON)
                    await self._handle_control_message(message)
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("Media WebSocket receive closed")
        except Exception as e:
            logger.error(f"Error receiving audio: {e}", exc_info=True)
    
    async def _send_audio(self):
        """Send audio frames to Asterisk"""
        try:
            while self.running:
                # Get audio chunk from queue
                audio_chunk = await self.outbound_queue.get()
                
                if audio_chunk is None:  # Stop signal
                    break
                
                if self.ws and self.connected:
                    # Send raw audio bytes (slin16 format)
                    await self.ws.send(audio_chunk)
                    
        except Exception as e:
            logger.error(f"Error sending audio: {e}", exc_info=True)
    
    async def _process_inbound_audio(self, audio_data: bytes):
        """Process incoming audio from caller"""
        # Add to buffer
        self.inbound_buffer.extend(audio_data)
        
        # Process in chunks (e.g., 20ms frames at 16kHz = 640 bytes)
        chunk_size = 640  # 20ms of slin16 audio
        
        while len(self.inbound_buffer) >= chunk_size:
            chunk = bytes(self.inbound_buffer[:chunk_size])
            self.inbound_buffer = self.inbound_buffer[chunk_size:]
            
            # Send to STT streaming service
            if self.on_audio_chunk:
                await self.on_audio_chunk(chunk)
    
    async def _handle_control_message(self, message: str):
        """Handle control messages from ARI"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "start":
                logger.info("Media stream started")
            elif msg_type == "stop":
                logger.info("Media stream stopped")
                self.running = False
                
        except Exception as e:
            logger.error(f"Error handling control message: {e}")
    
    async def send_audio(self, audio_data: bytes):
        """Queue audio to send to caller (TTS output)"""
        if self.running:
            await self.outbound_queue.put(audio_data)
    
    async def send_audio_file(self, audio_file_path: str):
        """Send entire audio file (for TTS output)"""
        try:
            with wave.open(audio_file_path, 'rb') as wav:
                # Ensure format matches
                if wav.getsampwidth() != 2 or wav.getnchannels() != 1:
                    logger.warning(f"Audio format mismatch: {wav.getsampwidth()}byte, {wav.getnchannels()}ch")
                
                # Read and send in chunks
                chunk_size = 640  # 20ms
                while True:
                    audio_chunk = wav.readframes(320)  # 320 samples = 640 bytes
                    if not audio_chunk:
                        break
                    await self.send_audio(audio_chunk)
                    
        except Exception as e:
            logger.error(f"Error sending audio file: {e}", exc_info=True)
    
    async def stop_playback(self):
        """Stop current playback (for barge-in)"""
        # Clear outbound queue
        while not self.outbound_queue.empty():
            try:
                self.outbound_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        logger.info("Playback stopped (barge-in)")
    
    async def disconnect(self):
        """Disconnect media WebSocket"""
        self.running = False
        
        # Send stop signal to send task
        await self.outbound_queue.put(None)
        
        if self.ws:
            await self.ws.close()
        
        logger.info(f"Media WebSocket disconnected for {self.channel_id}")
