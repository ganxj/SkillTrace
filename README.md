# SkillTrace

Mobile-first AI learning OS for learner state, mastery evidence, and domain packs.

SkillTrace is an open-source scaffold for building a fragmented-time learning product. It focuses on the learning loop itself: recommend a small next step, start a short session, collect mastery evidence, update learner state, and schedule review.

当前 MVP 的首个领域包是量化学习，但系统边界刻意保持通用：量化只是第一个 `DomainPack`，后续可以替换或扩展到数学、编程、英语、考试复习等主题。

## What This Is

- A Flutter mobile app for short learning sessions.
- A FastAPI backend for domains, skills, sessions, evidence, review, and tutor messages.
- A Next.js admin console for observing domain packs and learner state.
- A domain-pack structure that keeps subject content separate from the core learning system.
- A Tutor Provider abstraction that defaults to deterministic Mock responses and can be configured for OpenAI.

## What This Is Not

SkillTrace does not run quant backtests, execute strategies, connect trading accounts, or provide a strategy lab. Quant knowledge can be learned here; actual quant research and trading workflows should live in a separate system.

## Repository Structure

```text
apps/mobile_flutter      Flutter learning app
apps/admin_next          Next.js admin console
services/api             FastAPI + SQLAlchemy backend
domain_packs/quant_v1    First seed domain pack
docs/ARCHITECTURE.md     System boundaries and data flow
docs/TODO.md             MVP and future roadmap
scripts                  Local development helpers
```

## MVP Features

- Domain pack loading for `quant_v1`.
- Skill graph with prerequisite edges.
- Demo learner identity through `X-User-Id` or a default demo user.
- Learning session creation.
- Mastery evidence submission.
- Learner skill state updates.
- Simple review recommendation.
- Mock Tutor and OpenAI-compatible Tutor Provider.
- Flutter pages for home, skill path, learning session, review, and tutor chat.
- Read-only admin views for domains, skills, learner state, and evidence.

## Quick Start

This project is currently optimized for local development on Windows.

### 1. Start The API

**Option A: PostgreSQL (Recommended for production-like testing)**

```bat
scripts\dev-api-pgsql.cmd
```

Uses PostgreSQL at `192.168.1.49:5432`. Make sure PostgreSQL is running first.

For background mode:

```bat
scripts\dev-api-pgsql-bg.cmd
```

**Option B: SQLite (Quick local demo)**

```bat
scripts\dev-api-sqlite.cmd
```

Uses a local SQLite database file. No external database needed.

**API Endpoint:**

```text
http://127.0.0.1:8000
```

Health check:

```text
http://127.0.0.1:8000/api/v1/health
```

### 2. Start The Admin Console

```bat
scripts\dev-admin.cmd
```

Then open:

```text
http://127.0.0.1:3000
```

### 3. Run The Mobile App On Android

With an Android phone connected and USB debugging enabled:

```bat
scripts\mobile-build-install.cmd
```

This script builds the Flutter debug APK, installs it on the connected device, sets `adb reverse tcp:8000 tcp:8000`, and launches the app.

For a live Flutter debug session:

```bat
scripts\mobile-run.cmd
```

The local Flutter SDK and Android helper files are kept under `.tools/`, which is ignored by Git.

## API Overview

Base path:

```text
/api/v1
```

Core endpoints:

- `GET /health`
- `GET /domains`
- `GET /skills`
- `POST /sessions`
- `POST /evidence`
- `GET /learner/state`
- `GET /review/next`
- `POST /tutor/messages`

Local MVP authentication is intentionally minimal. Use `X-User-Id` during development, or let the backend fall back to the demo user.

## Tutor Provider

The backend defaults to Mock Tutor:

```text
AI_PROVIDER=mock
```

To enable OpenAI-compatible generation:

```text
AI_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_MODEL=...
OPENAI_BASE_URL=https://api.openai.com/v1
```

The OpenAI provider is wired for the Responses API:

```text
POST /v1/responses
```

If `AI_PROVIDER=openai` is set without `OPENAI_API_KEY`, the API returns a clear configuration error instead of silently falling back.

## Domain Packs

Domain packs are replaceable content modules. The current seed pack lives at:

```text
domain_packs/quant_v1/domain.json
```

It includes nodes such as market basics, probability and statistics, Python tooling, backtesting concepts, risk control, and factor models. These are learning topics only; they do not introduce execution or trading capabilities.

## Roadmap

Near-term:

- Improve the mastery update rules.
- Add richer review scheduling.
- Expand admin editing for domain packs.
- Add import/export for domain content.
- Add authentication and real multi-user isolation.

Later:

- Add more domain packs, such as mathematics, programming, and English.
- Add richer question types and adaptive learning flows.
- Add analytics for learning progress and content quality.
- Package a smoother first-run developer experience.

## Contributing

Contributions are welcome, especially around learning science, domain-pack authoring, mobile UX, and backend reliability.

Before opening a pull request, please keep these boundaries in mind:

- Keep the core learning system domain-agnostic.
- Keep quant research, backtesting, strategy execution, and trading integration out of this repository.
- Prefer small, reviewable changes.
- Update `docs/TODO.md` or `docs/ARCHITECTURE.md` when changing product scope or system boundaries.

## License

No license file has been added yet. Add a license, such as MIT or Apache-2.0, before publishing the repository as open source.
