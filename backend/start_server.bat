@echo off
REM AI Voice Agent - Startup Script
REM This ensures we use Python 3.10.11 with all installed packages

echo ========================================
echo AI Voice Agent - Starting Server
echo ========================================
echo.

REM Use Python 3.10 explicitly
python3.10 --version
echo.

echo Starting FastAPI server on http://localhost:8000
echo Press CTRL+C to stop the server
echo.
echo Swagger UI: http://localhost:8000/docs
echo ReDoc: http://localhost:8000/redoc
echo.

cd /d "%~dp0"
python3.10 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause
