@echo off
setlocal
set "ROOT=%~dp0.."
set "MOBILE_DIR=%ROOT%\apps\mobile_flutter"
cd /d "%MOBILE_DIR%"
call flutter pub get
call flutter run

