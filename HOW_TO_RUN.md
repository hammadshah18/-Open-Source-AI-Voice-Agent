# 🚀 HOW TO START & TEST YOUR AI VOICE AGENT

## ⚠️ IMPORTANT: Always Use Python 3.10.11

**Problem**: You have Python 3.13 and Python 3.10.11 installed.  
**Solution**: Always use Python 3.10.11 because that's where all packages are installed.

---

## 🎯 Quick Start (3 Methods)

### Method 1: Using run.bat (RECOMMENDED) ✅
```bash
cd e:\AI-Voice-Agent\backend
.\run.bat
```
**Advantages**:
- ✅ Automatically uses Python 3.10.11
- ✅ Sets correct working directory
- ✅ Shows server URL immediately
- ✅ Auto-reload on code changes

---

### Method 2: Using start_server.bat (NEW) ✅
```bash
cd e:\AI-Voice-Agent\backend
.\start_server.bat
```
**Same as run.bat** - both work perfectly!

---

### Method 3: Manual Command (Use this if batch files don't work)
```bash
cd e:\AI-Voice-Agent\backend
python3.10 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**⚠️ NEVER use just `python` or `uvicorn` directly** - it will use Python 3.13 which doesn't have packages!

---

## 📋 Startup Checklist

1. ✅ Open terminal (PowerShell or CMD)
2. ✅ Navigate to backend folder: `cd e:\AI-Voice-Agent\backend`
3. ✅ Run: `.\run.bat`
4. ✅ Wait for: `Application startup complete`
5. ✅ Server ready at: **http://localhost:8000**

---

## 🧪 How to Test Your Project

### Option 1: Swagger UI (Interactive Testing) 🌟
**URL**: http://localhost:8000/docs

**Steps**:
1. Start server with `.\run.bat`
2. Open browser → http://localhost:8000/docs
3. Click any endpoint (e.g., `/companies`)
4. Click "Try it out"
5. Click "Execute"
6. See response instantly!

**Best for**: Testing all endpoints interactively

---

### Option 2: ReDoc (API Documentation)
**URL**: http://localhost:8000/redoc

**Steps**:
1. Start server
2. Open browser → http://localhost:8000/redoc
3. Browse complete API documentation

**Best for**: Understanding API structure

---

### Option 3: Automated Test Script
```bash
# Start server first in one terminal
cd e:\AI-Voice-Agent\backend
.\run.bat

# Then in another terminal, run tests
cd e:\AI-Voice-Agent
python3.10 test_api.py
```

**Best for**: Quick verification all endpoints work

---

### Option 4: PowerShell Commands
```powershell
# Get companies
Invoke-RestMethod http://localhost:8000/companies

# Generate speech
$body = @{ text = "Hello from AI Voice Agent" } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/text-to-speech -Method Post -Body $body -ContentType "application/json"

# Switch company
Invoke-RestMethod -Uri http://localhost:8000/switch-company/techstore -Method Post

# Test basic endpoint
$body = @{ text = "test" } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8000/test -Method Post -Body $body -ContentType "application/json"
```

**Best for**: Quick command-line testing

---

## 📊 Available Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/docs` | GET | Swagger UI (interactive testing) |
| `/redoc` | GET | API documentation |
| `/test` | POST | Basic health check |
| `/companies` | GET | List all companies |
| `/switch-company/{id}` | POST | Change active company |
| `/text-to-speech` | POST | Generate speech from text |
| `/stt` | POST | Transcribe audio to text |
| `/voice-to-answer` | POST | Audio → Text → LLM |
| `/voice-conversation` | POST | Full pipeline (Audio → Audio) |
| `/download-audio/{file}` | GET | Download generated audio |

---

## 🔍 How to Verify Everything Works

### Step 1: Start Server
```bash
cd e:\AI-Voice-Agent\backend
.\run.bat
```

