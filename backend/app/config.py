import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parents[2]

# Active company (used later for KB switching)
ACTIVE_COMPANY = os.getenv("ACTIVE_COMPANY", "healthplus")

# Logs directory and file
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "app.log"

# Ensure logs directory exists
LOG_DIR.mkdir(exist_ok=True)

# Data directory for vector store indexes
DATA_DIR = BASE_DIR / "backend" / "data"
DATA_DIR.mkdir(exist_ok=True)

# Companies directory for knowledge base
COMPANIES_DIR = BASE_DIR / "companies"

# Google Gemini API configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash")

# RAG Configuration
RAG_ENABLED = os.getenv("RAG_ENABLED", "true").lower() == "true"
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))  # Number of documents to retrieve
RAG_MAX_CONTEXT_LENGTH = int(os.getenv("RAG_MAX_CONTEXT_LENGTH", "2000"))  # Max context chars
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")  # Sentence Transformer model

# TTS Configuration
TTS_ENABLED = os.getenv("TTS_ENABLED", "true").lower() == "true"
TTS_LANGUAGE = os.getenv("TTS_LANGUAGE", "en")
PRELOAD_TTS = os.getenv("PRELOAD_TTS", "false").lower() == "true"

# Asterisk ARI Configuration
ARI_URL = os.getenv("ARI_URL", "http://localhost:8088/ari")
ARI_USERNAME = os.getenv("ARI_USERNAME", "aiagent")
ARI_PASSWORD = os.getenv("ARI_PASSWORD", "strongpassword")
ARI_APP_NAME = os.getenv("ARI_APP_NAME", "ai_voice_agent")
WEBSOCKET_URL = os.getenv("WEBSOCKET_URL", "ws://localhost:8088/ari/events")
