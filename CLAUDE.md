# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SkillTrace is a mobile-first AI learning OS built around a domain-agnostic learning loop: recommend next step → short session → collect evidence → update state → schedule review. The system uses pluggable **domain packs** (JSON content modules) rather than hardcoded subject matter.

**Important boundary**: This is a learning system only. It does not execute quant backtests, run strategies, manage portfolios, or connect to trading systems. The quant domain pack (`domain_packs/quant_v1`) teaches quant concepts as learning content.

## Repository Structure

```
apps/
  mobile_flutter/      Flutter mobile app for learning sessions
  admin_next/          Next.js admin console (read-only dashboard)
services/
  api/                 FastAPI + SQLAlchemy + Alembic backend
domain_packs/
  quant_v1/            First seed domain pack (JSON)
docs/
  ARCHITECTURE.md      System boundaries and data flow
  TODO.md              MVP and future roadmap
scripts/               Windows batch scripts for local dev
```

## Development Commands

### Start the API Server

**With PostgreSQL (Recommended):**
```bash
scripts\dev-api-pgsql.cmd          # Interactive mode
scripts\dev-api-pgsql-bg.cmd       # Background mode
```

Uses PostgreSQL at `192.168.1.49:5432` (from docker-compose.yml).

**With SQLite (Quick demo):**
```bash
scripts\dev-api-sqlite.cmd
```

Uses local SQLite file, no external database needed.

**Manual startup:**
```bash
cd services/api
conda activate py3_11
python -m uvicorn app.main:app --reload --port 8000
```

Runs on `http://127.0.0.1:8000`. Health check at `/api/v1/health`.

### Start the Admin Console

```bash
scripts\dev-admin.cmd
```

Runs on `http://127.0.0.1:3000`.

Manual startup:
```bash
cd apps/admin_next
npm install
npm run dev
```

### Run the Mobile App

Live debug session:
```bash
scripts\mobile-run.cmd
```

Build and install APK on connected Android device:
```bash
scripts\mobile-build-install.cmd
```

This also runs `adb reverse tcp:8000 tcp:8000` to route mobile API calls to localhost.

### Database Migrations

Generate a new migration:
```bash
cd services/api
.venv\Scripts\alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
.venv\Scripts\alembic upgrade head
```

Rollback one migration:
```bash
.venv\Scripts\alembic downgrade -1
```

## Core Architecture

### Learning System Entities

The domain-neutral core revolves around these SQLAlchemy models (all in `services/api/app/models/learning.py`):

- **DomainPack**: A pluggable subject area (e.g., quant, math, programming)
- **SkillNode**: A single learnable concept or ability
- **SkillEdge**: Prerequisite relationships between skills
- **LearnerSkillState**: Per-user mastery, confidence, last_seen, review_due for each skill
- **LearningSession**: A short learning interaction (5-15 min)
- **MasteryEvidence**: Quiz, explanation, or review evidence with score and deltas
- **TutorMessage**: Conversational tutor interaction history
- **ContentImport**: Tracks import jobs for generating domain packs from PDFs/DOCX

### Domain Pack System

Domain packs are JSON files at `domain_packs/<slug>/domain.json` that seed the database on startup when `SEED_DOMAIN_PACKS=true`.

Each pack defines:
- Domain metadata (slug, name, version, description)
- Skill nodes (slug, title, summary, content, lesson_explain, questions_json, key_points_json)
- Skill edges (prerequisite relationships)

**Rule**: Never add domain-specific columns to core learning tables. Keep subject matter in the domain pack JSON and the generic `content`/`lesson_explain` text fields.

To add a new domain pack:
1. Create `domain_packs/<new_slug>/domain.json` following the quant_v1 structure
2. Restart the API with `SEED_DOMAIN_PACKS=true`
3. The seeder (`app/services/seed.py`) will load it into the database

### Authentication

MVP uses demo authentication:
- Mobile/admin sends `X-User-Id` header (optional)
- Backend falls back to `settings.demo_user_id` ("demo-user")
- No password, no JWT, no session management yet

**When adding real auth later**: Update `app/api/v1/deps.py` and add user management endpoints.

### Tutor Provider Abstraction

The backend supports pluggable tutor providers via `app/services/tutor/`:

**Mock provider** (default):
```bash
AI_PROVIDER=mock
```
Returns deterministic canned responses. No API key needed.

**OpenAI-compatible provider**:
```bash
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4
OPENAI_BASE_URL=https://api.openai.com/v1
```

Uses the `/v1/responses` endpoint. If `AI_PROVIDER=openai` but no API key, the backend returns a clear error rather than silently falling back to mock.

## API Endpoints

Base path: `/api/v1`

Core routes (see `app/api/v1/router.py`):
- `GET /health` - Health check
- `GET /domains` - List domain packs
- `GET /skills?domain_slug=quant_v1` - List skills for a domain
- `POST /sessions` - Create learning session
- `POST /evidence` - Submit mastery evidence
- `GET /evidence` - Query evidence history
- `GET /learner/state` - Get learner skill states
- `GET /review/next` - Get next due review items
- `POST /tutor/messages` - Send tutor chat message

## Development Patterns

### Running a Single Test

The backend does not yet have a test suite (see `docs/TODO.md` P1). When tests are added, use:
```bash
cd services/api
.venv\Scripts\pytest tests/test_specific.py::test_function -v
```

### Checking Code Quality

No linter/formatter is configured yet. When adding:
- Backend: `ruff` or `black` + `mypy`
- Frontend: ESLint + Prettier (admin_next), `flutter analyze` (mobile)

### Local Database Reset

To wipe and reseed the database:
```bash
cd services/api
.venv\Scripts\alembic downgrade base
.venv\Scripts\alembic upgrade head
# Restart API with SEED_DOMAIN_PACKS=true to reseed domain packs
```

## Important Constraints

1. **Domain-neutral core**: Do not add columns like `backtest_result` or `math_problem_type` to core tables. Keep subject content in domain pack JSON or generic text fields.

2. **No quant execution**: This system teaches quant concepts but does not run backtests, execute strategies, or connect to trading APIs. Keep those in a separate system.

3. **Windows-first dev environment**: The local tooling (`.tools/`, batch scripts) is optimized for Windows. Cross-platform support is a future goal.

4. **Demo mode**: Current authentication is intentionally minimal. Real multi-user isolation and auth are on the P2 roadmap (`docs/TODO.md`).

5. **Seeding on startup**: The API seeds domain packs from JSON on startup when `SEED_DOMAIN_PACKS=true`. In production, use migration-only startup mode (future P2 work).

## Environment Variables

Key settings in `services/api/.env`:

```bash
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/ai_learning_os
SEED_DOMAIN_PACKS=true
AI_PROVIDER=mock  # or "openai"
OPENAI_API_KEY=   # required if AI_PROVIDER=openai
OPENAI_MODEL=     # e.g., gpt-4
DEMO_USER_ID=demo-user
```

See `services/api/app/core/config.py` for all settings.

## Mobile App Configuration

The Flutter app hardcodes API base URL in code (not yet environment-aware). To change:
- Update the API base URL in `apps/mobile_flutter/lib/config/` (when added) or wherever the HTTP client is configured
- Rebuild and reinstall the APK

P2 work includes build flavors for dev/staging/prod API endpoints.
