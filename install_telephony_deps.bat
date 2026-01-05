@echo off
REM Windows users: Install dependencies for telephony support

echo ============================================================
echo   AI VOICE AGENT - TELEPHONY DEPENDENCIES INSTALLER
echo ============================================================
echo.

echo Installing audio processing libraries...
python3.10 -m pip install scipy==1.11.4 numpy==1.24.3

echo.
echo Installing async HTTP client...
python3.10 -m pip install aiohttp==3.13.2

echo.
echo Verifying installations...
python3.10 -c "import scipy; print('✓ scipy OK')"
python3.10 -c "import numpy; print('✓ numpy OK')"
python3.10 -c "import aiohttp; print('✓ aiohttp OK')"

echo.
echo ============================================================
echo   ✓ Telephony dependencies installed successfully!
echo ============================================================
echo.
echo Next steps:
echo 1. Install Asterisk on a Linux server (see docs/telephony.md)
echo 2. Copy asterisk-config/*.conf to /etc/asterisk/
echo 3. Start Asterisk: sudo systemctl start asterisk
echo 4. Start AI Voice Agent: python3.10 start.py
echo 5. Start ARI Bridge: python3.10 start_ari.py
echo.

pause
