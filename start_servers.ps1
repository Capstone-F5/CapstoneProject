$root     = $PSScriptRoot
$backend  = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

Write-Host ""
Write-Host "===================================="
Write-Host "  Kiosk Server Start"
Write-Host "===================================="

# Backend - WorkingDirectory 로 한글 경로를 명령 문자열 밖으로 분리
Start-Process powershell `
    -WorkingDirectory $backend `
    -ArgumentList "-NoExit", "-Command", "uvicorn main:app --reload --reload-dir . --reload-dir ../ai_modules --host 0.0.0.0 --port 8000"

Start-Sleep 2

# Frontend
Start-Process powershell `
    -WorkingDirectory $frontend `
    -ArgumentList "-NoExit", "-Command", "npm run dev"

Write-Host ""
Write-Host "  Backend  : http://localhost:8000"
Write-Host "  Frontend : https://localhost:5173"
Write-Host ""
Write-Host "  Run 'ipconfig' to find PC IP for Galaxy Tab access."
Write-Host "  Access: https://[PC_IP]:5173"
Write-Host ""
