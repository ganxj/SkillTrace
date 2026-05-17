$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$MobileDir = Join-Path $Root "apps/mobile_flutter"

Set-Location $MobileDir
flutter pub get
flutter run

