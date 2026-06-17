#Requires -Version 5.1
<#
.SYNOPSIS
  Start the AEGIS local dev stack (backend API + Vite dashboard).

.DESCRIPTION
  1. Kills any existing processes on the target ports.
  2. Creates/reuses a venv at backend/.venv (prefers py -3.13, falls back to python).
  3. Installs backend/requirements.txt into the venv.
  4. Launches uvicorn with visible log output (backend_live.log at repo root).
  5. Polls /health until 200 — fails loudly if the backend doesn't start.
  6. Launches the Vite dashboard (or Streamlit).

.EXAMPLE
  .\tools\start_local_mvp.ps1
  .\tools\start_local_mvp.ps1 -AnalystToken "mytoken" -EnrollmentToken "mytoken"
  .\tools\start_local_mvp.ps1 -UseStreamlit
#>
param(
    [string]$AnalystToken    = "sample-token",
    [string]$EnrollmentToken = "sample-token",
    [string]$ApiHost         = "0.0.0.0",
    [int]$ApiPort            = 8080,
    [int]$UiPort             = 5173,
    [int]$ApkPort            = 8000,
    [string]$LocalLlmProvider = "ollama",
    [string]$OpenRouterApiKey = "",
    [switch]$UseStreamlit,
    [switch]$StartApkStudio
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot   = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"
$logFile    = Join-Path $repoRoot "backend_live.log"

# ─── helpers ────────────────────────────────────────────────────────────────

function Write-Step { param([string]$msg) Write-Host "`n▶  $msg" -ForegroundColor Cyan }
function Write-Ok   { param([string]$msg) Write-Host "   ✓ $msg" -ForegroundColor Green }
function Write-Warn { param([string]$msg) Write-Host "   ⚠ $msg" -ForegroundColor Yellow }
function Fail       { param([string]$msg) Write-Host "`n✗ $msg" -ForegroundColor Red; exit 1 }

# ─── 1. Python version check ─────────────────────────────────────────────────

Write-Step "Checking Python toolchain"

$pyExe     = $null
$pyVersion = $null

foreach ($candidate in @("3.13", "3.12", "3.11")) {
    $ver = & py "-$candidate" --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $pyExe     = "py"
        $pyVersion = $candidate
        Write-Ok "Found Python $candidate via py launcher"
        break
    }
}

if (-not $pyExe) {
    $ver = & python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        Fail "No suitable Python found. Install Python 3.11–3.13 from python.org."
    }
    $pyExe = "python"
    if ($ver -match "Python (3\.\d+)") {
        $pyVersion = $Matches[1]
        Write-Ok "Found $ver (via 'python')"
        if ([version]$pyVersion -lt [version]"3.11") {
            Fail "Python 3.11+ required. Found $ver."
        }
    }
}

# ─── 2. Kill existing listeners ──────────────────────────────────────────────

Write-Step "Killing existing listeners on ports $ApiPort / $UiPort / $ApkPort / 8501"

$ports = @($ApiPort, $UiPort, $ApkPort, 8501)
$existingPids = Get-NetTCPConnection -LocalPort $ports -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique

foreach ($pid in $existingPids) {
    if ($pid -and $pid -ne 0) {
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        Write-Ok "Killed PID $pid"
    }
}
Start-Sleep -Seconds 1   # brief settle

# ─── 3. Create / reuse venv ──────────────────────────────────────────────────

Write-Step "Setting up backend/.venv"

$venvDir    = Join-Path $backendDir ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Warn "Creating new venv at $venvDir ..."
    if ($pyExe -eq "py") {
        & py "-$pyVersion" -m venv $venvDir
    } else {
        & python -m venv $venvDir
    }
    if ($LASTEXITCODE -ne 0) { Fail "Failed to create venv" }
    Write-Ok "Venv created"
} else {
    Write-Ok "Reusing existing venv"
}

# ─── 4. Install requirements ─────────────────────────────────────────────────

Write-Step "Installing backend dependencies"

$reqFile = Join-Path $backendDir "requirements.txt"
if (-not (Test-Path $reqFile)) {
    Fail "backend/requirements.txt not found. Run: cd backend && pip install -e ."
}

& $venvPython -m pip install --quiet --upgrade pip
& $venvPython -m pip install --quiet -r $reqFile
if ($LASTEXITCODE -ne 0) { Fail "pip install failed" }
Write-Ok "Dependencies installed"

# ─── 5. Environment variables ────────────────────────────────────────────────

