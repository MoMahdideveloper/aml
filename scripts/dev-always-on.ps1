# Platinum Heritage CRM — local always-on stack (Windows)
# Starts Redis (compose crm profile), Flask web, Celery worker, Celery beat.
# Usage (from repo root):
#   .\scripts\dev-always-on.ps1
#   .\scripts\dev-always-on.ps1 -NoRedis   # if Redis already running
#   .\scripts\dev-always-on.ps1 -WebOnly

param(
    [switch]$NoRedis,
    [switch]$WebOnly,
    [int]$Port = 55555
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "Platinum Heritage CRM — always-on dev stack" -ForegroundColor Cyan
Write-Host "Root: $Root"

if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
    Write-Host "No .env found — copy .env.example to .env and set SESSION_SECRET" -ForegroundColor Yellow
}

if (-not $NoRedis -and -not $WebOnly) {
    Write-Host "Starting Redis (docker compose --profile crm)..." -ForegroundColor Green
    try {
        docker compose --profile crm up -d redis 2>&1 | Out-Host
    } catch {
        Write-Host "Docker Redis failed — set REDIS_URL if you run Redis yourself. $_" -ForegroundColor Yellow
    }
}

$env:FLASK_ENV = if ($env:FLASK_ENV) { $env:FLASK_ENV } else { "development" }
$env:USE_TAILWIND_CDN = if ($env:USE_TAILWIND_CDN) { $env:USE_TAILWIND_CDN } else { "1" }
if (-not $env:REDIS_URL) { $env:REDIS_URL = "redis://localhost:6379/0" }

$py = if (Test-Path ".\.venv\Scripts\python.exe") { ".\.venv\Scripts\python.exe" } else { "python" }

Write-Host "Starting Flask web on :$Port ..." -ForegroundColor Green
$web = Start-Process -FilePath $py -ArgumentList "main.py" -WorkingDirectory $Root -PassThru -WindowStyle Normal

if (-not $WebOnly) {
    Write-Host "Starting Celery worker..." -ForegroundColor Green
    $workerArgs = "-m celery -A celery_app.celery_app worker -l info --pool=solo"
    $worker = Start-Process -FilePath $py -ArgumentList $workerArgs.Split(" ") -WorkingDirectory $Root -PassThru -WindowStyle Normal

    Write-Host "Starting Celery beat..." -ForegroundColor Green
    $beatArgs = "-m celery -A celery_app.celery_app beat -l info"
    $beat = Start-Process -FilePath $py -ArgumentList $beatArgs.Split(" ") -WorkingDirectory $Root -PassThru -WindowStyle Normal
}

Write-Host ""
Write-Host "Web:    http://127.0.0.1:$Port" -ForegroundColor Cyan
Write-Host "Health: http://127.0.0.1:$Port/healthz"
Write-Host "PIDs:   web=$($web.Id)" + $(if (-not $WebOnly) { " worker=$($worker.Id) beat=$($beat.Id)" } else { "" })
Write-Host "Stop processes from Task Manager or: Stop-Process -Id <pid>"
Write-Host "Always-on rematch needs Redis + worker + beat (defaults: queue 60s, full sweep 15m)."
