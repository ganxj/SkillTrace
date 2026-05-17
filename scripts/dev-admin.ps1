$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$AdminDir = Join-Path $Root "apps/admin_next"
$env:npm_config_cache = Join-Path $AdminDir ".npm-cache"

Set-Location $AdminDir
npm install
npm run dev

