"""
WebSocket endpoint for web-based voice calls
Handles real-time audio streaming from browser
"""
import asyncio
import logging
import base64
import io
import wave
import audioop
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..stt import whisper_stt
from ..llm import dialog_manager
from ..tts import coqui_tts

logger = logging.getLogger(__name__)
router = APIRouter()

# Store active web calls
active_web_calls = {}


@router.websocket("/ws/call")
async def websocket_call_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for web-based voice calls
    Receives audio from browser, processes with STT/LLM/TTS, sends back response
    """
    await websocket.accept()
    call_id = id(websocket)
    
    logger.info(f"🌐 Web call connected: {call_id}")
    
    try:
        # Services are module-level functions, no need to initialize
        
        # Store call session
        audio_buffer = bytearray()
        
        active_web_calls[call_id] = {
            'conversation': [],
            'audio_buffer': audio_buffer,
            'is_processing': False
        }
        
        # Send greeting
        greeting = "Hello! How can I help you today?"
        greeting_audio = await generate_audio(greeting)
        
        await websocket.send_json({
            'type': 'greeting',
            'text': greeting,
            'audio': greeting_audio
        })
        
        active_web_calls[call_id]['conversation'].append({
            'role': 'assistant',
            'text': greeting
        })
        
        logger.info("✓ Web call initialized, waiting for audio...")
        
        # Receive audio stream
        while True:
            data = await websocket.receive()
            
            if 'bytes' in data:
                # Audio chunk from browser (WebM/Opus format)
                audio_chunk = data['bytes']
                
                # Add to buffer
                audio_buffer.extend(audio_chunk)
                
                # Process when we have enough audio (2 seconds worth)
                if len(audio_buffer) > 32000 and not active_web_calls[call_id]['is_processing']:
                    active_web_calls[call_id]['is_processing'] = True
                    
                    # Process accumulated audio
                    await process_audio_buffer(
                        websocket,
                        call_id,
                        bytes(audio_buffer)
                    )
                    
                    # Clear buffer
                    audio_buffer.clear()
                    active_web_calls[call_id]['is_processing'] = False
                    
            elif 'text' in data:
                # Control messages
                import json
                msg = json.loads(data['text'])
                
                if msg.get('type') == 'end_call':
                    break
    
    except WebSocketDisconnect:
        logger.info(f"🌐 Web call disconnected: {call_id}")
    except Exception as e:
        logger.error(f"Error in web call: {e}", exc_info=True)
        try:
            await websocket.send_json({
                'type': 'error',
                'message': str(e)
            })
        except:
            pass
    finally:
        # Cleanup
        if call_id in active_web_calls:
            del active_web_calls[call_id]
        
        logger.info(f"🌐 Web call ended: {call_id}")


async def process_audio_buffer(websocket, call_id, audio_data):
    """Process audio buffer and generate response"""
    try:
        logger.info(f"Processing audio buffer: {len(audio_data)} bytes")
        
        # Save to temporary WAV file for STT
        import tempfile
        import os
        
        # Audio data is already in WAV format from browser
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp.write(audio_data)
            wav_path = tmp.name
        
        # Transcribe
        await websocket.send_json({
            'type': 'status',
            'status': 'processing',
            'message': '👂 Listening...'
        })
        
        transcript = await asyncio.to_thread(whisper_stt.transcribe_audio, wav_path)
        
        # Cleanup temp file
        try:
            os.unlink(wav_path)
        except:
            pass
        
        if not transcript or not transcript.strip():
            logger.warning("No speech detected")
            await websocket.send_json({
                'type': 'status',
                'status': 'active',
                'message': '🎙️ Speak now!'
            })
            return
        
        logger.info(f"👤 User said: {transcript}")
        
        # Send transcript to UI
        await websocket.send_json({
            'type': 'transcript',
            'text': transcript
        })
        
        # Add to conversation
        active_web_calls[call_id]['conversation'].append({
            'role': 'user',
            'text': transcript
        })
        
        # Generate response
        await websocket.send_json({
            'type': 'status',
            'status': 'processing',
            'message': '🤔 Thinking...'
        })
        
        response_text = await asyncio.to_thread(
            dialog_manager.generate_response,
            transcript
        )
        
        logger.info(f"🤖 Agent responds: {response_text}")
        
        # Generate audio
        response_audio = await generate_audio(response_text)
        
        # Send response
        await websocket.send_json({
            'type': 'response',
            'text': response_text,
            'audio': response_audio
        })
        
        active_web_calls[call_id]['conversation'].append({
            'role': 'assistant',
            'text': response_text
        })
        
        await websocket.send_json({
            'type': 'status',
            'status': 'active',
            'message': '🎙️ Your turn - Speak now!'
        })
        
    except Exception as e:
        logger.error(f"Error processing audio: {e}", exc_info=True)
        await websocket.send_json({
            'type': 'error',
            'message': 'Could not process audio. Please try again.'
        })


async def generate_audio(text: str) -> str:
    """Generate audio and return as base64"""
    try:
        import tempfile
        import os
        
        # Generate to temp file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp_path = tmp.name
        
        # Use the module-level function
        await asyncio.to_thread(coqui_tts.synthesize_speech, text, tmp_path)
        
        # Read and encode as base64
        with open(tmp_path, 'rb') as f:
            audio_data = f.read()
        
        # Cleanup
        os.unlink(tmp_path)
        
        return base64.b64encode(audio_data).decode('utf-8')
    
    except Exception as e:
        logger.error(f"Error generating audio: {e}")
        return ""
