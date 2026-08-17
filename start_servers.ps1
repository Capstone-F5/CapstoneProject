$root     = $PSScriptRoot
$backend  = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

Write-Host ""
Write-Host "===================================="
Write-Host "  Kiosk Server Start"
Write-Host "===================================="

# Backend - WorkingDirectory 로 한글 경로를 명령 문자열 밖으로 분리
$conda = Get-Command conda -ErrorAction SilentlyContinue
if ($conda) {
    $backendCommand = "conda run --no-capture-output -n kiosk-backend python -m uvicorn main:app --reload --reload-dir . --reload-dir ../ai_modules --host 0.0.0.0 --port 8000"
} else {
    # conda가 PATH에 없는 경우, 현재 PowerShell의 Python 환경을 사용한다.
    $backendCommand = "python -m uvicorn main:app --reload --reload-dir . --reload-dir ../ai_modules --host 0.0.0.0 --port 8000"
}

Start-Process powershell `
    -WorkingDirectory $backend `
    -ArgumentList "-NoExit", "-Command", $backendCommand

# 백엔드 준비 전에 Vite를 실행하면 최초 API 요청이 ECONNREFUSED가 된다.
$backendReady = $false
for ($attempt = 1; $attempt -le 20; $attempt++) {
    try {
        Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:8000/health" -TimeoutSec 1 | Out-Null
        $backendReady = $true
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $backendReady) {
    Write-Host ""
    Write-Host "  Backend could not start on http://localhost:8000." -ForegroundColor Red
    Write-Host "  Check the backend PowerShell window for the error, then run this script again."
    exit 1
}

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
