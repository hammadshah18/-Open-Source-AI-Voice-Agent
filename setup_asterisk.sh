#!/bin/bash
#==============================================================================
# Quick Setup Script for Asterisk Telephony Integration
# For Ubuntu/Debian systems
#==============================================================================

set -e

echo "========================================================================"
echo "  AI VOICE AGENT - ASTERISK TELEPHONY SETUP"
echo "========================================================================"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (use sudo)"
   exit 1
fi

echo "📦 Step 1: Installing dependencies..."
apt update
apt install -y build-essential git wget curl libssl-dev libncurses5-dev \
    libnewt-dev libxml2-dev linux-headers-$(uname -r) libsqlite3-dev \
    uuid-dev libjansson-dev

echo ""
echo "📥 Step 2: Downloading Asterisk..."
cd /usr/src
if [ ! -f "asterisk-20-current.tar.gz" ]; then
    wget https://downloads.asterisk.org/pub/telephony/asterisk/asterisk-20-current.tar.gz
fi

echo ""
echo "📦 Step 3: Extracting Asterisk..."
tar xzf asterisk-20-current.tar.gz
cd asterisk-20*/

echo ""
echo "🔧 Step 4: Configuring Asterisk..."
contrib/scripts/get_mp3_source.sh || true
./configure --with-jansson-bundled

echo ""
echo "⚙️  Step 5: Selecting modules..."
echo "   Enabling ARI and PJSIP modules..."
make menuselect.makeopts
menuselect/menuselect \
    --enable res_ari --enable res_ari_applications --enable res_ari_asterisk \
    --enable res_ari_bridges --enable res_ari_channels --enable res_ari_device_states \
    --enable res_ari_endpoints --enable res_ari_events --enable res_ari_playbacks \
    --enable res_ari_recordings --enable res_ari_sounds \
    --enable chan_pjsip --enable res_pjsip --enable res_pjsip_session \
    menuselect.makeopts

echo ""
echo "🔨 Step 6: Compiling Asterisk (this takes 10-20 minutes)..."
make -j$(nproc)

echo ""
echo "📦 Step 7: Installing Asterisk..."
make install
make samples
make config
ldconfig

echo ""
echo "👤 Step 8: Creating asterisk user..."
if ! id asterisk &>/dev/null; then
    useradd -m -s /bin/bash -G audio asterisk
fi

echo ""
echo "🔐 Step 9: Setting permissions..."
chown -R asterisk:asterisk /etc/asterisk
chown -R asterisk:asterisk /var/lib/asterisk
chown -R asterisk:asterisk /var/log/asterisk
chown -R asterisk:asterisk /var/spool/asterisk
chown -R asterisk:asterisk /usr/lib/asterisk

echo ""
echo "🔥 Step 10: Configuring firewall..."
ufw allow 5060/udp comment "SIP"
ufw allow 10000:20000/udp comment "RTP"
ufw allow 8088/tcp comment "ARI HTTP"

echo ""
echo "========================================================================"
echo "✅ Asterisk installation complete!"
echo "========================================================================"
echo ""
echo "Next steps:"
echo "1. Copy configuration files:"
echo "   sudo cp asterisk-config/*.conf /etc/asterisk/"
echo ""
echo "2. Start Asterisk:"
echo "   sudo systemctl start asterisk"
echo ""
echo "3. Verify ARI:"
echo "   curl -u asterisk:asterisk http://localhost:8088/ari/api-docs/resources.json"
echo ""
echo "4. See full guide: docs/telephony.md"
echo ""
