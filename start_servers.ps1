$root     = $PSScriptRoot
$backend  = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

Write-Host ""
Write-Host "===================================="
Write-Host "  Kiosk Server Start"
Write-Host "===================================="

# 8000부터 시작해 비어 있는 포트를 자동으로 찾는다(다른 프로젝트가 점유 중이면 회피).
function Test-PortFree($port) {
    $listener = $null
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Any, $port)
        $listener.Start()
        return $true
    } catch {
        return $false
    } finally {
        if ($listener) { $listener.Stop() }
    }
}

$backendPort = 8000
while (-not (Test-PortFree $backendPort)) {
    Write-Host "  Port $backendPort is in use, trying next..." -ForegroundColor Yellow
    $backendPort++
    if ($backendPort -gt 8100) {
        Write-Host "  No free port found in 8000-8100." -ForegroundColor Red
        exit 1
    }
}

# 자식 프로세스가 상속받는 환경변수: Vite 프록시 대상, AI 모듈의 백엔드 호출 주소
$env:BACKEND_PORT = "$backendPort"
$env:API_BASE_URL = "http://localhost:$backendPort"

# Backend - WorkingDirectory 로 한글 경로를 명령 문자열 밖으로 분리
$conda = Get-Command conda -ErrorAction SilentlyContinue
if ($conda) {
    $backendCommand = "conda run --no-capture-output -n kiosk-backend python -m uvicorn main:app --reload --reload-dir . --reload-dir ../ai_modules --host 0.0.0.0 --port $backendPort"
} else {
    # conda가 PATH에 없는 경우, 현재 PowerShell의 Python 환경을 사용한다.
    $backendCommand = "python -m uvicorn main:app --reload --reload-dir . --reload-dir ../ai_modules --host 0.0.0.0 --port $backendPort"
}

Start-Process powershell `
    -WorkingDirectory $backend `
    -ArgumentList "-NoExit", "-Command", $backendCommand

# 백엔드 준비 전에 Vite를 실행하면 최초 API 요청이 ECONNREFUSED가 된다.
$backendReady = $false
$backendHealthUrl = "http://127.0.0.1:$backendPort/health"
$backendStartupTimeoutSeconds = 120
$backendStartupDeadline = (Get-Date).AddSeconds($backendStartupTimeoutSeconds)

Write-Host "  Waiting for backend (up to $backendStartupTimeoutSeconds seconds)..."
while ((Get-Date) -lt $backendStartupDeadline) {
    try {
        Invoke-WebRequest -UseBasicParsing -Uri $backendHealthUrl -TimeoutSec 2 | Out-Null
        $backendReady = $true
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}

if (-not $backendReady) {
    Write-Host ""
    Write-Host "  Backend could not start within $backendStartupTimeoutSeconds seconds (port $backendPort)." -ForegroundColor Red
    Write-Host "  Check the backend PowerShell window for the error, then run this script again."
    exit 1
}

# Frontend — 포트는 자동: 5173부터 비어 있는 포트를 찾는다(다른 프로그램이 쓰고 있으면 다음 번호).
# Pi 키오스크는 start_kiosk.sh가 이 포트를 스스로 찾아 접속하므로 번호가 바뀌어도 된다.
$vitePort = 5173
while (-not (Test-PortFree $vitePort)) {
    Write-Host "  Port $vitePort is in use, trying next..." -ForegroundColor Yellow
    $vitePort++
    if ($vitePort -gt 5200) {
        Write-Host "  No free port found in 5173-5200." -ForegroundColor Red
        exit 1
    }
}
$env:VITE_PORT = "$vitePort"
Start-Process powershell `
    -WorkingDirectory $frontend `
    -ArgumentList "-NoExit", "-Command", "npm run dev"

Write-Host ""
Write-Host "  Backend  : http://localhost:$backendPort"
Write-Host "  Frontend : https://localhost:$vitePort"
Write-Host ""
Write-Host "  Run 'ipconfig' to find PC IP for Galaxy Tab access."
Write-Host "  Access: https://[PC_IP]:$vitePort"
Write-Host ""

