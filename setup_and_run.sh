#!/bin/bash
# ==================================================================
# Complete Setup Script for AI Voice Agent with Mobile Phone Access
# ==================================================================

echo ""
echo "=================================================================="
echo "  AI VOICE AGENT - COMPLETE SETUP"
echo "  Mobile Phone Integration"
echo "=================================================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root for some commands
if [ "$EUID" -ne 0 ]; then 
    echo -e "${YELLOW}Note: Some steps may require sudo password${NC}"
fi

# Step 1: Check Asterisk
echo ""
echo "[1/8] Checking Asterisk status..."
if systemctl is-active --quiet asterisk; then
    echo -e "${GREEN}✓ Asterisk is running${NC}"
else
    echo -e "${RED}✗ Asterisk is not running${NC}"
    echo "Starting Asterisk..."
    sudo systemctl start asterisk
    sleep 2
    if systemctl is-active --quiet asterisk; then
        echo -e "${GREEN}✓ Asterisk started${NC}"
    else
        echo -e "${RED}✗ Failed to start Asterisk${NC}"
        exit 1
    fi
fi

# Step 2: Check ARI connection
echo ""
echo "[2/8] Testing ARI connection..."
if curl -s -u aiagent:strongpassword http://localhost:8088/ari/api-docs/resources.json > /dev/null 2>&1; then
    echo -e "${GREEN}✓ ARI is accessible${NC}"
else
    echo -e "${RED}✗ Cannot connect to ARI${NC}"
    echo "Check /etc/asterisk/ari.conf and /etc/asterisk/http.conf"
    exit 1
fi

# Step 3: Check dialplan
echo ""
echo "[3/8] Checking dialplan configuration..."
if sudo asterisk -rx "dialplan show from-internal" | grep -q "9000"; then
    echo -e "${GREEN}✓ Extension 9000 is configured${NC}"
else
    echo -e "${YELLOW}⚠ Extension 9000 not found in dialplan${NC}"
    echo "Please add it to /etc/asterisk/extensions.conf"
    echo ""
    echo "Add this:"
    echo "[from-internal]"
    echo "exten => 9000,1,NoOp(=== AI Voice Agent ===)"
    echo " same => n,Answer()"
    echo " same => n,Stasis(voiceagent)"
    echo " same => n,Hangup()"
    echo ""
    read -p "Press Enter after adding the dialplan, or Ctrl+C to exit..."
    sudo asterisk -rx "dialplan reload"
fi

# Step 4: Check PJSIP endpoint
echo ""
echo "[4/8] Checking PJSIP endpoint..."
if sudo asterisk -rx "pjsip show endpoints" | grep -q "6001"; then
    echo -e "${GREEN}✓ SIP endpoint 6001 is configured${NC}"
else
    echo -e "${YELLOW}⚠ SIP endpoint 6001 not found${NC}"
    echo "Please add it to /etc/asterisk/pjsip.conf"
    echo ""
    echo "See CALL_FROM_MOBILE.md for full configuration"
fi

# Step 5: Check firewall
echo ""
echo "[5/8] Checking firewall configuration..."
if command -v ufw &> /dev/null; then
    if sudo ufw status | grep -q "5060"; then
        echo -e "${GREEN}✓ Port 5060 is open${NC}"
    else
        echo -e "${YELLOW}⚠ Opening port 5060 for SIP...${NC}"
        sudo ufw allow 5060/udp
    fi
    
    if sudo ufw status | grep -q "10000:20000"; then
        echo -e "${GREEN}✓ RTP ports are open${NC}"
    else
        echo -e "${YELLOW}⚠ Opening RTP ports 10000-20000...${NC}"
        sudo ufw allow 10000:20000/udp
    fi
else
    echo -e "${YELLOW}⚠ UFW not installed, skipping firewall check${NC}"
fi

# Step 6: Get server IP
echo ""
echo "[6/8] Getting server IP address..."
SERVER_IP=$(hostname -I | awk '{print $1}')
echo -e "${GREEN}Your server IP: $SERVER_IP${NC}"
echo ""
echo "Use this IP in your mobile SIP app configuration:"
echo "  Server: $SERVER_IP"
echo "  Username: 6001"
echo "  Password: test1234"
echo "  Port: 5060"

# Step 7: Test Python environment
echo ""
echo "[7/8] Checking Python environment..."
if command -v python3.10 &> /dev/null; then
    echo -e "${GREEN}✓ Python 3.10 is available${NC}"
else
    echo -e "${RED}✗ Python 3.10 not found${NC}"
    echo "Install Python 3.10 first"
    exit 1
fi

# Check required packages
echo "Checking Python packages..."
python3.10 -c "import aiohttp" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ aiohttp installed${NC}"
else
    echo -e "${YELLOW}⚠ Installing aiohttp...${NC}"
    python3.10 -m pip install aiohttp
fi

python3.10 -c "import scipy" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ scipy installed${NC}"
else
    echo -e "${YELLOW}⚠ scipy not installed${NC}"
    echo "For production integration, install: pip install scipy numpy"
fi

# Step 8: Ready to start
echo ""
echo "[8/8] Setup complete!"
echo ""
echo "=================================================================="
echo "  READY TO START"
echo "=================================================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Configure your mobile SIP app:"
echo "   - Server: $SERVER_IP"
echo "   - Username: 6001"
echo "   - Password: test1234"
echo "   - Port: 5060"
echo ""
echo "2. Start the AI Voice Agent:"
echo "   ${GREEN}python3.10 simple_ari_integration.py${NC}"
echo ""
echo "3. From your mobile SIP app, dial: ${GREEN}9000${NC}"
echo ""
echo "4. Enjoy talking to your AI agent!"
echo ""
echo "For detailed instructions, see: CALL_FROM_MOBILE.md"
echo ""
echo "=================================================================="
echo ""

# Offer to start the integration
read -p "Do you want to start the AI Voice Agent now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Starting AI Voice Agent..."
    echo "Press Ctrl+C to stop"
    echo ""
    python3.10 simple_ari_integration.py
fi
