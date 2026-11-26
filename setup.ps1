# Kadar — instalacija svih preduvjeta na Windowsu (PowerShell).
# Pokretanje (u mapi projekta):   powershell -ExecutionPolicy Bypass -File .\setup.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"

function Say($m)  { Write-Host "> $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "OK $m" -ForegroundColor Green }
function Warn($m) { Write-Host "!  $m" -ForegroundColor Yellow }

# 1) Python >= 3.9 (py launcher ili python)
Say "Provjeravam Python..."
$py = $null
foreach ($c in @("py -3", "python", "python3")) {
  try {
    $parts = $c.Split(" ")
    $ok = & $parts[0] $parts[1..9] -c "import sys; print(sys.version_info >= (3, 9))" 2>$null
    if ($ok -eq "True") { $py = $c; break }
  } catch {}
}
if (-not $py) {
  Write-Host "Treba Python 3.9 ili noviji: https://www.python.org/downloads/ (oznaci 'Add python.exe to PATH')." -ForegroundColor Red
  exit 1
}
$pyParts = $py.Split(" ")
Ok ("Python: " + (& $pyParts[0] $pyParts[1..9] --version))

# 2) virtualno okruzenje + paketi
$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
  Say "Stvaram virtualno okruzenje .venv..."
  & $pyParts[0] $pyParts[1..9] -m venv .venv
}
Say "Instaliram Python pakete..."
& $venvPy -m pip install --quiet --upgrade pip
& $venvPy -m pip install --quiet -r requirements.txt
Ok "Paketi instalirani"

# 3) Chromium za render
Say "Instaliram Chromium za render (jednom, ~150 MB)..."
& $venvPy -m playwright install chromium | Out-Null
Ok "Chromium spreman"

# 4) .env iz predloska (bez kljuceva)
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env"; Ok "Napravljen .env iz .env.example" }

# 5) AI backend (nije potreban za pregled demo runa, render, provjeru u kodu i isporuku)
$backend = (Select-String -Path ".env" -Pattern "^KADAR_LLM_BACKEND=(.*)$" | ForEach-Object { $_.Matches[0].Groups[1].Value }) | Select-Object -First 1
if (-not $backend) { $backend = "claude-code" }
if ($backend -eq "api") {
  if (Select-String -Path ".env" -Pattern "^ANTHROPIC_API_KEY=.+" -Quiet) { Ok "Backend: Claude API (kljuc u .env)" }
  else { Warn "Backend je 'api', ali ANTHROPIC_API_KEY je prazan." }
} else {
  $claude = Get-Command claude -ErrorAction SilentlyContinue
  if (-not $claude) {
    $cand = Join-Path $env:USERPROFILE ".local\bin\claude.exe"
    if (Test-Path $cand) { $claude = $cand }
  }
  if (-not $claude) {
    Warn "Claude Code nije instaliran. AI kadrovi (analiza, plan, novi tekstovi, AI provjera) ga trebaju; ostalo radi i bez njega."
    Warn "Instalacija (PowerShell):  irm https://claude.ai/install.ps1 | iex   zatim:  claude auth login"
    Warn "Ili u .env postavi KADAR_LLM_BACKEND=api i ANTHROPIC_API_KEY."
  } else {
    Ok "Claude Code pronaden. Ako nisi prijavljen:  claude auth login"
  }
}

# 6) brza provjera
& $venvPy -m kadar --help | Out-Null
Ok "Kadar je instaliran"
Write-Host ""
Write-Host "Pokretanje aplikacije:   powershell -ExecutionPolicy Bypass -File .\run.ps1   (http://127.0.0.1:8770)"
Write-Host "Naredbeni redak:         .venv\Scripts\python.exe -m kadar --help"
