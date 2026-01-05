#!/bin/bash
#==============================================================================
# AI Voice Agent - Production Start Script
# Starts Asterisk + FastAPI Backend
#==============================================================================

set -e

echo "=========================================="
echo "AI Voice Agent - Starting System"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
ASTERISK_CONFIG_DIR="./asterisk-config"
BACKEND_DIR="./backend"
ARI_APP_NAME="ai_voice_agent"

echo ""
echo "Step 1: Checking Asterisk installation..."
if ! command -v asterisk &> /dev/null; then
    echo -e "${RED}✗ Asterisk not found${NC}"
    echo "Install with: sudo apt install asterisk"
    exit 1
fi
echo -e "${GREEN}✓ Asterisk found$(NC)"

echo ""
echo "Step 2: Copying Asterisk configuration..."
if [ "$EUID" -eq 0 ]; then
    # Running as root
    cp ${ASTERISK_CONFIG_DIR}/*.conf /etc/asterisk/
    echo -e "${GREEN}✓ Configuration copied${NC}"
else
    # Need sudo
    sudo cp ${ASTERISK_CONFIG_DIR}/*.conf /etc/asterisk/
    echo -e "${GREEN}✓ Configuration copied (sudo)${NC}"
fi

echo ""
echo "Step 3: Starting/Reloading Asterisk..."
if [ "$EUID" -eq 0 ]; then
    systemctl restart asterisk
    sleep 2
    asterisk -rx "core reload"
    asterisk -rx "ari show status"
    asterisk -rx "ari show apps"
else
    sudo systemctl restart asterisk
    sleep 2
    sudo asterisk -rx "core reload"
    sudo asterisk -rx "ari show status"
    sudo asterisk -rx "ari show apps"
fi
echo -e "${GREEN}✓ Asterisk running${NC}"

echo ""
echo "Step 4: Starting FastAPI backend..."
cd ${BACKEND_DIR}

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "Using virtual environment..."
    source venv/bin/activate
fi

# Install dependencies if needed
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

echo ""
echo -e "${GREEN}Starting server on http://0.0.0.0:8000${NC}"
echo -e "${YELLOW}Press CTRL+C to stop${NC}"
echo ""

# Start uvicorn
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info
