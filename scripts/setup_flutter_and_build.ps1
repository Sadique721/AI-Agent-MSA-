# scripts/setup_flutter_and_build.ps1
# Automatically download, configure portable Flutter SDK, and build the APK.

$ErrorActionPreference = "Stop"

# Define Paths
$ProjectRoot = (Get-Item $PSScriptRoot).Parent.FullName
$ToolsDir = Join-Path $ProjectRoot "tools"
$FlutterZip = Join-Path $ToolsDir "flutter_windows.zip"
$FlutterDir = Join-Path $ToolsDir "flutter"
$FlutterBin = Join-Path $FlutterDir "bin"
$FlutterExe = Join-Path $FlutterBin "flutter.bat"
$FlutterAppDir = Join-Path $ProjectRoot "flutter_app"

# Ensure Tools directory exists
if (-not (Test-Path $ToolsDir)) {
    Write-Host "Creating tools directory..." -ForegroundColor Green
    New-Item -ItemType Directory -Path $ToolsDir | Out-Null
}

# 1. Download Flutter SDK if not already present
$DownloadUrl = "https://storage.googleapis.com/flutter_infra_release/releases/stable/windows/flutter_windows_3.44.2-stable.zip"

if (-not (Test-Path $FlutterExe)) {
    if (-not (Test-Path $FlutterZip)) {
        Write-Host "Downloading Flutter stable SDK (3.44.2)... This may take a few minutes (approx 1GB)." -ForegroundColor Cyan
        Write-Host "URL: $DownloadUrl" -ForegroundColor Cyan
        try {
            Import-Module BitsTransfer
            Start-BitsTransfer -Source $DownloadUrl -Destination $FlutterZip -DisplayName "Downloading Flutter SDK"
        } catch {
            Write-Host "BitsTransfer failed, falling back to WebClient..." -ForegroundColor Yellow
            $WebClient = New-Object System.Net.WebClient
            $WebClient.DownloadFile($DownloadUrl, $FlutterZip)
        }
    }

    # 2. Extract Flutter SDK
    Write-Host "Extracting Flutter SDK to $ToolsDir..." -ForegroundColor Cyan
    try {
        Expand-Archive -Path $FlutterZip -DestinationPath $ToolsDir -Force
    } catch {
        Write-Host "Extraction failed with Expand-Archive. Trying Shell.Application..." -ForegroundColor Yellow
        $shell = New-Object -ComObject Shell.Application
        $zip = $shell.NameSpace($FlutterZip)
        $dest = $shell.NameSpace($ToolsDir)
        $dest.CopyHere($zip.Items(), 16)
    }

    # Clean up zip
    if (Test-Path $FlutterZip) {
        Remove-Item $FlutterZip -Force
        Write-Host "Cleaned up Flutter ZIP file." -ForegroundColor Green
    }
} else {
    Write-Host "Flutter SDK already found at $FlutterDir." -ForegroundColor Green
}

# 3. Configure Environments
Write-Host "Configuring build environment variables..." -ForegroundColor Cyan
$env:ANDROID_HOME = "C:\Users\MD SADIQUE AMIN\AppData\Local\Android\Sdk"
$env:PATH = "$FlutterBin;" + $env:PATH

# Redirect all Gradle, Pub, and Temp writes to D: drive due to low space on C:
$BuildTmp = Join-Path $ProjectRoot ".build_tmp"
if (-not (Test-Path $BuildTmp)) { New-Item -ItemType Directory -Path $BuildTmp | Out-Null }
$env:GRADLE_USER_HOME = Join-Path $BuildTmp ".gradle"
$env:PUB_CACHE = Join-Path $BuildTmp ".pub_cache"
$env:TEMP = $BuildTmp
$env:TMP = $BuildTmp

# Verify Flutter execution
Write-Host "Checking local Flutter SDK integrity..." -ForegroundColor Cyan
& $FlutterExe --version

# 4. Build the Flutter App APK
Write-Host "Navigating to Flutter App directory: $FlutterAppDir..." -ForegroundColor Cyan
Set-Location $FlutterAppDir

# Check if android folder is missing
$AndroidDir = Join-Path $FlutterAppDir "android"
if (-not (Test-Path $AndroidDir)) {
    Write-Host "Android platform directory is missing. Regenerating Flutter project scaffolding..." -ForegroundColor Yellow
    
    # Back up lib and pubspec.yaml
    Rename-Item -Path (Join-Path $FlutterAppDir "lib") -NewName "lib_backup" -Force
    Rename-Item -Path (Join-Path $FlutterAppDir "pubspec.yaml") -NewName "pubspec.yaml.backup" -Force
    
    # Run flutter create
    & $FlutterExe create --platforms=android .
    
    # Restore backups
    Remove-Item -Path (Join-Path $FlutterAppDir "lib") -Recurse -Force
    Rename-Item -Path (Join-Path $FlutterAppDir "lib_backup") -NewName "lib" -Force
    Remove-Item -Path (Join-Path $FlutterAppDir "pubspec.yaml") -Force
    Rename-Item -Path (Join-Path $FlutterAppDir "pubspec.yaml.backup") -NewName "pubspec.yaml" -Force
}

Write-Host "Running flutter clean..." -ForegroundColor Cyan
& $FlutterExe clean

Write-Host "Running flutter pub get..." -ForegroundColor Cyan
& $FlutterExe pub get

Write-Host "Compiling MSA AI AGENT Mobile Client APK (Debug)..." -ForegroundColor Cyan
& $FlutterExe build apk --debug

# Verify APK creation
$ApkPath = Join-Path $FlutterAppDir "build\app\outputs\flutter-apk\app-debug.apk"
if (Test-Path $ApkPath) {
    Write-Host "`n=================================================================" -ForegroundColor Green
    Write-Host "SUCCESS: APK file compiled successfully!" -ForegroundColor Green
    Write-Host "APK Location: $ApkPath" -ForegroundColor Green
    Write-Host "=================================================================" -ForegroundColor Green
    
    # Copy APK to project root for easy user access
    $DestApk = Join-Path $ProjectRoot "msa_agent_client.apk"
    Copy-Item -Path $ApkPath -Destination $DestApk -Force
    Write-Host "Copied APK to project root: $DestApk" -ForegroundColor Green
} else {
    Write-Error "APK file compilation failed. APK not found at $ApkPath"
}
