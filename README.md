# Social Media AI OS

An AI operating system for running a social-media-driven business: a CRM, a
content calendar/scheduler, AI-generated captions/hashtags/scripts, and twelve
persona-based AI agents, on top of a dashboard with real analytics.

This repo is a deliberately **scoped foundation**, not a claim that every
feature in the original spec (video editing pipeline with Whisper/YOLO/OpenCV,
eight live social-platform integrations, a visual automation builder, etc.) is
implemented. Everything that *is* here is real and working — no mocked
endpoints, no placeholder UI wired to nothing. See [`docs/ROADMAP.md`](docs/ROADMAP.md)
for what's intentionally left as an extension point, and why.

## Monorepo layout

```
apps/
  api/            FastAPI backend (Python 3.11, SQLAlchemy, Alembic, Celery)
  web/             Next.js 16 frontend (TypeScript, Tailwind v4, Radix UI)
  video-editor/    Standalone browser-based video editor (Vite + React + ffmpeg.wasm)
infra/
  k8s/             Kubernetes manifests
docker-compose.yml Local/single-host orchestration for postgres, redis, api, worker, beat, web
docs/              Architecture notes and roadmap
scripts/           Dev/deploy helper scripts
```

`apps/video-editor` predates this build-out and runs entirely client-side
(FFmpeg.wasm, no backend) — see its own README. It's not yet wired into the
`apps/web` dashboard as an "AI Video Editor" feature; that integration is
tracked in the roadmap.

## What's implemented

**Backend** (`apps/api`) — see `apps/api/app/`:

- **Auth**: JWT access/refresh tokens, Google Sign-In (ID token verified
  against Google's tokeninfo endpoint), RBAC (`owner`/`admin`/`member`/`viewer`)
  via a FastAPI dependency
- **CRM**: leads, deals, pipeline stages, tasks, notes — full CRUD, ownership-
  scoped access with admin override
- **Content calendar & scheduler**: posts with platform/format/status, a
  Celery-beat-driven scheduler that publishes due posts through a pluggable
  `Publisher` interface (`app/integrations/`)
- **AI content generation**: caption/hashtag/script generation through a
  pluggable provider strategy (`app/services/ai/`) hitting OpenAI, Anthropic,
  or Gemini directly over REST — no SDK lock-in
- **12 AI agents**: persona-based system prompts over the same provider
  layer; the CRM, Analytics, and Scheduler agents ground their responses with
  real data pulled from Postgres before calling the model
- **Dashboard analytics**: aggregates real `Metric` rows into follower/view/
  revenue trends, top/worst posts by engagement, and a transparent linear-
  regression 30-day growth projection (labeled as exactly that — not "AI
  predictions")
- **Notifications**: in-app notifications created on lead/deal/post events and
  daily/weekly/monthly summaries
- **Security**: rate limiting (slowapi), an audit log middleware, Pydantic
  validation everywhere, bcrypt password hashing

**Frontend** (`apps/web`) — Next.js App Router, dark glassmorphism theme:

- Auth pages, protected dashboard shell (sidebar + topbar + notification bell)
- Dashboard with live stat cards, Recharts trend charts, top/worst posts,
  growth projections, CRM snapshot
- CRM: leads table + drag-and-drop Kanban pipeline board
- Content calendar: scheduling form + status-tracked post list
- AI Content Studio: caption/hashtag/script generators with provider choice
- AI Agents: chat UI for all 12 agents
- Settings: profile + brand voice (used automatically by the generators)

Verified end-to-end in a real browser against the live backend (registration,
CRM, calendar, agents, settings) with zero console errors. `tsc`, `eslint`,
and `next build` all pass; 26 backend pytest tests pass against a real
Postgres database; ruff is clean.

## Quickstart

### Docker Compose (recommended)

```bash
cp apps/api/.env.example apps/api/.env   # add AI provider keys etc. if you want them
./scripts/dev-up.sh                      # or: docker compose up --build
```

- Web: http://localhost:3000
- API docs: http://localhost:8000/docs

### Manual (no Docker)

Backend:

```bash
cd apps/api
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # point DATABASE_URL at a local Postgres
alembic upgrade head
uvicorn app.main:app --reload
```

Run the test suite (needs a reachable Postgres database):

```bash
pytest
```

Frontend:

```bash
cd apps/web
npm install
cp .env.local.example .env.local
npm run dev
```

## Kubernetes

See [`infra/k8s/README.md`](infra/k8s/README.md).

## AI providers

Caption/hashtag/script generation and the AI agents need at least one of
`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `GEMINI_API_KEY` set in
`apps/api/.env`. Without one configured, those endpoints return a `503` with a
clear message — they never return fabricated output.

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — how the pieces fit together
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — what from the original spec isn't
  built yet, and the extension points designed for each
