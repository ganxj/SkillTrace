@echo off
setlocal
set "ROOT=%~dp0.."
set "API_DIR=%ROOT%\services\api"
set "DATABASE_URL=sqlite:///%API_DIR:\=/%/.local_dev.db"
set "SEED_DOMAIN_PACKS=true"
cd /d "%API_DIR%"
call conda activate py3_11
if errorlevel 1 (
  echo Failed to activate conda environment py3_11.
  echo Make sure Conda is initialized for cmd.exe and the py3_11 environment exists.
  exit /b 1
)
python -c "import fastapi, sqlalchemy, pydantic, pydantic_settings, httpx, psycopg, alembic, uvicorn" >nul 2>nul
if errorlevel 1 (
  echo Installing API dependencies into conda environment py3_11...
  python -m pip install -r requirements.txt
  if errorlevel 1 exit /b 1
)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