$env:AEGIS_ANALYST_TOKENS            = $AnalystToken
$env:AEGIS_ACCEPTED_ENROLLMENT_TOKENS = $EnrollmentToken
$env:AEGIS_LOCAL_LLM_PROVIDER        = $LocalLlmProvider
$env:AEGIS_LOGS_MODEL                = "llama3:latest"
$env:AEGIS_TELEMETRY_MODEL           = "llama3:latest"
$env:AEGIS_RISK_MODEL                = "llama3:latest"
$env:AEGIS_LOCAL_LLM_TIMEOUT_SECONDS = "120"
$env:AEGIS_CORS_ALLOWED_ORIGINS      = "http://localhost:$UiPort,http://127.0.0.1:$UiPort,http://10.0.2.2:$ApiPort"

if ($OpenRouterApiKey) {
    $env:OPENROUTER_API_KEY = $OpenRouterApiKey
}

# ─── 6. Optionally start Ollama ──────────────────────────────────────────────

if ($LocalLlmProvider -eq "ollama") {
    try {
        Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3 | Out-Null
        Write-Ok "Ollama already running"
    } catch {
        $ollama = Get-Command ollama -ErrorAction SilentlyContinue
        if ($ollama) {
            Write-Warn "Starting Ollama..."
            Start-Process -FilePath $ollama.Source -ArgumentList "serve" -WindowStyle Hidden
            Start-Sleep -Seconds 4
        } else {
            Write-Warn "Ollama not found. AI analysis will run in stub mode."
            $env:AEGIS_LOCAL_LLM_PROVIDER = "stub"
        }
    }
}

# ─── 5b. Run database migrations ────────────────────────────────────────────

Write-Step "Running database migrations (alembic upgrade head)"

Push-Location $backendDir
$upgradeOut  = & $venvPython -m alembic upgrade head 2>&1
$upgradeExit = $LASTEXITCODE
if ($upgradeExit -ne 0) {
    if ($upgradeOut -match "already exists") {
        # Tables were created by create_all before Alembic was introduced.
        # Stamp as 0001 (all tables present) then apply incremental migrations.
        Write-Warn "Tables exist without Alembic stamp — stamping 0001 and retrying..."
        & $venvPython -m alembic stamp 0001 | Out-Null
        & $venvPython -m alembic upgrade head | Out-Null
        if ($LASTEXITCODE -ne 0) { Fail "Alembic migration failed after stamp." }
    } else {
        $upgradeOut | Select-Object -Last 8 | ForEach-Object { Write-Host "  $_" }
        Fail "Alembic migration failed."
    }
}
Pop-Location
Write-Ok "Database migrations up to date"

# ─── 7. Start uvicorn (logged, not hidden) ───────────────────────────────────

Write-Step "Starting AEGIS backend on $ApiHost`:$ApiPort"

# Truncate old log
"" | Set-Content -Path $logFile -Encoding utf8

$uvicornArgs = @(
    "-m", "uvicorn",
    "app.main:app",
    "--host", $ApiHost,
    "--port", "$ApiPort",
    "--log-level", "info"
)

$uvicornProc = Start-Process `
    -FilePath $venvPython `
    -ArgumentList $uvicornArgs `
    -WorkingDirectory $backendDir `
    -RedirectStandardOutput $logFile `
    -RedirectStandardError  $logFile `
    -PassThru

if (-not $uvicornProc) { Fail "Failed to launch uvicorn" }
Write-Ok "uvicorn PID $($uvicornProc.Id) — log: $logFile"

# ─── 8. Poll /health until 200 ───────────────────────────────────────────────

Write-Step "Waiting for /health 200 (up to 30s)"

$healthy    = $false
$healthUrl  = "http://127.0.0.1:$ApiPort/health"
$maxRetries = 30

for ($i = 1; $i -le $maxRetries; $i++) {
    Start-Sleep -Seconds 1
    if ($uvicornProc.HasExited) {
        Write-Host ""
        Write-Warn "uvicorn exited early. Last log lines:"
        Get-Content $logFile -Tail 20 | ForEach-Object { Write-Host "  $_" }
        Fail "Backend crashed before becoming healthy. See $logFile"
    }
    try {
        $resp = Invoke-WebRequest -Uri $healthUrl -TimeoutSec 2 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) {
            $healthy = $true
            Write-Ok "Backend healthy (${i}s)"
            break
        }
    } catch {
        Write-Host "." -NoNewline
    }
}

if (-not $healthy) {
    Write-Host ""
    Write-Warn "Backend did not respond in ${maxRetries}s. Last log lines:"
    Get-Content $logFile -Tail 20 | ForEach-Object { Write-Host "  $_" }
    Fail "Backend failed health check. See $logFile"
}

# ─── 9. Start frontend ───────────────────────────────────────────────────────

