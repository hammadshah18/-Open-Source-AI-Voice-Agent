#!/bin/bash
#==============================================================================
# AI Voice Agent Telephony Service Startup Script
#==============================================================================

echo "=========================================================================="
echo "  AI VOICE AGENT - TELEPHONY SERVICE"
echo "=========================================================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Asterisk is running
echo -n "Checking Asterisk status... "
if pgrep asterisk > /dev/null; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not running${NC}"
    echo ""
    echo "Please start Asterisk first:"
    echo "  sudo systemctl start asterisk"
    echo "  OR"
    echo "  sudo asterisk -c"
    exit 1
fi

# Check Asterisk configuration
echo -n "Checking Asterisk configuration... "
if asterisk -rx "ari show status" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ ARI enabled${NC}"
else
    echo -e "${RED}✗ ARI not configured${NC}"
    echo ""
    echo "Please configure Asterisk ARI:"
    echo "  sudo cp asterisk-config/*.conf /etc/asterisk/"
    echo "  sudo asterisk -rx 'core reload'"
    exit 1
fi

# Check Python version
echo -n "Checking Python 3.10... "
if command -v python3.10 &> /dev/null; then
    echo -e "${GREEN}✓ Found${NC}"
    PYTHON_CMD="python3.10"
elif command -v python3 &> /dev/null; then
    PY_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    if [ "$PY_VERSION" == "3.10" ]; then
        echo -e "${GREEN}✓ Found (as python3)${NC}"
        PYTHON_CMD="python3"
    else
        echo -e "${YELLOW}⚠ Using Python $PY_VERSION instead of 3.10${NC}"
        PYTHON_CMD="python3"
    fi
else
    echo -e "${RED}✗ Not found${NC}"
    exit 1
fi

# Navigate to backend directory
cd backend || exit 1

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo -n "Activating virtual environment... "
    source venv/bin/activate
    echo -e "${GREEN}✓ Activated${NC}"
else
    echo -e "${YELLOW}No virtual environment found. Installing dependencies globally...${NC}"
fi

# Install/update dependencies
echo ""
echo "Installing dependencies..."
$PYTHON_CMD -m pip install -q -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Create necessary directories
mkdir -p logs/call_audio
echo -e "${GREEN}✓ Created log directories${NC}"

echo ""
echo "=========================================================================="
echo ""
echo -e "${GREEN}Starting FastAPI backend with telephony support...${NC}"
echo ""
echo "  API Documentation: http://localhost:8000/docs"
echo "  Telephony Status:  http://localhost:8000/telephony/status"
echo "  Health Check:      http://localhost:8000/telephony/health"
echo ""
echo "=========================================================================="
echo ""
echo "📞 To test with Zoiper:"
echo "   1. Configure Zoiper: server=localhost, user=6001, password=zoiper123"
echo "   2. Dial 7000 from Zoiper to talk to AI"
echo ""
echo "📡 To make outbound call:"
echo "   curl -X POST http://localhost:8000/telephony/calls/outbound \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"phone_number\": \"6001\"}'"
echo ""
echo "=========================================================================="
echo ""

# Start the server
$PYTHON_CMD -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
