@echo off
setlocal
set "ROOT=%~dp0.."
set "ADMIN_DIR=%ROOT%\apps\admin_next"
set "npm_config_cache=%ADMIN_DIR%\.npm-cache"
set "API_INTERNAL_BASE_URL=http://127.0.0.1:8898/api/v1"
set "LOCAL_API_BASE_URL=http://127.0.0.1:8898/api/v1"
if not exist "%ROOT%\node_modules\next" (
  cd /d "%ROOT%"
  call npm.cmd install
)
cd /d "%ADMIN_DIR%"
call npm.cmd run dev

