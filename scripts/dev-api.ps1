$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$ApiDir = Join-Path $Root "services/api"
$Python = Join-Path $ApiDir ".venv/Scripts/python.exe"
$Pip = Join-Path $ApiDir ".venv/Scripts/pip.exe"
$Uvicorn = Join-Path $ApiDir ".venv/Scripts/uvicorn.exe"

if (!(Test-Path $Python)) {
  python -m venv (Join-Path $ApiDir ".venv")
}

& $Pip install -r (Join-Path $ApiDir "requirements.txt")
Set-Location $ApiDir
& $Uvicorn app.main:app --reload --port 8000

