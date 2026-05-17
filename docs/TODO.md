# AI Learning OS TODO

## P0 - MVP Scaffold

- [x] Create monorepo structure.
- [x] Add Docker Compose Postgres.
- [x] Add FastAPI project with SQLAlchemy models.
- [x] Add Alembic initial migration.
- [x] Add quant v1 Domain Pack seed data.
- [x] Add Mock Tutor provider.
- [x] Add OpenAI provider switch and Responses API path.
- [x] Add Flutter mobile source for today, skills, review, tutor, and learning session.
- [x] Add Next.js admin read-only dashboard.
- [x] Document system boundary and startup flow.

## P1 - Learning Quality

- [ ] Replace the simple mastery update with a tested scoring policy per evidence type.
- [ ] Add explicit quiz task generation and answer checking.
- [ ] Add explanation rubric fields: correctness, clarity, transfer, misconception.
- [ ] Add review queue filters by domain and available time.
- [ ] Add session completion endpoint and reflection capture.
- [ ] Add seed data validation for domain packs.
- [ ] Add backend test suite for all MVP endpoints.

## P2 - Product Hardening

- [ ] Add user authentication and multi-user isolation.
- [ ] Add admin create/edit/import/export for Domain Packs.
- [ ] Add OpenAI streaming responses.
- [ ] Add structured tutor prompts per mode: teach, quiz, review, exam.
- [ ] Add Postgres migration-only startup mode for production.
- [ ] Add mobile API base URL configuration by build flavor.
- [ ] Add offline mobile cache for current review queue.

## P3 - More Domains

- [ ] Add math Domain Pack.
- [ ] Add programming Domain Pack.
- [ ] Add English Domain Pack.
- [ ] Add cross-domain learner summary view.
- [ ] Add domain-neutral learning analytics.

