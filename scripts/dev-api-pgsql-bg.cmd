@echo off
setlocal
set "ROOT=%~dp0.."
set "API_DIR=%ROOT%\services\api"
set "DATABASE_URL=postgresql+psycopg://postgres:postgres@192.168.1.49:5432/ai_learning_os"
set "SEED_DOMAIN_PACKS=true"

cd /d "%API_DIR%"

echo ================================================
echo Starting API with PostgreSQL (Background Mode)
echo ================================================
echo Database: %DATABASE_URL%
echo.

call conda activate py3_11
if errorlevel 1 (
  echo Failed to activate conda environment py3_11.
  echo Make sure Conda is initialized for cmd.exe and the py3_11 environment exists.
  exit /b 1
)

echo Checking dependencies...
python -c "import fastapi, sqlalchemy, pydantic, pydantic_settings, httpx, psycopg, alembic, uvicorn" >nul 2>nul
if errorlevel 1 (
  echo Installing API dependencies into conda environment py3_11...
  python -m pip install -r requirements.txt
  if errorlevel 1 exit /b 1
)

echo.
echo Starting uvicorn server in background on http://0.0.0.0:8000
echo Health check: http://localhost:8000/api/v1/health
echo.
echo To stop the server, use: taskkill /F /IM python.exe /FI "WINDOWTITLE eq *uvicorn*"
echo.

start "AI Learning OS API" /MIN python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

timeout /t 3 /nobreak >nul
echo Server started in background.
