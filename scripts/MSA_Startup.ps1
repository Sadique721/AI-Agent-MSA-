# MSA_Startup.ps1
# ================
# Auto-starts all MSA AI Agent V6 services on Windows login:
#   1. Ollama daemon
#   2. Python Flask backend (port 5000)
#   3. Electron desktop app (.exe)
#
# Registered via Task Scheduler by install_autostart.ps1
# -------------------------------------------------------

$ProjectRoot = "D:\My Self Details\Programs\AI\msa_agent"
$LogFile     = "$ProjectRoot\data\logs\startup.log"
$PythonExe   = "$ProjectRoot\.venv\Scripts\python.exe"
$OllamaExe   = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
$ElectronExe = "$ProjectRoot\frontend-desktop\dist-electron\win-unpacked\MSA AI Agent.exe"

# Ensure log directory exists
if (-not (Test-Path "$ProjectRoot\data\logs")) {
    New-Item -ItemType Directory -Path "$ProjectRoot\data\logs" -Force | Out-Null
}

function Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts  $msg" | Out-File -FilePath $LogFile -Append -Encoding UTF8
    Write-Host "$ts  $msg"
}

Log "==============================="
Log " MSA AI Agent V6 — Startup"
Log "==============================="

# ── 1. Start Ollama ───────────────────────────────────────────────────────────
$ollamaRunning = $false
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing -TimeoutSec 3
    if ($resp.StatusCode -eq 200) {
        $ollamaRunning = $true
        Log "[Ollama]  Already running on port 11434."
    }
} catch { $ollamaRunning = $false }

if (-not $ollamaRunning) {
    if (Test-Path $OllamaExe) {
        Log "[Ollama]  Starting daemon: $OllamaExe"
        Start-Process -FilePath $OllamaExe -WindowStyle Hidden
        Start-Sleep -Seconds 4
        Log "[Ollama]  Daemon launched."
    } else {
        Log "[Ollama]  WARNING: ollama.exe not found at $OllamaExe"
    }
}

# ── 2. Start Python Backend (port 5000) ───────────────────────────────────────
$backendRunning = $false
try {
    $resp2 = Invoke-WebRequest -Uri "http://localhost:5000/api/health" -UseBasicParsing -TimeoutSec 3
    if ($resp2.StatusCode -eq 200) {
        $backendRunning = $true
        Log "[Backend] Already running on port 5000."
    }
} catch { $backendRunning = $false }

if (-not $backendRunning) {
    if (Test-Path $PythonExe) {
        Log "[Backend] Starting: $PythonExe main.py"
        $backendJob = Start-Process -FilePath $PythonExe `
            -ArgumentList "main.py" `
            -WorkingDirectory $ProjectRoot `
            -WindowStyle Hidden `
            -PassThru
        Log "[Backend] PID: $($backendJob.Id)"
        Start-Sleep -Seconds 6
    } else {
        Log "[Backend] WARNING: .venv python not found at $PythonExe"
    }
}

# ── 3. Wait for backend to be ready ──────────────────────────────────────────
$maxWait = 30
$waited  = 0
$ready   = $false
while ($waited -lt $maxWait) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:5000/api/health" -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
    Start-Sleep -Seconds 2
    $waited += 2
}

if ($ready) {
    Log "[Backend] Ready! (waited ${waited}s)"
} else {
    Log "[Backend] WARNING: Backend did not respond after ${maxWait}s — continuing anyway."
}

# ── 4. Launch Electron desktop app ───────────────────────────────────────────
$electronRunning = Get-Process -Name "MSA AI Agent" -ErrorAction SilentlyContinue
if ($electronRunning) {
    Log "[Electron] Already running."
} elseif (Test-Path $ElectronExe) {
    Log "[Electron] Launching: $ElectronExe"
    Start-Process -FilePath $ElectronExe -WorkingDirectory (Split-Path $ElectronExe)
    Log "[Electron] Launched."
} else {
    Log "[Electron] WARNING: .exe not found at $ElectronExe"
}

Log "[Done]  All MSA services started."
Log "==============================="
