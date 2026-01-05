# 📞 ASTERISK TELEPHONY INTEGRATION GUIDE

## 🎯 Overview

This guide covers the complete Asterisk telephony integration for the AI Voice Agent. After following this guide, your system will handle **real phone calls** with:

✅ Automatic call answering
✅ Real-time speech recognition (Whisper)  
✅ RAG-powered responses (FAISS + Sentence Transformers)
✅ Natural voice synthesis (Coqui TTS)
✅ **Barge-in support** (caller can interrupt AI)
✅ WebSocket audio streaming
✅ Multi-company support

---

## 🏗️ Architecture

```
Phone Call (SIP)
      ↓
┌─────────────────┐
│   Asterisk      │
│   (SIP/RTP)     │
└─────────────────┘
      ↓
┌─────────────────┐
│  ARI WebSocket  │  ← Call control & events
└─────────────────┘
      ↓
┌─────────────────┐
│  ARI Bridge     │  ← Python application
│  (ari_bridge.py)│
└─────────────────┘
      ↓
┌──────────────────────────────────┐
│  FastAPI WebSocket               │
│  /ws/telephony/{channel_id}      │
└──────────────────────────────────┘
      ↓
┌──────────────────────────────────┐
│  Session Manager                 │
│  - Audio buffering               │
│  - VAD for barge-in              │
│  - STT → RAG → LLM → TTS        │
└──────────────────────────────────┘
      ↓
  AI Response (audio)
      ↓
Back through WebSocket → Asterisk → Caller
```

---

## 📋 Prerequisites

### System Requirements
- **OS**: Ubuntu 20.04/22.04 or Debian 11/12 (recommended)
- **RAM**: 4GB minimum (8GB recommended)
- **CPU**: 2 cores minimum
- **Python**: 3.10.11
- **Network**: Static IP or proper NAT configuration

### Already Installed (from your existing project)
✅ Python 3.10.11
✅ FastAPI
✅ Whisper STT
✅ Google Gemini API
✅ Sentence Transformers
✅ FAISS
✅ Coqui TTS

### New Dependencies to Install
```bash
# Install scipy and numpy for audio resampling
python3.10 -m pip install scipy==1.11.4 numpy==1.24.3 aiohttp==3.13.2
```

---

## 🔧 STEP 1: Install Asterisk

### On Ubuntu/Debian:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y build-essential git wget curl libssl-dev \
    libncurses5-dev libnewt-dev libxml2-dev linux-headers-$(uname -r) \
    libsqlite3-dev uuid-dev libjansson-dev

# Download Asterisk (latest LTS version)
cd /usr/src
sudo wget https://downloads.asterisk.org/pub/telephony/asterisk/asterisk-20-current.tar.gz
sudo tar xvf asterisk-20-current.tar.gz
cd asterisk-20*/

# Install MP3 support (optional but recommended)
sudo contrib/scripts/get_mp3_source.sh

# Configure
sudo ./configure --with-jansson-bundled

# Select modules
sudo make menuselect
# Navigate to:
# - Resource Modules → Enable res_ari, res_ari_*
# - Channel Drivers → Enable chan_pjsip
# - Save & Exit

# Compile (this takes 10-20 minutes)
sudo make -j$(nproc)

# Install
sudo make install
sudo make samples  # Install sample config files
sudo make config   # Install init scripts
sudo ldconfig

# Create asterisk user
sudo useradd -m -s /bin/bash -G audio asterisk
sudo chown -R asterisk:asterisk /etc/asterisk
sudo chown -R asterisk:asterisk /var/lib/asterisk
sudo chown -R asterisk:asterisk /var/log/asterisk
sudo chown -R asterisk:asterisk /var/spool/asterisk
sudo chown -R asterisk:asterisk /usr/lib/asterisk
```

---

## ⚙️ STEP 2: Configure Asterisk

### 2.1 Copy Configuration Files

Copy the provided configuration files to `/etc/asterisk/`:

```bash
# Navigate to your project
cd /path/to/AI-Voice-Agent

# Copy configurations
sudo cp asterisk-config/ari.conf /etc/asterisk/
sudo cp asterisk-config/pjsip.conf /etc/asterisk/
sudo cp asterisk-config/extensions.conf /etc/asterisk/
sudo cp asterisk-config/http.conf /etc/asterisk/