if ($UseStreamlit) {
    Write-Step "Starting Streamlit dashboard on port 8501"

    $env:AEGIS_API_URL      = "http://127.0.0.1:$ApiPort/api/v1"
    $env:AEGIS_ANALYST_TOKEN = $AnalystToken

    Start-Process `
        -FilePath $venvPython `
        -ArgumentList "-m", "streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=127.0.0.1" `
        -WorkingDirectory $backendDir `
        -WindowStyle Normal

    $uiUrl = "http://127.0.0.1:8501"
    Start-Sleep -Seconds 3

} else {
    Write-Step "Starting Vite dashboard on port $UiPort"

    if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
        Write-Warn "node_modules not found — running npm install..."
        Push-Location $frontendDir
        npm install
        if ($LASTEXITCODE -ne 0) { Fail "npm install failed" }
        Pop-Location
        Write-Ok "npm install done"
    }

    $env:VITE_AEGIS_API_URL = "http://127.0.0.1:$ApiPort/api/v1"

    $viteProc = Start-Process `
        -FilePath "npm.cmd" `
        -ArgumentList "run", "dev", "--", "--host", "127.0.0.1", "--port", "$UiPort" `
        -WorkingDirectory $frontendDir `
        -PassThru

    $uiUrl = "http://127.0.0.1:$UiPort"

    # Brief wait then confirm Vite started
    Start-Sleep -Seconds 4
    $viteTcp = Get-NetTCPConnection -LocalPort $UiPort -ErrorAction SilentlyContinue
    if ($viteTcp) {
        Write-Ok "Vite listening on $UiPort (PID $($viteProc.Id))"
    } else {
        Write-Warn "Vite may still be starting — check $UiPort in a moment"
    }
}

# ─── 9b. Start APK Studio backend (optional) ────────────────────────────────

$apkStudioDir = Join-Path $repoRoot "apk-studio"
$apkLogFile   = Join-Path $repoRoot "apk_studio.log"

if ($StartApkStudio) {
    if (-not (Test-Path $apkStudioDir)) {
        Write-Warn "apk-studio/ not found — skipping APK Studio. Clone it first:"
        Write-Warn "  git clone <APK_STUDIO_REPO_URL> apk-studio"
    } else {
        Write-Step "Starting APK Studio backend on port $ApkPort"

        $apkVenvPy = Join-Path $apkStudioDir ".venv\Scripts\python.exe"
        if (-not (Test-Path $apkVenvPy)) {
            Write-Warn "APK Studio venv not found. Creating..."
            if ($pyExe -eq "py") {
                & py "-$pyVersion" -m venv (Join-Path $apkStudioDir ".venv")
            } else {
                & python -m venv (Join-Path $apkStudioDir ".venv")
            }
        }
        $apkReqFile = Join-Path $apkStudioDir "requirements.txt"
        if (Test-Path $apkReqFile) {
            & $apkVenvPy -m pip install --quiet -r $apkReqFile
        }

        "" | Set-Content -Path $apkLogFile -Encoding utf8
        $apkProc = Start-Process `
            -FilePath $apkVenvPy `
            -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$ApkPort", "--log-level", "info" `
            -WorkingDirectory $apkStudioDir `
            -RedirectStandardOutput $apkLogFile `
            -RedirectStandardError  $apkLogFile `
            -PassThru

        Start-Sleep -Seconds 3
        $apkTcp = Get-NetTCPConnection -LocalPort $ApkPort -ErrorAction SilentlyContinue
        if ($apkTcp) {
            Write-Ok "APK Studio listening on $ApkPort (PID $($apkProc.Id))"
        } else {
            Write-Warn "APK Studio may still be starting — check http://127.0.0.1:$ApkPort"
        }
    }
}

# ─── 10. Summary ─────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " AEGIS stack is UP" -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Backend API :  http://127.0.0.1:$ApiPort"
Write-Host "  Dashboard   :  $uiUrl"
Write-Host "  Health      :  http://127.0.0.1:$ApiPort/health"
Write-Host "  Log file    :  $logFile"
Write-Host "  LLM provider:  $($env:AEGIS_LOCAL_LLM_PROVIDER)"
Write-Host "  Analyst tok :  $AnalystToken"
Write-Host "  Enroll tok  :  $EnrollmentToken"
if ($StartApkStudio -and (Test-Path $apkStudioDir)) {
    Write-Host "  APK Studio  :  http://127.0.0.1:$ApkPort" -ForegroundColor Magenta
    Write-Host "  APK log     :  $apkLogFile"
} else {
    Write-Host "  APK Studio  :  (not started — use -StartApkStudio after cloning apk-studio/)" -ForegroundColor DarkGray
}
Write-Host ""
Write-Host "  Android emulator → http://10.0.2.2:$ApiPort" -ForegroundColor Yellow
Write-Host ""
