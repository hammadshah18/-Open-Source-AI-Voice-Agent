@echo off
cd /d "e:\AI-Voice-Agent\backend"
C:\Users\hamma\AppData\Local\Microsoft\WindowsApps\python3.10.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
