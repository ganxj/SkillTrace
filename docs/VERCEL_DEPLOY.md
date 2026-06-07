# Vercel Deployment

There are two supported deployment shapes.

## Option A: One Vercel Project For Admin + API

Use this if you want the admin frontend and FastAPI API under the same Vercel domain.

Create a Vercel project with:

- Root Directory: repository root
- Config: `vercel.json`

The root config deploys:

- Next.js admin from `apps/admin_next`
- FastAPI serverless function from `api/index.py`
- API routes under `/api/v1/*`

Environment variables:

```text
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require
APP_ENV=production
SEED_DOMAIN_PACKS=true
AI_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_MODEL=...
OPENAI_BASE_URL=https://api.openai.com/v1
CORS_ORIGINS=["*"]
NEXT_PUBLIC_API_BASE_URL=/api/v1
```

After deployment:

```text
https://your-project.vercel.app
https://your-project.vercel.app/api/v1/health
```

## Option B: Two Vercel Projects

Use this if you want frontend and backend deployed independently.

This project can also be deployed as two Vercel projects:

1. FastAPI backend
2. Next.js admin frontend

Vercel does not run `docker-compose.yml`. Use an external Postgres database such as Vercel Postgres, Neon, Supabase, or Railway.

## Backend Project

Create a Vercel project with:

- Root Directory: `services/api`
- Runtime entry: `api/index.py`
- Config: `services/api/vercel.json`

Environment variables:

```text
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require
APP_ENV=production
SEED_DOMAIN_PACKS=true
AI_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_MODEL=...
OPENAI_BASE_URL=https://api.openai.com/v1
CORS_ORIGINS=["*"]
```

Health check after deployment:

```text
https://your-api-project.vercel.app/api/v1/health
```

## Admin Project

Create another Vercel project with:

- Root Directory: `apps/admin_next`
- Framework Preset: Next.js
- Config: `apps/admin_next/vercel.json`

Environment variables:

```text
NEXT_PUBLIC_API_BASE_URL=https://your-api-project.vercel.app/api/v1
API_INTERNAL_BASE_URL=https://your-api-project.vercel.app/api/v1
```

Open after deployment:

```text
https://your-admin-project.vercel.app
```

## Important Limits

Vercel serverless functions are not ideal for long PDF parsing and long AI generation jobs. The backend config sets `maxDuration` to `60`, which may still be too short for large PDFs. If course generation times out, deploy the FastAPI backend on a long-running host such as Railway, Render, Fly.io, a VPS, or Docker Compose, and keep only the admin frontend on Vercel.
