# Pokrece Kadar web aplikaciju na Windowsu (http://127.0.0.1:8770). Prvo jednom pokreni setup.ps1.
Set-Location $PSScriptRoot
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"
$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { Write-Host "Prvo pokreni setup.ps1"; exit 1 }
& $venvPy -m kadar app @args
