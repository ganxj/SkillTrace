@echo off
setlocal
set "ROOT=%~dp0.."
set "API_DIR=%ROOT%\services\api"
set "DATABASE_URL=sqlite:///%API_DIR:\=/%/.local_dev.db"
set "SEED_DOMAIN_PACKS=true"
cd /d "%API_DIR%"
if not exist ".venv\Scripts\uvicorn.exe" (
  echo Missing API virtualenv. Run install first:
  echo services\api\.venv\Scripts\pip.exe install -r services\api\requirements.txt
  exit /b 1
)
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
