param(
  [string]$ExePath = "$PSScriptRoot\AutonomousSoftwareAgent.exe",
  [string]$InstallRoot = "$env:LOCALAPPDATA\AutonomousSoftwareAgent"
)
$ErrorActionPreference = "Stop"
if (!(Test-Path $ExePath)) { throw "EXE non trovato: $ExePath" }
New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
foreach ($name in @("INBOX","SESSIONS","READY","LOGS")) { New-Item -ItemType Directory -Force -Path (Join-Path $InstallRoot $name) | Out-Null }
$dest = Join-Path $InstallRoot "AutonomousSoftwareAgent.exe"
Copy-Item $ExePath $dest -Force
& $dest self-test
if ($LASTEXITCODE -ne 0) { throw "Self-test fallito: installazione annullata" }
$startup = [Environment]::GetFolderPath("Startup")
$cmd = Join-Path $startup "AutonomousSoftwareAgent.cmd"
$line = '@echo off' + "`r`n" + 'start "" /min "' + $dest + '" watch "' + $InstallRoot + '"'
Set-Content -LiteralPath $cmd -Value $line -Encoding ASCII
Start-Process -FilePath $dest -ArgumentList @("watch", $InstallRoot) -WindowStyle Hidden
Write-Host "INSTALLAZIONE_OK $dest"
