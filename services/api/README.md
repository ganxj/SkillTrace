# API Service

FastAPI backend for AI Learning OS.

## Run

```powershell
copy .env.example .env
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\uvicorn app.main:app --reload --port 8000
```

The API seeds `domain_packs/*/domain.json` on startup when `SEED_DOMAIN_PACKS=true`.

## Endpoints

- `GET /api/v1/health`
- `GET /api/v1/domains`
- `GET /api/v1/skills?domain_slug=quant_v1`
- `POST /api/v1/sessions`
- `POST /api/v1/evidence`
- `GET /api/v1/evidence`
- `GET /api/v1/learner/state`
- `GET /api/v1/review/next`
- `POST /api/v1/tutor/messages`

