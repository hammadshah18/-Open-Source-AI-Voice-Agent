"""
Streaming LLM Service with Google Gemini
Generates responses in real-time with streaming output
"""
import asyncio
import logging
from typing import Optional, Callable, AsyncIterator
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None  # type: ignore

from ..config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)


class StreamingLLM:
    """
    Real-time LLM response generation with streaming
    Allows TTS to begin before full response is complete
    """
    
    def __init__(
        self,
        on_chunk: Optional[Callable] = None,
        on_complete: Optional[Callable] = None
    ):
        self.on_chunk = on_chunk
        self.on_complete = on_complete
        self.model = None
        
    async def initialize(self):
        """Initialize Gemini model"""
        try:
            if not GENAI_AVAILABLE or not genai:
                raise ImportError("google-generativeai not installed")
            
            if GEMINI_API_KEY:
                genai.configure(api_key=GEMINI_API_KEY)  # type: ignore
                self.model = genai.GenerativeModel(GEMINI_MODEL)  # type: ignore
                logger.info("✓ Gemini LLM initialized")
            else:
                logger.warning("GEMINI_API_KEY not set - using mock responses")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            logger.warning("LLM will use mock responses")
        
        self.conversation_history = []
        logger.info("Streaming LLM initialized")
    
    async def generate_response_stream(
        self,
        user_message: str,
        context: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> AsyncIterator[str]:
        """
        Generate streaming response
        Yields text chunks as they're generated
        """
        try:
            # Add user message to history
            self.conversation_history.append({
                "role": "user",
                "text": user_message
            })
            
            # Build prompt
            prompt = self._build_prompt(user_message, context, system_prompt)
            
            if not self.model:
                # Mock streaming response for testing
                mock_response = "I understand. How else can I assist you today?"
                for word in mock_response.split():
                    yield word + " "
                    await asyncio.sleep(0.05)  # Simulate streaming delay
                return
            
            # Stream from Gemini
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                stream=True
            )
            
            full_response = ""
            
            for chunk in response:
                if chunk.text:
                    text = chunk.text
                    full_response += text
                    
                    # Yield chunk for TTS
                    yield text
                    
                    # Callback
                    if self.on_chunk:
                        await self.on_chunk(text)
            
            # Add to history
            self.conversation_history.append({
                "role": "assistant",
                "text": full_response
            })
            
            logger.info(f"🤖 LLM: {full_response}")
            
            # Complete callback
            if self.on_complete:
                await self.on_complete(full_response)
                
        except Exception as e:
            logger.error(f"LLM error: {e}", exc_info=True)
            # Fallback response
            fallback = "I apologize, I encountered an error. Could you please repeat that?"
            yield fallback
    
    def _build_prompt(
        self,
        user_message: str,
        context: Optional[str] = None,
        system_prompt: Optional[str] = None
    ) -> str:
        """Build prompt with context and history"""
        parts = []
        
        # System prompt
        if system_prompt:
            parts.append(system_prompt)
        else:
            parts.append(
                "You are a helpful AI voice assistant. "
                "Provide concise, natural responses suitable for voice conversation. "
                "Keep responses under 50 words when possible."
            )
        
        # RAG context
        if context:
            parts.append(f"\nRelevant information:\n{context}")
        
        # Conversation history (last 4 turns)
        if self.conversation_history:
            parts.append("\nConversation history:")
            for msg in self.conversation_history[-4:]:
                role = msg["role"].upper()
                text = msg["text"]
                parts.append(f"{role}: {text}")
        
        # Current message
        parts.append(f"\nUSER: {user_message}")
        parts.append("\nASSISTANT:")
        
        return "\n".join(parts)
    
    def reset_conversation(self):
        """Clear conversation history"""
        self.conversation_history.clear()
        logger.debug("Conversation history cleared")
    
    def get_conversation_history(self):
        """Get current conversation history"""
        return self.conversation_history.copy()
