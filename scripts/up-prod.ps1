# Start Platinum Heritage production stack (Windows PowerShell)
# Usage:
#   $env:SESSION_SECRET = "your-long-secret"
#   $env:POSTGRES_PASSWORD = "your-strong-db-password"
#   .\scripts\up-prod.ps1

$ErrorActionPreference = "Stop"

if (-not $env:SESSION_SECRET) {
    Write-Host "SESSION_SECRET is required. Example:" -ForegroundColor Yellow
    Write-Host '  $env:SESSION_SECRET = -join ((48..57)+(65..90)+(97..122) | Get-Random -Count 48 | ForEach-Object {[char]$_})'
    exit 1
}

if (-not $env:POSTGRES_PASSWORD) {
    Write-Host "POSTGRES_PASSWORD is required for prod Compose. Example:" -ForegroundColor Yellow
    Write-Host '  $env:POSTGRES_PASSWORD = -join ((48..57)+(65..90)+(97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})'
    exit 1
}

Write-Host "Building and starting prod profile (db + web + redis)..." -ForegroundColor Cyan
docker compose --profile prod up -d --build

Write-Host "Waiting for /readyz (DB-backed readiness)..." -ForegroundColor Cyan
$ok = $false
for ($i = 0; $i -lt 45; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/readyz" -UseBasicParsing -TimeoutSec 3
        if ($r.StatusCode -eq 200) { $ok = $true; break }
    } catch {
        Start-Sleep -Seconds 2
    }
}

if ($ok) {
    Write-Host "OK  http://127.0.0.1:8000/readyz" -ForegroundColor Green
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:8000/healthz" -UseBasicParsing -TimeoutSec 3 | Out-Null
        Write-Host "OK  http://127.0.0.1:8000/healthz" -ForegroundColor Green
    } catch {
        Write-Host "WARN /healthz check failed (readyz already OK)" -ForegroundColor Yellow
    }
    Write-Host "App http://127.0.0.1:8000/" -ForegroundColor Green
} else {
    Write-Host "Service not ready yet. Check: docker compose --profile prod logs web" -ForegroundColor Yellow
    exit 1
}
