@echo off
setlocal
set "ROOT=%~dp0.."
set "API_DIR=%ROOT%\services\api"
cd /d "%API_DIR%"
call conda activate base
if not exist ".venv\Scripts\python.exe" (
  echo Creating project virtualenv with conda base Python...
  python -m venv .venv
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
".venv\Scripts\python.exe" -c "import fastapi, sqlalchemy, pydantic, pydantic_settings, httpx, psycopg, alembic; print('API dependencies OK')"
