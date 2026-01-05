# 🚀 AI Voice Agent - Quick Test Guide

## ✅ Server is Running!

Your server is now running at: **http://localhost:8000**

### 📋 What the URLs Mean:

- **http://0.0.0.0:8000** - This is the server binding (don't click this)
- **http://localhost:8000** - This is what YOU access (click this!)
- **http://localhost:8000/docs** - Interactive API documentation

---

## 🌐 Step 1: Open the API Documentation

**Click this link or copy to browser:**
```
http://localhost:8000/docs
```

You'll see the FastAPI interactive documentation with all available endpoints.

---

## 🧪 Step 2: Test the System

### Option A: Check Status (Simple Test)

**In PowerShell:**
```powershell
curl http://localhost:8000/telephony/status
```

**Expected Response:**
```json
{
  "status": "running",
  "ari_connected": true,
  "active_calls": 0,
  "app_name": "ai_voice_agent",
  "timestamp": "2026-01-05T16:04:00"
}
```

### Option B: Using API Docs (Interactive)

1. Open http://localhost:8000/docs in your browser
2. Find **GET /telephony/status**
3. Click "Try it out"
4. Click "Execute"
5. See the response

---

## 📞 Step 3: Test with a Real Call

### Method 1: Via Asterisk CLI (In WSL)

```bash
# Open WSL terminal
wsl

# Connect to Asterisk CLI
sudo asterisk -rvvv

# Inside Asterisk CLI, originate a test call:
channel originate Local/test@default application Stasis ai_voice_agent
```

**What happens:**
1. Asterisk creates a test channel
2. Routes to Stasis application `ai_voice_agent`
3. Your backend answers immediately
4. AI plays greeting
5. System listens for speech
6. Processes: STT → LLM → TTS → Response

### Method 2: Via API (From PowerShell)

```powershell
# Create outbound call
$body = @{
    phone_number = "Local/test@default"
    caller_id = "AI Test"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://localhost:8000/telephony/calls/outbound" -Body $body -ContentType "application/json"
```

### Method 3: Via SIP Phone (If you have SIP trunk configured)

Configure a SIP phone to connect to your Asterisk and dial any number - it will route to the AI agent.

---

## 🔍 Step 4: Monitor the Agent

### Watch Server Logs

Look at the **server window** (the one that opened with START_SERVER.bat). You'll see:

```
INFO | 📞 StasisStart: Unknown → channel-id-here
INFO | Call Manager initialized
INFO | 🔊 Playing audio: greeting-playback-id
INFO | 👂 Listening on channel...
INFO | 👤 User said: Hello
INFO | 🤖 AI response: Hello! How can I help you?
INFO | 📴 Call ended
```

### Check Active Calls

```powershell
curl http://localhost:8000/telephony/calls
```

Shows all currently active calls.

### View API Documentation

```powershell
# Open in browser:
start http://localhost:8000/docs
```

---

## 🎯 How to Know Agent is Working

### ✅ Signs Agent is Working:

1. **Server logs show:**
   - "✓ Connected to Asterisk ARI"
   - "Stasis app 'ai_voice_agent' registered"

2. **Status endpoint returns:**
   - `"status": "running"`
   - `"ari_connected": true`

3. **When you make a test call:**
   - Logs show "📞 StasisStart"
   - You see "Playing audio" messages
   - You see "Listening on channel" messages
   - You see "AI response" messages

### ❌ If Not Working:

**Check Asterisk is running (in WSL):**
```bash
wsl sudo systemctl status asterisk
```

**Check ARI is enabled:**
```bash
wsl sudo asterisk -rx "ari show status"
```

**Should show:**
```
ARI Status:
Enabled: Yes
```

---

## 📊 Available Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Welcome message |
| `/health` | GET | Health check |
| `/docs` | GET | API documentation |
| `/telephony/status` | GET | Service status |
| `/telephony/calls` | GET | List active calls |
| `/telephony/calls/outbound` | POST | Make outbound call |
| `/telephony/calls/{id}/hangup` | POST | Hangup call |

---

## 🎤 What Agent Does During Call:

```
1. Call arrives → Agent answers immediately
2. Plays greeting (TTS): "Hello! How can I assist you today?"
3. Listens for 3 seconds (or until silence detected)
4. Transcribes your speech (Whisper STT)
5. Searches knowledge base (RAG)
6. Generates response (Gemini LLM)
7. Converts to speech (Coqui TTS)
8. Plays response to you
9. Listens again → Repeat until you hang up
```

**Features:**
- ✨ **Barge-in:** Interrupt AI anytime - it stops and listens
- 🧠 **Context:** Remembers conversation history
- 📚 **Knowledge:** Uses company FAQ/policies/services
- ⚡ **Fast:** 3-second recording timeout for quick response

---

## 🛑 Stop the Server

Press **CTRL+C** in the server window (START_SERVER.bat)

---

## 🔄 Restart the Server

Double-click: `E:\AI-Voice-Agent\START_SERVER.bat`

Or in PowerShell:
```powershell
cd E:\AI-Voice-Agent
.\START_SERVER.bat
```

---

## ✅ Quick Test Checklist

- [ ] Server started (green text in window)
- [ ] Open http://localhost:8000/docs in browser
- [ ] Run: `curl http://localhost:8000/health` → Returns `{"status":"ok"}`
- [ ] Run: `curl http://localhost:8000/telephony/status` → Returns `"ari_connected": true`
- [ ] Make test call (via Asterisk CLI or API)
- [ ] Watch server logs for call flow
- [ ] Agent answers and speaks!

**Your AI Voice Agent is ready! 🎉**