**Expected Output**:
```
Starting AI Voice Agent FastAPI Server...
Using Python 3.10.11
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

---

### Step 2: Open Swagger UI
1. Open browser
2. Go to: **http://localhost:8000/docs**
3. You should see a nice API documentation page with all endpoints

---

### Step 3: Test Companies Endpoint
1. In Swagger UI, find `/companies` endpoint
2. Click on it to expand
3. Click "Try it out"
4. Click "Execute"

**Expected Response** (200 OK):
```json
{
  "companies": [
    "edulearn",
    "healthplus", 
    "helpdesk",
    "shopverse",
    "techstore"
  ],
  "active_company": "healthplus"
}
```

---

### Step 4: Test Text-to-Speech
1. Find `/text-to-speech` endpoint
2. Click "Try it out"
3. Enter JSON:
```json
{
  "text": "Hello, this is a test",
  "language": "en"
}
```
4. Click "Execute"

**Expected**: 200 OK with audio file name in response

---

### Step 5: Run Automated Tests
```bash
# Open NEW terminal (keep server running)
cd e:\AI-Voice-Agent
python3.10 test_api.py
```

**Expected Output**:
```
🎉 ALL TESTS PASSED! System is fully operational.
Total: 5/5 tests passed (100%)
```

---

## ❌ Common Errors & Solutions

### Error 1: `ModuleNotFoundError: No module named 'TTS'`
**Cause**: Using Python 3.13 instead of 3.10.11  
**Solution**: Always use `python3.10` command or `.\run.bat`

```bash
# ❌ WRONG
python -m uvicorn app.main:app
uvicorn app.main:app

# ✅ CORRECT
python3.10 -m uvicorn app.main:app --reload
.\run.bat
```

---

### Error 2: `Address already in use`
**Cause**: Server already running on port 8000  
**Solution**: Stop existing server

```powershell
# Find process
netstat -ano | findstr :8000

# Kill process (replace <PID> with actual number)
taskkill /PID <PID> /F
```

---

### Error 3: Can't connect to server
**Cause**: Server not started  
**Solution**: Check server terminal window

```bash
# Should see this:
INFO:     Application startup complete.

# If not, restart:
cd e:\AI-Voice-Agent\backend
.\run.bat
```

---

### Error 4: `ImportError` or package issues
**Cause**: Missing packages in Python 3.10.11  
**Solution**: Reinstall packages

```bash
python3.10 -m pip install -r requirements.txt
```

---

## 🎯 Daily Workflow

### Starting Your Work:
```bash
# 1. Open terminal
cd e:\AI-Voice-Agent\backend

# 2. Start server
.\run.bat

# 3. Open browser to Swagger UI
start http://localhost:8000/docs

# 4. Start testing your changes!
```

### Testing Changes:
1. Server auto-reloads when you save files
2. Refresh browser or re-run API calls
3. Check server terminal for errors/logs

### Stopping Server:
- Press `CTRL+C` in server terminal
- Or close terminal window

---

## 📝 Quick Reference

### Server URLs:
- **API Base**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Important Commands:
```bash
# Start server (ALWAYS use this)
cd e:\AI-Voice-Agent\backend
.\run.bat

# Test all APIs
cd e:\AI-Voice-Agent
python3.10 test_api.py

# Test TTS only
python3.10 test_tts.py

# Check Python version (should be 3.10.11)
python3.10 --version

# Install missing packages
python3.10 -m pip install -r backend/requirements.txt
```

---

## ✅ Success Indicators

Your system is working correctly when:

1. ✅ Server starts without errors
2. ✅ Swagger UI loads at http://localhost:8000/docs
3. ✅ `/companies` returns 5 companies
4. ✅ `/text-to-speech` generates audio files
5. ✅ No import errors in terminal
6. ✅ Test suite passes (5/5 tests)

---

## 🆘 Still Having Issues?

### Quick Diagnostic:
```powershell
# 1. Check Python version
python3.10 --version
# Expected: Python 3.10.11

# 2. Check if packages installed
python3.10 -c "from TTS.api import TTS; print('TTS OK')"
# Expected: TTS OK

# 3. Check if port is free
netstat -ano | findstr :8000
# Expected: No output (port is free)

# 4. Try starting server
cd e:\AI-Voice-Agent\backend
.\run.bat
# Expected: Application startup complete
```

If all these pass, your system should work!

---

**Last Updated**: December 26, 2025  
**Python Version**: 3.10.11 (REQUIRED)  
**Server Port**: 8000  
**Status**: ✅ Fully Operational
