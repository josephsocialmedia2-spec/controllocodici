param([string]$InstallRoot = "$env:LOCALAPPDATA\AutonomousSoftwareAgent")
$startup = [Environment]::GetFolderPath("Startup")
Remove-Item (Join-Path $startup "AutonomousSoftwareAgent.cmd") -Force -ErrorAction SilentlyContinue
Get-Process AutonomousSoftwareAgent -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "Rimossi avvio automatico e processo. Dati conservati in $InstallRoot"
