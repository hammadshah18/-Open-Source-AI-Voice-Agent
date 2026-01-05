@echo off
echo ========================================
echo AI Voice Agent - Starting Server
echo ========================================
echo.
cd /d E:\AI-Voice-Agent\backend
set PYTHONPATH=E:\AI-Voice-Agent\backend
echo Starting server on http://localhost:8000
echo Press CTRL+C to stop
echo.
python3.10 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
