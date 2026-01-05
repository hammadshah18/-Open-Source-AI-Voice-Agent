# AI Voice Agent - Production System

## Overview

A production-ready AI Voice Agent system that handles telephone calls programmatically using:
- **Asterisk 20** - PBX for call handling
- **ARI (Asterisk REST Interface)** - WebSocket-based call control
- **Python FastAPI Backend** - Async REST API and call management
- **AI Pipeline** - Whisper STT → Gemini LLM → Coqui TTS

## Architecture

```
┌────────────────────────────────────────────────────────┐
│                    Phone Call                          │
│                        │                               │
│                        ▼                               │
│  ┌──────────────────────────────────────────────┐     │
│  │         Asterisk PBX (Port 5060)             │     │
│  │  • Answers calls                             │     │
│  │  • Routes to Stasis(aiagent)                 │     │
│  │  • ARI WebSocket (Port 8088)                 │     │
│  └────────────────┬─────────────────────────────┘     │
│                   │ ARI Events                         │
│                   ▼                                    │
│  ┌──────────────────────────────────────────────┐     │
│  │    FastAPI Backend (Port 8000)               │     │
│  │  ┌────────────────────────────────────────┐  │     │
│  │  │  ARIWebSocketClient                    │  │     │
│  │  │  • Listens to call events              │  │     │
│  │  │  • Controls channels (answer/hangup)   │  │     │
│  │  │  • Manages audio playback              │  │     │
│  │  └─────────────┬──────────────────────────┘  │     │
│  │                ▼                              │     │
│  │  ┌────────────────────────────────────────┐  │     │
│  │  │  CallManager                           │  │     │
│  │  │  • Call lifecycle management           │  │     │
│  │  │  • Recording → Processing → Playback   │  │     │
│  │  │  • Barge-in support                    │  │     │
│  │  └─────────────┬──────────────────────────┘  │     │
│  │                ▼                              │     │
│  │  ┌────────────────────────────────────────┐  │     │
│  │  │  AI Pipeline                           │  │     │
│  │  │  STT → RAG → LLM → TTS                 │  │     │
│  │  └────────────────────────────────────────┘  │     │
│  └──────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────┘
```

## Prerequisites

### System Requirements
- **OS:** Ubuntu 20.04+ (or Windows with WSL2)
- **Python:** 3.10.11
- **Asterisk:** Version 20
- **RAM:** 4GB minimum
- **Disk:** 5GB free space

### Asterisk Installation (Ubuntu)

```bash
# Install Asterisk 20
sudo apt update
sudo apt install -y asterisk

# Verify installation
asterisk -V

# Enable and start service
sudo systemctl enable asterisk
sudo systemctl start asterisk
```

### Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**Key packages:**
- `fastapi` - REST API framework
- `uvicorn` - ASGI server
- `websockets` - ARI WebSocket client
- `aiohttp` - Async HTTP client
- `faster-whisper` - Speech-to-text
- `google-generativeai` - LLM
- `TTS` (Coqui) - Text-to-speech
- `faiss-cpu` - Vector database for RAG

## Configuration

### 1. Asterisk Configuration

Copy configuration files:

```bash
sudo cp asterisk-config/ari.conf /etc/asterisk/
sudo cp asterisk-config/http.conf /etc/asterisk/
sudo cp asterisk-config/extensions.conf /etc/asterisk/

# Reload Asterisk
sudo asterisk -rx "core reload"
```

**Key configurations:**

**ari.conf:**
- User: `aiagent`
- Password: `strongpassword`
- Permissions: read/write

**extensions.conf:**
- All calls route to `Stasis(aiagent)`
- No manual dial plans needed

### 2. Backend Configuration

Edit `backend/app/config.py`:

```python
# Company to use for knowledge base
ACTIVE_COMPANY = "healthplus"

# ARI connection (if different from defaults)
ARI_HOST = "localhost"
ARI_PORT = 8088
ARI_USERNAME = "aiagent"
ARI_PASSWORD = "strongpassword"
```

## Running the System

### Start Asterisk

```bash
sudo systemctl start asterisk

# Verify it's running
sudo asterisk -rx "core show version"
sudo asterisk -rx "ari show status"
```

### Start Backend

```bash
cd backend
python3.10 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Expected output:**
```
INFO | FastAPI application started with telephony support
INFO | Starting telephony service...
INFO | Call Manager initialized
INFO | ARI Client initialized: http://localhost:8088/ari, app=aiagent
INFO | ✓ Telephony service started successfully
INFO | Connecting to ARI WebSocket: ws://localhost:8088/ari/events
INFO | ✓ Connected to Asterisk ARI - Stasis app 'aiagent' registered
INFO | Uvicorn running on http://0.0.0.0:8000
```

## API Usage

### Check System Status

```bash
curl http://localhost:8000/telephony/status
```

**Response:**
```json
{
  "status": "running",
  "ari_connected": true,
  "active_calls": 0,
  "app_name": "aiagent",
  "timestamp": "2026-01-05T23:45:00"
}
```

### List Active Calls

```bash
curl http://localhost:8000/telephony/calls
```

### Originate Outbound Call

```bash
curl -X POST http://localhost:8000/telephony/calls/outbound \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "PJSIP/1001@trunk",
    "caller_id": "AI Agent"
  }'
```

### Hangup Call

```bash
curl -X POST http://localhost:8000/telephony/calls/{call_id}/hangup
```

### Health Check

```bash
curl http://localhost:8000/telephony/health
```

## Call Flow

### Inbound Call

1. **Phone rings** → Asterisk answers
2. **Asterisk** routes to `Stasis(aiagent)`
3. **ARI WebSocket** sends `StasisStart` event
4. **CallManager** creates bridge, answers call
5. **AI greets** caller (TTS)
6. **System listens** (starts recording)
7. **User speaks** (8 seconds max)
8. **STT transcribes** audio
9. **RAG retrieves** relevant context from knowledge base
10. **LLM generates** response
11. **TTS synthesizes** speech
12. **System plays** response to caller
13. **Loop** continues until hangup

### Barge-In Support

- If user speaks while AI is talking
- System stops playback immediately
- Starts listening for new input
- No need to wait for AI to finish

## Project Structure

```
AI-Voice-Agent/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI application
│   │   ├── config.py               # Configuration
│   │   ├── logger.py               # Logging setup
│   │   ├── api/                    # REST API routes
│   │   ├── stt/                    # Whisper speech-to-text
│   │   ├── llm/                    # Gemini LLM integration
│   │   ├── tts/                    # Coqui text-to-speech
│   │   ├── rag/                    # RAG system (FAISS)
│   │   └── telephony/
│   │       ├── telephony_service.py    # FastAPI routes
│   │       ├── ari_websocket.py        # ARI WebSocket client
│   │       ├── call_manager.py         # Call lifecycle
│   │       └── audio_stream.py         # Audio handling
│   ├── requirements.txt
│   └── logs/
├── asterisk-config/
│   ├── ari.conf               # ARI user configuration
│   ├── http.conf              # HTTP server for ARI
│   └── extensions.conf        # Dialplan
├── companies/                 # Knowledge base (RAG data)
│   └── healthplus/
│       ├── faqs.json
│       ├── services.json
│       └── policies.txt
└── README.md
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/telephony/status` | GET | Service status and connection info |
| `/telephony/calls` | GET | List all active calls |
| `/telephony/calls/{id}` | GET | Get specific call details |
| `/telephony/calls/outbound` | POST | Originate new outbound call |
| `/telephony/calls/{id}/hangup` | POST | Terminate specific call |
| `/telephony/calls/{id}/mute` | POST | Mute/unmute call |
| `/telephony/health` | GET | Health check |
| `/docs` | GET | Interactive API documentation |

## Logging

**Backend logs:**
```bash
tail -f backend/logs/app.log
```

**Asterisk logs:**
```bash
# CLI (interactive)
sudo asterisk -rvvv

# Log files
tail -f /var/log/asterisk/messages
tail -f /var/log/asterisk/full
```

**Call audio recordings:**
```bash
ls -lh backend/logs/call_audio/
```

## Troubleshooting

### ARI WebSocket Not Connecting

**Check Asterisk HTTP server:**
```bash
sudo asterisk -rx "http show status"
```

**Expected output:**
```
HTTP Server Status:
Prefix: /asterisk
Server: Asterisk
Server Enabled and Bound to 0.0.0.0:8088
```

**If disabled:**
```bash
# Edit http.conf
sudo nano /etc/asterisk/http.conf