# Set permissions
sudo chown asterisk:asterisk /etc/asterisk/*.conf
sudo chmod 640 /etc/asterisk/*.conf
```

### 2.2 Edit PJSIP Configuration (if behind NAT)

If your server is behind NAT/firewall:

```bash
sudo nano /etc/asterisk/pjsip.conf
```

Replace `YOUR_PUBLIC_IP` with your actual public IP address:

```ini
external_media_address=YOUR_PUBLIC_IP
external_signaling_address=YOUR_PUBLIC_IP
```

### 2.3 Configure Firewall

```bash
# Allow SIP (UDP 5060)
sudo ufw allow 5060/udp

# Allow RTP (UDP 10000-20000)
sudo ufw allow 10000:20000/udp

# Allow ARI HTTP (TCP 8088)
sudo ufw allow 8088/tcp

# Optional: Allow HTTPS for ARI (TCP 8089)
sudo ufw allow 8089/tcp
```

---

## 🚀 STEP 3: Start Asterisk

```bash
# Start Asterisk
sudo systemctl start asterisk

# Enable auto-start on boot
sudo systemctl enable asterisk

# Check status
sudo systemctl status asterisk

# Connect to Asterisk CLI
sudo asterisk -rvvv

# In Asterisk CLI, verify modules loaded:
module show like res_ari
module show like chan_pjsip

# Exit CLI
exit
```

### Verify ARI is Running

```bash
# Test ARI endpoint
curl -u asterisk:asterisk http://localhost:8088/ari/api-docs/resources.json

# Should return JSON with API documentation
```

---

## 🔌 STEP 4: Configure AI Voice Agent

### 4.1 Update .env File

Add Asterisk configuration to `backend/.env`:

```bash
# Asterisk ARI Configuration
ARI_URL=http://localhost:8088/ari
ARI_USERNAME=asterisk
ARI_PASSWORD=asterisk
ARI_APP_NAME=voiceagent
WEBSOCKET_URL=ws://localhost:8000
```

### 4.2 Install New Dependencies

```bash
python3.10 -m pip install scipy==1.11.4 numpy==1.24.3
```

---

## 📱 STEP 5: Configure Softphone for Testing

### Install Zoiper (Recommended)

**Download**: https://www.zoiper.com/en/voip-softphone/download/current

**Configuration**:
1. Open Zoiper
2. Add Account:
   - **Account Name**: Test User
   - **Domain**: Your server IP (e.g., 192.168.1.100)
   - **Username**: 6001
   - **Password**: test1234
   - **Protocol**: SIP
3. Save and register

### Alternative: Linphone

**Download**: https://www.linphone.org/

**Configuration**:
- **SIP Address**: sip:6001@YOUR_SERVER_IP
- **Password**: test1234

---

## 🎯 STEP 6: Start the Complete System

### Terminal 1: Start FastAPI Server

```bash
cd /path/to/AI-Voice-Agent
python3.10 start.py
```

**Expected output**:
```
============================================================
AI VOICE AGENT - SERVER STARTER
============================================================

Starting FastAPI server...
Server will be available at: http://localhost:8000
INFO:     Application startup complete.
```

### Terminal 2: Start ARI Bridge

```bash
cd /path/to/AI-Voice-Agent
python3.10 start_ari.py
```

**Expected output**:
```
============================================================
ASTERISK ARI BRIDGE - STARTING
============================================================
INFO | Connecting to ARI WebSocket: ws://localhost:8088/ari/events...
INFO | ✓ ARI WebSocket connected
INFO | Listening for incoming calls...
```

---

## 🧪 STEP 7: Test the System

### Test 1: Check System Status

```bash
# Check FastAPI
curl http://localhost:8000/telephony/status

# Expected:
{
  "status": "operational",
  "active_calls": 0,
  "timestamp": "2025-12-27T..."
}
```

### Test 2: Make a Test Call

1. **Open your softphone** (Zoiper/Linphone)
2. **Dial**: 7000 (AI Agent extension)
3. **Wait for answer**

**Expected flow**:
```
1. Call connects
2. AI greets you: "Hello! Welcome to our AI voice assistant..."
3. Speak your question
4. AI responds with relevant information
5. You can interrupt AI while speaking (barge-in)
```

### Test 3: Verify Logs

**Check ARI Bridge logs**:
```
INFO | 📞 Incoming call from 6001 (Channel: XXX)
INFO | ✓ Answered channel XXX
INFO | ✓ Created external media channel: external-XXX
INFO | ✓ Audio streaming session started
```

**Check FastAPI logs**:
```
INFO | 📞 WebSocket connection established for channel: XXX
INFO | Starting telephony session: XXX (Caller: 6001, Company: healthplus)
INFO | 🎤 Processing speech from 6001
INFO | 📝 Transcript: what services do you offer
INFO | 🤖 AI Response: We offer comprehensive health services...
```

---

## 🎙️ How Real-Time Audio Streaming Works

### Audio Flow Diagram

```
Caller speaks
    ↓
Asterisk receives RTP (8kHz, PCMU/PCMA)
    ↓
ARI converts to 16-bit PCM (slin16)
    ↓
WebSocket sends 20ms audio chunks
    ↓
Session Manager buffers audio
    ↓
When buffer reaches 3 seconds:
    ↓
Whisper STT transcribes
    ↓
RAG retrieves relevant docs
    ↓
Gemini generates response
    ↓
Coqui TTS synthesizes speech
    ↓
Audio resampled to 8kHz
    ↓
WebSocket streams back in chunks
    ↓
Asterisk plays via RTP
    ↓
Caller hears AI response
```

### Audio Specifications

| Parameter | Value | Notes |
|-----------|-------|-------|
| Sample Rate | 8kHz | Standard for telephony |
| Bit Depth | 16-bit | Signed linear PCM |
| Channels | 1 (Mono) | Required for telephony |
| Chunk Size | 20ms | 160 samples @ 8kHz |
| Format | slin16 | Asterisk native format |

---

## 🛑 How Barge-In Works

### Detection Method

The system uses **Voice Activity Detection (VAD)** based on audio energy:

```python
# In session_manager.py
vad_threshold = 500  # Energy threshold
min_speech_frames = 3  # Require 3 consecutive frames

# For each audio frame:
energy = calculate_audio_energy(audio_data)

if energy > vad_threshold:
    speech_frames += 1
    
    if speech_frames >= min_speech_frames:
        # BARGE-IN DETECTED!
        stop_playback()
```

### Barge-In Flow

```
AI is speaking TTS
    ↓
Caller starts speaking
    ↓
Audio energy exceeds threshold
    ↓
3 consecutive frames detected
    ↓
System triggers barge-in:
    1. Stop TTS playback immediately
    2. Clear TTS queue
    3. Resume listening for caller
    4. Process new question
    ↓
AI generates new response
```

### Tuning Barge-In Sensitivity

Edit `backend/app/telephony/session_manager.py`:

```python
# More sensitive (detects quieter speech)
self.vad_threshold = 300

# Less sensitive (ignores background noise)
self.vad_threshold = 700

# Faster detection
self.min_speech_frames = 2

# More reliable detection
self.min_speech_frames = 4
```

---

## 🔍 Troubleshooting

### Issue 1: ARI Connection Fails

**Symptom**: `Failed to connect to ARI`

**Solutions**:
```bash
# Check if Asterisk is running
sudo systemctl status asterisk

# Check if ARI HTTP is enabled
sudo asterisk -rx "http show status"

# Test ARI endpoint
curl -u asterisk:asterisk http://localhost:8088/ari/api-docs/resources.json

# Check firewall
sudo ufw status
```

### Issue 2: No Audio in Call

**Symptom**: Call connects but no audio

**Solutions**:
```bash
# Check if external media is working
sudo asterisk -rx "core show channels"

# Check FastAPI WebSocket
# Look for: "WebSocket connection established"

# Verify RTP ports are open
sudo ufw allow 10000:20000/udp

# Check NAT configuration in pjsip.conf
```

### Issue 3: Softphone Can't Register

**Symptom**: "Registration failed"

**Solutions**:
```bash
# Check PJSIP endpoints
sudo asterisk -rx "pjsip show endpoints"

# Should show:
# 6001    Not in use    0 of inf

# Check if user exists
sudo asterisk -rx "pjsip show auths"

# Verify firewall allows SIP
sudo ufw allow 5060/udp

# Check logs
sudo asterisk -rx "pjsip set logger on"
```

### Issue 4: TTS Not Playing

**Symptom**: Transcription works but no voice response

**Solutions**:
```bash
# Check TTS model loaded
python3.10 -c "from app.tts.coqui_tts import get_tts_model; tts = get_tts_model(); print('TTS OK')"

# Check logs for TTS errors
tail -f backend/logs/app.log | grep TTS

# Verify audio resampling
python3.10 -c "import scipy.signal; print('scipy OK')"
```

### Issue 5: Barge-In Not Working

**Symptom**: Can't interrupt AI

**Solutions**:
1. Check VAD threshold (may be too high)
2. Verify audio energy calculation
3. Check logs for "Barge-in detected"
4. Adjust `vad_threshold` and `min_speech_frames`

---

## 📊 Monitoring & Logging

### View Live Logs

```bash
# FastAPI logs
tail -f backend/logs/app.log

# Asterisk logs
sudo tail -f /var/log/asterisk/full

# ARI bridge logs (in terminal where start_ari.py runs)
```

### Key Log Messages

**Successful call**:
```
📞 Incoming call from 6001
✓ Answered channel
✓ Created external media channel
✓ Audio streaming session started
🎤 Processing speech
📝 Transcript: [user question]
🤖 AI Response: [ai answer]
🔊 Generating TTS
📴 Call ended
```

**Barge-in detected**:
```
🛑 Barge-in detected on [channel]
⏹️ TTS playback stopped (barge-in)
🎤 Processing speech
```

---

## 🎯 Advanced Configuration

### Multi-Company Support by DID

Edit `/etc/asterisk/extensions.conf`:

```ini
[from-trunk]
; HealthPlus
exten => 5551000,1,Set(COMPANY_ID=healthplus)
 same => n,Stasis(voiceagent,${COMPANY_ID})

; TechStore
exten => 5552000,1,Set(COMPANY_ID=techstore)
 same => n,Stasis(voiceagent,${COMPANY_ID})

; ShopVerse
exten => 5553000,1,Set(COMPANY_ID=shopverse)
 same => n,Stasis(voiceagent,${COMPANY_ID})
```

### Connect to Real SIP Trunk

Edit `/etc/asterisk/pjsip.conf` (uncomment and configure):

```ini
[mytrunk]
type=endpoint
context=from-trunk
from_user=YOUR_DID
outbound_auth=mytrunk-auth
aors=mytrunk

[mytrunk-auth]
type=auth
auth_type=userpass
username=YOUR_TRUNK_USERNAME
password=YOUR_TRUNK_PASSWORD

[mytrunk]
type=aor
contact=sip:YOUR_SIP_PROVIDER
```

Then reload:
```bash
sudo asterisk -rx "pjsip reload"
```

---

## 🚀 Production Deployment

### Use Systemd Services

**FastAPI Service** (`/etc/systemd/system/voiceagent-api.service`):
```ini
[Unit]
Description=AI Voice Agent FastAPI
After=network.target

[Service]
Type=simple
User=asterisk
WorkingDirectory=/opt/AI-Voice-Agent
ExecStart=/usr/bin/python3.10 start.py
Restart=always

[Install]
WantedBy=multi-user.target
```

**ARI Bridge Service** (`/etc/systemd/system/voiceagent-ari.service`):
```ini
[Unit]
Description=AI Voice Agent ARI Bridge
After=network.target asterisk.service
Requires=asterisk.service

[Service]
Type=simple
User=asterisk
WorkingDirectory=/opt/AI-Voice-Agent
ExecStart=/usr/bin/python3.10 start_ari.py
Restart=always

[Install]
WantedBy=multi-user.target
```

**Enable services**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable voiceagent-api
sudo systemctl enable voiceagent-ari
sudo systemctl start voiceagent-api
sudo systemctl start voiceagent-ari
```

---

## ✅ Success Checklist

- [ ] Asterisk installed and running
- [ ] ARI enabled and accessible
- [ ] Softphone registered successfully
- [ ] FastAPI server running on port 8000
- [ ] ARI bridge connected to Asterisk
- [ ] Test call connects to AI agent
- [ ] AI greets caller
- [ ] Speech transcription works
- [ ] AI responds with knowledge from RAG
- [ ] Barge-in interrupts AI successfully
- [ ] Logs show complete conversation flow

---

## 📚 Additional Resources

- **Asterisk Documentation**: https://docs.asterisk.org/
- **ARI Reference**: https://docs.asterisk.org/Configuration/Interfaces/Asterisk-REST-Interface-ARI/
- **PJSIP Config**: https://docs.asterisk.org/Configuration/Channel-Drivers/SIP/Configuring-res_pjsip/

---

**Status**: 🎉 Production-Ready Real-Time Voice AI System
**Last Updated**: December 27, 2025
