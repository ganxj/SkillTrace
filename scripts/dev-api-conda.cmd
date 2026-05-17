@echo off
setlocal
set "ROOT=%~dp0.."
set "API_DIR=%ROOT%\services\api"
set "DATABASE_URL=sqlite:///%API_DIR:\=/%/.local_dev.db"
set "SEED_DOMAIN_PACKS=true"
cd /d "%API_DIR%"
call conda activate base
if not exist ".venv\Scripts\python.exe" (
  echo Creating project virtualenv with conda base Python...
  python -m venv .venv
)
".venv\Scripts\python.exe" -c "import fastapi, sqlalchemy, pydantic, pydantic_settings, httpx, psycopg, alembic" >nul 2>nul
if errorlevel 1 (
  echo Installing API dependencies into services\api\.venv...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
