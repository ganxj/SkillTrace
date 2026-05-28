$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$ApiDir = Join-Path $Root "services/api"
$env:DATABASE_URL = "sqlite:///$($ApiDir.Replace('\', '/'))/.local_dev.db"
$env:SEED_DOMAIN_PACKS = "true"

Set-Location $ApiDir
& .\.venv\Scripts\uvicorn.exe app.main:app --host 192.168.1.192 --port 8001
