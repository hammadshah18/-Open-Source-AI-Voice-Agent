@echo off
REM ==============================================================================
REM AI Voice Agent Telephony Service Startup Script (Windows/WSL2)
REM ==============================================================================

echo ==========================================================================
echo   AI VOICE AGENT - TELEPHONY SERVICE
echo ==========================================================================
echo.

REM Check if WSL is available
where wsl >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] WSL not found. Please install WSL2 with Ubuntu.
    echo.
    echo Installation guide: https://docs.microsoft.com/en-us/windows/wsl/install
    pause
    exit /b 1
)

echo [INFO] Starting services in WSL2...
echo.

REM Start Asterisk in WSL2
echo [1/3] Starting Asterisk...
wsl sudo systemctl start asterisk 2>nul
if %ERRORLEVEL% EQU 0 (
    echo       ^[OK^] Asterisk started
) else (
    echo       ^[WARN^] Asterisk may already be running
)

REM Copy configuration files
echo [2/3] Updating Asterisk configuration...
wsl sudo cp /mnt/e/AI-Voice-Agent/asterisk-config/*.conf /etc/asterisk/ 2>nul
wsl sudo asterisk -rx "core reload" 2>nul
echo       ^[OK^] Configuration updated

REM Start FastAPI backend
echo [3/3] Starting FastAPI backend...
echo.
echo ==========================================================================
echo   Backend starting on http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo   Telephony Status: http://localhost:8000/telephony/status
echo ==========================================================================
echo.

cd backend
python3.10 -m pip install -q -r requirements.txt
python3.10 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause
