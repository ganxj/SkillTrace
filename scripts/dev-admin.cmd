@echo off
setlocal
set "ROOT=%~dp0.."
set "ADMIN_DIR=%ROOT%\apps\admin_next"
set "npm_config_cache=%ADMIN_DIR%\.npm-cache"
cd /d "%ADMIN_DIR%"
if not exist "node_modules" (
  call npm.cmd install
)
call npm.cmd run dev

