# Start Platinum Heritage production stack (Windows PowerShell)
# Usage:
#   $env:SESSION_SECRET = "your-long-secret"
#   .\scripts\up-prod.ps1

$ErrorActionPreference = "Stop"

if (-not $env:SESSION_SECRET) {
    Write-Host "SESSION_SECRET is required. Example:" -ForegroundColor Yellow
    Write-Host '  $env:SESSION_SECRET = -join ((48..57)+(65..90)+(97..122) | Get-Random -Count 48 | ForEach-Object {[char]$_})'
    exit 1
}

Write-Host "Building and starting prod profile (db + web + redis)..." -ForegroundColor Cyan
docker compose --profile prod up -d --build

Write-Host "Waiting for healthz..." -ForegroundColor Cyan
$ok = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/healthz" -UseBasicParsing -TimeoutSec 3
        if ($r.StatusCode -eq 200) { $ok = $true; break }
    } catch {
        Start-Sleep -Seconds 2
    }
}

if ($ok) {
    Write-Host "OK  http://127.0.0.1:8000/healthz" -ForegroundColor Green
    Write-Host "App http://127.0.0.1:8000/" -ForegroundColor Green
} else {
    Write-Host "Service not healthy yet. Check: docker compose --profile prod logs web" -ForegroundColor Yellow
    exit 1
}
