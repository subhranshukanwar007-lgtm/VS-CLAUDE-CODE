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
- **6 AI agents**: content, crm, sales, analytics, money, support — persona
  system prompts over the same provider layer. Four of them (crm, sales,
  analytics, money) ground their responses in real data pulled from Postgres
  before calling the model; the Sales agent gets your actual hot leads by name.
  Trimmed down from twelve: the rest were job titles from the original spec that
  a solo operator never opened
- **Dashboard analytics**: aggregates real `Metric` rows into follower/view/
  revenue trends, top/worst posts by engagement, and a transparent linear-
  regression 30-day growth projection (labeled as exactly that — not "AI
  predictions")
- **CRM follow-up automation**: a daily Celery beat job flags leads with no
  notes/tasks/status changes in a user-configurable window (`User.follow_up_days`,
  default 5, 0 disables it), drafts an AI follow-up message grounded in the
  lead's details, creates a reminder task, and notifies the owner —
  self-resets each run so the same lead isn't re-flagged until the window
  passes again after the last follow-up. Also available on demand via
  `POST /leads/{id}/follow-up` (a "suggest follow-up" button in the CRM UI)
- **AI video generation**: prompt (or image, for image-to-video) in, a real
  video out, via a pluggable `VideoProvider` (`app/services/video/`) — ships
  with two working integrations, Replicate (broad model catalog) and
  Higgsfield (avatar/persona "soul" models), both verified against each
  vendor's own API docs. Generation is async (jobs take 30s–minutes), so it's
  submit-then-poll: a Celery beat task polls every in-flight job every 30s,
  and `GET /video/{id}` also polls live for a faster feel in the UI.
  `POST /video/{id}/attach-to-post` turns a finished video straight into a
  draft Post in the content calendar, reusing the scheduler you already have.
  `POST /video/{id}/thumbnail` generates a thumbnail image (Replicate
  `flux-schnell`) for it.
- **Real publishing to Instagram, Facebook and Threads** (`app/integrations/meta_publisher.py`):
  Instagram's two-step container flow (`/media` → `/media_publish`, polling
  container status for video since transcoding is async), Facebook Page feed /
  photos / videos / Stories, and Threads via `graph.threads.net` with its
  500-character cap. Gated behind a **per-platform auto-publish toggle that
  defaults to off** — a due post drops back to draft and notifies you instead of
  posting unattended. `POST /posts/{id}/publish` is the approve action and runs
  the same code path as the scheduler. OAuth tokens are encrypted at rest
  (Fernet, keyed off `SECRET_KEY`)
- **Buying-intent scoring** (`app/services/intent_service.py`): reads what each
  lead actually wrote and scores HOT/WARM/COLD with a reason, so the one person
  who asked "how much?" doesn't get buried. A keyword layer (including Hinglish)
  runs synchronously on the webhook — Meta retries slow webhooks, so an obvious
  buying question alerts within the same second — and an AI pass refines the rest
  in the background. Notifies once on the transition into HOT, never downgrades a
  score, and leaves a lead who has said nothing unscored rather than recording a
  confident "cold"
- **Engagement capture**: a real Meta webhook receiver
  (`app/services/engagement_service.py`, `POST /api/v1/webhooks/meta`) that
  verifies Meta's X-Hub-Signature-256 HMAC and turns comments on your
  Instagram/Facebook posts into CRM leads automatically, deduped per
  commenter. Requires a real Meta Developer App + a public HTTPS callback URL
  to actually receive events — see `.env.example` for setup.
- **Notifications**: in-app notifications created on lead/deal/post/follow-up/
  video/engagement events and daily/weekly/monthly summaries
- **Security**: rate limiting (slowapi), an audit log middleware, Pydantic
  validation everywhere, bcrypt password hashing

**Frontend** (`apps/web`) — Next.js App Router, dark glassmorphism theme:

- Auth pages, protected dashboard shell (sidebar + topbar + notification bell)
- **Command Center** (`/home`, the landing page): one screen with hot leads to
  talk to, drafts awaiting approval with an inline Approve button, what's going
  out next, the money numbers, and lead breakdowns by platform and country
- Analytics dashboard with live stat cards, Recharts trend charts, top/worst posts,
  growth projections, CRM snapshot
- CRM: leads table + drag-and-drop Kanban pipeline board, with a stale-lead
  indicator and a one-click "suggest follow-up" action
- Content calendar: scheduling form + status-tracked post list
- AI Content Studio: caption/hashtag/script generators with provider choice
- AI Video Studio: provider picker (Replicate/Higgsfield), prompt-to-video
  generation with live status polling, video preview, one-click thumbnail
  generation, and a "create post from this video" action
- AI Agents: chat UI for the 6 agents
- Settings: profile, brand voice, follow-up window, connected accounts,
  per-platform auto-publish toggles, auto-DM template and trigger keywords,
  Threads keywords, posts per day, and reply language (English / Hinglish in
  Roman script / Hindi) — everything editable in the browser, no code or restart

Verified end-to-end in a real browser against the live backend (registration,
CRM, calendar, agents, settings, follow-up automation, video generation) with
zero console errors. `tsc`, `eslint`, and `next build` all pass; 139 backend
pytest tests pass against a real Postgres database; ruff is clean.

`tests/test_migrations.py` runs the migration chain against a scratch database
and asserts every Postgres enum's labels match its Python enum. That test exists
because the rest of the suite builds its schema with `create_all()` rather than
migrations, which let five miscased enum labels ship — they were unwritable by
the ORM, so follow-up notifications, video notifications and every Higgsfield
generation raised `invalid input value for enum` in any migrated database while
tests stayed green.

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

- [`docs/START_HERE.md`](docs/START_HERE.md) — **start here**: the whole process
  step by step, from installing Docker to your daily routine
- [`docs/COWORK_TEAM.md`](docs/COWORK_TEAM.md) — the judgement half: competitor
  research, trust rules, and weekly review routines for the things automation
  can't do
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — how the pieces fit together
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — what from the original spec isn't
  built yet, and the extension points designed for each
