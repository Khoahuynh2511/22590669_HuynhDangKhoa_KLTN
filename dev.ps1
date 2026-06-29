<#
.SYNOPSIS
  Dev launcher (Windows PowerShell): Redis + Backend + Frontend
.DESCRIPTION
  .\dev.ps1            -> start tất cả (Redis + Backend + Frontend)
  .\dev.ps1 all        -> same
  .\dev.ps1 redis      -> chỉ Redis
  .\dev.ps1 be         -> chỉ Backend
  .\dev.ps1 fe         -> chỉ Frontend
  .\dev.ps1 stop       -> dừng tất cả
.NOTES
  Nếu lỗi "cannot be loaded because running scripts is disabled":
    Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
#>
param([string]$Command = "all")

$ErrorActionPreference = "Continue"
$Root        = Split-Path -Parent $MyInvocation.MyCommand.Path
$RedisDir    = Join-Path $Root "tools\redis"
$BackendDir  = Join-Path $Root "Backend"
$FrontendDir = Join-Path $Root "Frontend"
$RedisPort = 6379; $BePort = 8000; $FePort = 4200

function Write-Dev($msg, $color = "Green") {
    Write-Host "[dev] " -NoNewline -ForegroundColor $color
    Write-Host $msg
}

function Test-PortOpen($port) {
    try {
        $c = New-Object System.Net.Sockets.TcpClient
        $c.Connect("127.0.0.1", $port); $c.Close()
        return $true
    } catch { return $false }
}

function Find-RedisExe {
    $exe = Join-Path $RedisDir "redis-server.exe"
    if (Test-Path $exe) { return $exe }
    $cmd = Get-Command redis-server -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

function Start-Redis {
    $exe = Find-RedisExe
    if (-not $exe) { Write-Dev "Không tìm thấy redis-server.exe (đặt tại tools\redis)" "Red"; return $false }
    if (Test-PortOpen $RedisPort) { Write-Dev "Redis đang chạy tại :$RedisPort (bỏ qua)"; return $true }
    Write-Dev "Khởi động Redis..."
    Start-Process -FilePath $exe -ArgumentList "--port", "6379", "--bind", "127.0.0.1" -WindowStyle Hidden
    for ($i = 0; $i -lt 20; $i++) {
        if (Test-PortOpen $RedisPort) { Write-Dev "Redis UP tại :$RedisPort"; return $true }
        Start-Sleep -Milliseconds 500
    }
    Write-Dev "Redis không lên được tại :$RedisPort" "Red"
    return $false
}

function Start-InWindow($title, $workDir, $cmdline) {
    # -NoExit giữ cửa sổ mở sau khi lệnh chạy xong (hoặc lỗi) để xem log.
    $inner = "Set-Location -LiteralPath '$workDir'; Write-Host '=== $title ===' -ForegroundColor Cyan; $cmdline"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $inner
}

function Start-Backend {
    if (Test-PortOpen $BePort) { Write-Dev "Cổng :$BePort đang bận (Backend đã chạy?)" "Yellow"; return }
    $envFile = Join-Path $BackendDir ".env"
    if (-not (Test-Path $envFile)) {
        Write-Dev "Backend\.env chưa có -> copy từ .env.example (nhớ điền SMTP/DB)" "Yellow"
        $src = Join-Path $BackendDir ".env.example"
        if (Test-Path $src) { Copy-Item $src $envFile }
    }
    Write-Dev "Khởi động Backend (uv sync + uvicorn :$BePort)..."
    Start-InWindow "Backend" $BackendDir "uv sync; uv run uvicorn main:app --reload --host 0.0.0.0 --port $BePort"
}

function Start-Frontend {
    if (Test-PortOpen $FePort) { Write-Dev "Cổng :$FePort đang bận (Frontend đã chạy?)" "Yellow"; return }
    Write-Dev "Khởi động Frontend (npm install nếu thiếu + ng serve :$FePort)..."
    $cmd = "if (-not (Test-Path node_modules)) { npm install }; ng serve --port $FePort"
    Start-InWindow "Frontend" $FrontendDir $cmd
}

function Stop-Port($port) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($conns) {
        $procId = ($conns | Select-Object -First 1).OwningProcess
        if ($procId) {
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            Write-Dev "Đã dừng process trên :$port (PID $procId)"
        }
    } else {
        Write-Dev "Không có process nào trên :$port" "Yellow"
    }
}

function Stop-All {
    Write-Dev "Dừng tất cả..."
    Stop-Port $FePort
    Stop-Port $BePort
    Stop-Port $RedisPort
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  AI Tour Booking - Dev Launcher (PowerShell)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

switch ($Command) {
    "redis" { Start-Redis }
    "be"    { Start-Backend }
    "fe"    { Start-Frontend }
    "all" {
        if (-not (Start-Redis)) { Write-Dev "Redis fail -> dừng (cần Redis để OTP hoạt động)" "Red"; break }
        Start-Sleep -Seconds 1
        Start-Backend
        Start-Sleep -Seconds 1
        Start-Frontend
        Write-Host ""
        Write-Dev "Frontend : http://localhost:$FePort"
        Write-Dev "Backend  : http://localhost:$BePort  (docs: /docs)"
        Write-Dev "Redis    : 127.0.0.1:$RedisPort"
    }
    "stop" { Stop-All }
    default {
        Write-Dev "Lệnh không hợp lệ: $Command" "Red"
        Write-Host "Dùng: .\dev.ps1 [all|redis|be|fe|stop]"
    }
}
