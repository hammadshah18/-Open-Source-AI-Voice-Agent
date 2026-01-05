from typing import Optional, List, Dict
import google.generativeai as genai
from ..config import GEMINI_API_KEY, GEMINI_MODEL, RAG_ENABLED, RAG_TOP_K, ACTIVE_COMPANY, COMPANIES_DIR
from ..logger import logger
from ..rag.vector_store import RAGSystem
from pathlib import Path

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)  # type: ignore

# Initialize RAG System (singleton)
_rag_system = None

def get_rag_system():
    """
    Lazy load RAG system
    """
    global _rag_system
    if _rag_system is None and RAG_ENABLED:
        logger.info("Initializing RAG system...")
        _rag_system = RAGSystem(companies_dir=COMPANIES_DIR)
        # Load default company
        _rag_system.load_company(ACTIVE_COMPANY)
    return _rag_system

def generate_response(user_text: str, system_prompt: Optional[str] = None, company_id: Optional[str] = None) -> str:
    """
    Generates a response using Google Gemini API with RAG.
    
    Args:
        user_text (str): The user's input text (from STT)
        system_prompt (str): Optional system prompt for context
        company_id (str): Company ID for RAG retrieval (uses ACTIVE_COMPANY if not provided)
        
    Returns:
        str: Generated response from LLM
    """
    try:
        logger.info(f"Generating LLM response for input: {user_text}")
        
        # Initialize model for each request
        model = genai.GenerativeModel(model_name=GEMINI_MODEL)  # type: ignore
        
        # RAG: Retrieve relevant context
        retrieved_context = ""
        if RAG_ENABLED:
            rag_system = get_rag_system()
            
            # Check if RAG system is available
            if rag_system is not None:
                # Switch company if needed
                target_company = company_id or ACTIVE_COMPANY
                if rag_system.current_company != target_company:
                    logger.info(f"Switching RAG to company: {target_company}")
                    rag_system.switch_company(target_company)
                
                # Retrieve relevant knowledge
                retrieved_context = rag_system.retrieve(user_text, top_k=RAG_TOP_K)
                
                if retrieved_context:
                    logger.info(f"Retrieved context: {len(retrieved_context)} characters")
                else:
                    logger.warning("No relevant context found for query")
            else:
                logger.warning("RAG system not initialized")
        
        # Prepare the prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\nUser: {user_text}\n\nAssistant:"
        else:
            # Build knowledge-grounded system prompt
            if retrieved_context:
                default_system = f"""You are a professional AI voice customer support agent with expertise in customer service.

INSTRUCTIONS:
- PRIORITIZE information from the company knowledge base provided below
- Use your general customer service expertise to provide helpful, complete answers
- Combine company-specific information with best practices in customer support
- Be polite, professional, empathetic, and conversational
- Provide clear, concise, and actionable responses
- If company information is incomplete, supplement with helpful general guidance while noting what's company-specific
- Always maintain a friendly, helpful tone suitable for voice conversations

COMPANY KNOWLEDGE BASE:
{retrieved_context}

Use the above company information as your primary source, and enhance your response with professional customer service knowledge where appropriate."""
            else:
                # Fallback when no context is found - still be helpful
                default_system = """You are a professional AI voice customer support agent with expertise in customer service.

INSTRUCTIONS:
- The specific company information for this query is not available in the knowledge base
- Provide helpful general customer service guidance based on your expertise
- Be professional, empathetic, and supportive
- Offer to help with other questions or suggest contacting the company directly for specific details
- Maintain a friendly, conversational tone suitable for voice interactions
- Focus on being as helpful as possible within reasonable boundaries"""
            
            full_prompt = f"{default_system}\n\nCustomer: {user_text}\n\nAgent:"
        
        # Generate response
        response = model.generate_content(full_prompt)
        
        generated_text = response.text.strip()
        
        logger.info(f"LLM response generated: {generated_text}")
        
        return generated_text
    
    except Exception as e:
        logger.error(f"Error generating LLM response: {e}")
        return "I apologize, but I'm having trouble processing your request right now. Please try again."


def generate_response_with_context(user_text: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
    """
    Generates a response with conversation context.
    
    Args:
        user_text (str): The user's input text
        conversation_history (list): List of previous messages [{"role": "user", "content": "..."}, ...]
        
    Returns:
        str: Generated response from LLM
    """
    try:
        logger.info(f"Generating contextual LLM response for input: {user_text}")
        
        # Initialize model for each request
        model = genai.GenerativeModel(model_name=GEMINI_MODEL)  # type: ignore
        
        # Build conversation context
        system_prompt = """You are a professional AI voice customer support agent with expertise in customer service and call center operations.
You have access to company knowledge and general customer service best practices.
Be polite, professional, empathetic, and conversational.
Provide clear, helpful, and actionable answers.
Use both company-specific information and your customer service expertise to assist customers effectively."""
        
        # Start chat with history
        chat = model.start_chat(history=[])
        
        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history:
                if msg.get("role") == "user":
                    chat.send_message(msg.get("content", ""))
        
        # Send current message
        response = chat.send_message(f"{system_prompt}\n\n{user_text}")
        
        generated_text = response.text.strip()
        
        logger.info(f"Contextual LLM response generated: {generated_text}")
        
        return generated_text
    
    except Exception as e:
        logger.error(f"Error generating contextual LLM response: {e}")
        return "I apologize, but I'm having trouble processing your request right now. Please try again."
