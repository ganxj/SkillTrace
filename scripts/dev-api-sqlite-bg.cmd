@echo off
setlocal
set "ROOT=%~dp0.."
set "API_DIR=%ROOT%\services\api"
set "LOG_DIR=%ROOT%\logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "DATABASE_URL=sqlite:///%API_DIR:\=/%/.local_dev.db"
set "SEED_DOMAIN_PACKS=true"
cd /d "%API_DIR%"
echo Starting API at %DATE% %TIME% > "%LOG_DIR%\api.log"
if not exist ".venv\Scripts\uvicorn.exe" (
  echo Missing API virtualenv. >> "%LOG_DIR%\api.err"
  exit /b 1
)
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 >> "%LOG_DIR%\api.log" 2>> "%LOG_DIR%\api.err"
