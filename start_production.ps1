# AI Voice Agent - Windows/WSL Start Script
# Run this in WSL Ubuntu terminal

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "AI Voice Agent - Starting in WSL" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Check if WSL is available
$wslCheck = wsl --list --quiet 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ WSL not found. Install with:" -ForegroundColor Red
    Write-Host "  wsl --install" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ WSL detected" -ForegroundColor Green
Write-Host ""
Write-Host "Launching start script in WSL..." -ForegroundColor Yellow
Write-Host ""

# Convert Windows path to WSL path
$scriptPath = "/mnt/e/AI-Voice-Agent/start_production.sh"

# Execute in WSL
wsl bash $scriptPath
