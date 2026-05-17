# AI Learning OS MVP

Mobile-first fragmented learning system scaffold.

This repository intentionally separates the learning system from any quant research, backtesting, strategy execution, or trading workflow. Quant is only the first `DomainPack` used to validate the learning loop.

## Structure

```text
apps/mobile_flutter   Flutter learning app
apps/admin_next       Next.js admin console
services/api          FastAPI + SQLAlchemy backend
domain_packs/quant_v1 Quant learning seed pack
docs                  Architecture notes and TODOs
```

## Local Startup

1. Start Postgres:

```powershell
docker compose up -d postgres
```

2. Start API:

```powershell
cd services/api
copy .env.example .env
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

Or from the repo root:

```powershell
.\scripts\dev-api.ps1
```

If Docker/Postgres is not running yet, use the SQLite demo API:

```powershell
.\scripts\dev-api-sqlite.ps1
```

If PowerShell scripts are blocked, use the command-file versions:

```bat
scripts\dev-api-conda.cmd
scripts\dev-admin.cmd
```

3. Start admin console:

```powershell
cd apps/admin_next
npm install
npm run dev
```

Or from the repo root:

```powershell
.\scripts\dev-admin.ps1
```

4. Start mobile app after installing Flutter:

```powershell
cd apps/mobile_flutter
flutter create . --platforms=android,ios,web
flutter pub get
flutter run
```

Or from the repo root:

```powershell
.\scripts\dev-mobile.ps1
```

If you run the mobile app on an Android emulator, set `ApiClient(baseUrl: "http://10.0.2.2:8000/api/v1")` in `lib/main.dart`.

## Tutor Provider

The backend defaults to Mock Tutor:

```text
AI_PROVIDER=mock
```

To enable OpenAI:

```text
AI_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_MODEL=...
OPENAI_BASE_URL=https://api.openai.com/v1
```

The provider calls:

```text
POST https://api.openai.com/v1/responses
```
