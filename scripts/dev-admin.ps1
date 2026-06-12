$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$AdminDir = Join-Path $Root "apps/admin_next"
$env:npm_config_cache = Join-Path $AdminDir ".npm-cache"
$env:API_INTERNAL_BASE_URL = "http://127.0.0.1:8898/api/v1"
$env:LOCAL_API_BASE_URL = "http://127.0.0.1:8898/api/v1"
$env:NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8898/api/v1"

if (-not (Test-Path (Join-Path $Root "node_modules/next"))) {
    Set-Location $Root
    npm.cmd install
}

Set-Location $AdminDir
npm.cmd run dev