[general]
enabled=yes
bindaddr=0.0.0.0
bindport=8088

# Reload
sudo asterisk -rx "http reload"
```

### ARI Authentication Failed

**Verify credentials:**
```bash
sudo cat /etc/asterisk/ari.conf
```

Should match backend configuration:
- Username: `aiagent`
- Password: `strongpassword`

### No Audio in Calls

**Check Asterisk sounds directory:**
```bash
ls -la /var/lib/asterisk/sounds/
```

**For production, set up audio file serving:**
1. Copy TTS output to `/var/lib/asterisk/sounds/`
2. Or use HTTP server for audio streaming
3. Or implement external media channel

### Calls Not Routing to ARI

**Check dialplan:**
```bash
sudo asterisk -rx "dialplan show default"
```

Should show `Stasis(aiagent)` in routing.

**Check Stasis app registration:**
```bash
sudo asterisk -rx "ari show apps"
```

Should list `aiagent` application.

## Performance Optimization

### Reduce Latency

1. **Decrease recording timeout** - Edit `call_manager.py`:
   ```python
   await asyncio.sleep(5)  # Reduce from 8 to 5 seconds
   ```

2. **Use faster STT model** - Edit `config.py`:
   ```python
   WHISPER_MODEL = "tiny"  # or "base" instead of "small"
   ```

3. **Optimize TTS** - Use faster vocoder or pre-generate common responses

4. **Cache LLM responses** - Implement response caching for FAQs

### Scale for Production

1. **Use multiple workers:**
   ```bash
   uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000
   ```

2. **Add load balancer** (nginx/haproxy)

3. **Separate services:**
   - Asterisk on dedicated server
   - Backend on application server
   - Database for call logs

4. **Use external media channels** for real-time audio streaming

## Development

### Running Tests

```bash
cd backend
pytest tests/
```

### Adding New Company Knowledge Base

1. Create directory: `companies/mycompany/`
2. Add files: `faqs.json`, `services.json`, `policies.txt`
3. Update config: `ACTIVE_COMPANY = "mycompany"`
4. Restart backend

### Debugging

**Enable verbose logging:**
```python
# config.py
LOG_LEVEL = "DEBUG"
```

**Monitor ARI events in real-time:**
```bash
# Install wscat
npm install -g wscat

# Connect to ARI WebSocket
wscat -c "ws://localhost:8088/ari/events?app=aiagent&api_key=aiagent:strongpassword"
```

## Production Deployment

### Security

1. **Change default passwords:**
   ```bash
   # In ari.conf
   password=<strong-random-password>
   ```

2. **Use HTTPS/WSS:**
   - Configure TLS certificates in Asterisk
   - Use reverse proxy (nginx) with SSL

3. **Firewall rules:**
   ```bash
   sudo ufw allow 5060/udp  # SIP (if using SIP trunks)
   sudo ufw allow 10000:20000/udp  # RTP
   sudo ufw allow 8088/tcp  # ARI (restrict to localhost/backend IP)
   ```

4. **Restrict ARI access:**
   ```ini
   # ari.conf
   read_only=no
   [aiagent]
   type=user
   password=<strong-password>
   ```

### Monitoring

1. **System metrics:**
   - Prometheus + Grafana
   - Monitor call duration, success rate, error rate

2. **Asterisk metrics:**
   - Active channels
   - Call quality (jitter, packet loss)

3. **Backend metrics:**
   - API response time
   - AI pipeline latency (STT/LLM/TTS)
   - Active WebSocket connections

### Backup

```bash
# Backup Asterisk config
sudo tar -czf asterisk-config-backup.tar.gz /etc/asterisk/

# Backup knowledge base
tar -czf companies-backup.tar.gz companies/

# Backup call logs
tar -czf call-logs-backup.tar.gz backend/logs/
```

## License

This project is for educational/internship purposes.

## Support

For issues:
1. Check logs: `backend/logs/app.log`
2. Check Asterisk CLI: `sudo asterisk -rvvv`
3. Verify ARI connection: `curl http://localhost:8000/telephony/health`
