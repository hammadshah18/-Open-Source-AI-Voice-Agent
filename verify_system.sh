#!/bin/bash
#==============================================================================
# AI Voice Agent - System Verification
# Run this in WSL to verify all components
#==============================================================================

echo "=========================================="
echo "AI Voice Agent - System Verification"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0

# Test function
test_component() {
    local name=$1
    local command=$2
    
    echo -n "Testing $name... "
    
    if eval "$command" &> /dev/null; then
        echo -e "${GREEN}✓ PASS${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC}"
        ((FAILED++))
        return 1
    fi
}

echo "1. System Components"
echo "--------------------"
test_component "Asterisk installed" "command -v asterisk"
test_component "Python 3 installed" "command -v python3"
test_component "pip installed" "command -v pip3"
echo ""

echo "2. Asterisk Service"
echo "-------------------"
test_component "Asterisk running" "sudo systemctl is-active asterisk"
echo ""

if command -v asterisk &> /dev/null; then
    echo "3. ARI Configuration"
    echo "--------------------"
    
    # Check ARI status
    echo "ARI Status:"
    sudo asterisk -rx "ari show status" 2>/dev/null || echo "  (Need sudo access)"
    echo ""
    
    # Check registered apps
    echo "Registered Stasis Apps:"
    sudo asterisk -rx "ari show apps" 2>/dev/null || echo "  (Need sudo access)"
    echo ""
    
    # Check HTTP server
    echo "HTTP Server Status:"
    sudo asterisk -rx "http show status" 2>/dev/null || echo "  (Need sudo access)"
    echo ""
fi

echo "4. Python Dependencies"
echo "----------------------"
cd backend 2>/dev/null || cd /mnt/e/AI-Voice-Agent/backend 2>/dev/null

test_component "FastAPI" "python3 -c 'import fastapi'"
test_component "uvicorn" "python3 -c 'import uvicorn'"
test_component "websockets" "python3 -c 'import websockets'"
test_component "aiohttp" "python3 -c 'import aiohttp'"
echo ""

echo "5. Configuration Files"
echo "----------------------"
cd .. 2>/dev/null
test_component "ari.conf" "test -f asterisk-config/ari.conf"
test_component "extensions.conf" "test -f asterisk-config/extensions.conf"
test_component "http.conf" "test -f asterisk-config/http.conf"
echo ""

echo "6. Backend Structure"
echo "--------------------"
test_component "main.py" "test -f backend/app/main.py"
test_component "ari_websocket.py" "test -f backend/app/telephony/ari_websocket.py"
test_component "call_manager.py" "test -f backend/app/telephony/call_manager.py"
echo ""

echo "=========================================="
echo "Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "Ready to start:"
    echo "  ./start_production.sh"
    echo ""
    echo "Or manually:"
    echo "  cd backend"
    echo "  python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
    exit 0
else
    echo -e "${RED}✗ Some checks failed${NC}"
    echo ""
    echo "Fix issues and run again."
    exit 1
fi
