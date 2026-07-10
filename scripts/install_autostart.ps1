# install_autostart.ps1
# ======================
# Registers MSA_Startup.ps1 as a Windows Task Scheduler task
# that auto-runs on every user login (at logon trigger).
#
# Run this ONCE to install. After that, it runs automatically at startup.
# To uninstall: schtasks /delete /tn "MSA AI Agent AutoStart" /f

$TaskName   = "MSA AI Agent AutoStart"
$ScriptPath = "D:\My Self Details\Programs\AI\msa_agent\scripts\MSA_Startup.ps1"
$LogPath    = "D:\My Self Details\Programs\AI\msa_agent\data\logs\startup.log"

Write-Host ""
Write-Host "========================================"
Write-Host " MSA AI Agent V6 — Autostart Installer"
Write-Host "========================================"
Write-Host ""

# Remove old task if exists
$existing = schtasks /query /tn $TaskName 2>&1
if ($existing -notlike "*ERROR*") {
    Write-Host "Removing old task: $TaskName"
    schtasks /delete /tn $TaskName /f | Out-Null
}

# Register new task via XML (most reliable for complex scripts)
$xml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Auto-starts MSA AI Agent V6: Ollama + Flask backend + Electron desktop app on Windows login.</Description>
    <Author>MSA AI Agent</Author>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <Delay>PT15S</Delay>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>$env:USERNAME</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>false</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings><StopOnIdleEnd>false</StopOnIdleEnd><RestartOnIdle>false</RestartOnIdle></IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>powershell.exe</Command>
      <Arguments>-WindowStyle Hidden -ExecutionPolicy Bypass -File "$ScriptPath"</Arguments>
    </Exec>
  </Actions>
</Task>
"@

$xmlPath = "$env:TEMP\MSA_Task.xml"
$xml | Out-File -FilePath $xmlPath -Encoding Unicode

schtasks /create /tn $TaskName /xml $xmlPath /f

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "SUCCESS: Task '$TaskName' registered!" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Trigger : At every logon of $env:USERNAME (15s delay)"
    Write-Host "  Script  : $ScriptPath"
    Write-Host "  Log     : $LogPath"
    Write-Host ""
    Write-Host "To manually run: schtasks /run /tn `"$TaskName`""
    Write-Host "To remove      : schtasks /delete /tn `"$TaskName`" /f"
} else {
    Write-Host "FAILED to register task. Try running as Administrator." -ForegroundColor Red
}

Remove-Item $xmlPath -Force -ErrorAction SilentlyContinue
