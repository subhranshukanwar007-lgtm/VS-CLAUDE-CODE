# Roadmap

The original request asked for an exhaustive AI social media operating system:
video editing with scene/speech/emotion/object detection, eight live social
integrations, email/WhatsApp marketing, a visual automation builder,
competitor/trend tracking, and more — genuinely months of work for a team.
This document is the honest accounting of what's built (see the root
[`README.md`](../README.md)) versus what's deliberately left as a next step,
and where each one plugs into the existing architecture.

## Social platform integrations (Instagram, Facebook, YouTube, LinkedIn,
## Threads, Pinterest, TikTok, X, WhatsApp)

**Status:** scheduling engine is real and tested; actual publishing to any
platform is not implemented. `app/integrations/log_publisher.py` is the
working default (marks a post published, logs it, no network call).

**To add a platform:**
1. Implement OAuth connect flow, storing tokens on `SocialAccount`
   (`app/models/social_account.py` already has the fields).
2. Subclass `Publisher` (`app/integrations/base.py`) using that platform's
   official API to actually post.
3. Register it in `app/integrations/registry.py`.

Nothing else in the scheduling pipeline (`scheduler_service.py`,
`workers/tasks.py`, the calendar UI) needs to change.

## AI Video Engine (paste URL, download, scene split, speech/emotion/object
## detection, virality score, auto-improve)

**Status:** not built. `apps/video-editor` is a separate, working, purely
client-side trim/caption/export tool (FFmpeg.wasm) that predates this
build-out — it is not yet wired into the dashboard as a feature, and it has no
AI analysis layer (no Whisper transcription, no YOLO object detection, no
scene-cut detection, no virality scoring).

**Suggested path:** a new `apps/api` module using `ffmpeg-python` for
scene/shot splitting, `openai-whisper` (or the OpenAI Whisper API) for speech
recognition, and a hosted object-detection API or a YOLO model server for
object/camera-movement analysis, with results stored against a new `VideoAsset`
model. This is real infrastructure work (GPU or a hosted inference API) and
was out of scope for this pass.

## Automation Builder / Workflow Builder (visual, drag-and-drop)

**Status:** not built. The scheduler and Celery beat give you cron-style
automation (see `celery_app.py`'s `beat_schedule`) but there's no visual
builder or arbitrary trigger→action graph.

**Suggested path:** a `Workflow` model (trigger type, condition, action) plus
a Celery task that evaluates workflows on relevant events (lead created, post
published, etc. — the `notify()` call sites in `app/api/v1/` are exactly where
you'd also fire workflow evaluation).

## Email marketing, WhatsApp integration

**Status:** not built. `notification_service.py` only creates in-app
notifications today. Wiring in an email provider (Postmark/SES/SendGrid) or
WhatsApp Business API is a matter of adding a new notification "channel" and
calling it from the same `notify()` call sites.

## Competitor tracking, trend tracking, audience insights

**Status:** not built as scraping/tracking infrastructure. The **Trend Agent**
and **Research Agent** (`app/services/agents/personas.py`) exist and will
reason about trends/competitors if you describe them in the chat — they don't
independently scrape or monitor anything yet. Real tracking needs either
platform APIs with the right scopes or a scraping pipeline, both of which
carry ToS/legal considerations worth a deliberate decision, not a default.

## Revenue dashboard, sales funnel, conversion analytics beyond what's shown

**Status:** partially built. `Metric` supports `revenue`/`conversions`/`ctr`
kinds and the dashboard aggregates them; deal-stage-based funnel visualization
and multi-step conversion analytics are not built.

## S3-compatible media storage

**Status:** config is wired (`S3_ENDPOINT_URL` etc. in `app/config.py`) but no
upload endpoint exists yet. `Post.media_url` currently expects a URL you
already have (e.g. pasted from elsewhere). Adding an upload endpoint means a
presigned-URL flow using `boto3` against the configured S3-compatible
endpoint.

## Admin panel

**Status:** partial. `require_admin` RBAC exists and `GET /users`,
`PATCH /users/{id}/role` are admin-only, but there's no dedicated admin UI in
the frontend — admin actions currently require calling the API directly (see
`/docs` for the OpenAPI UI).

## Everything else marked done

Auth (JWT + Google), RBAC, CRM, content scheduling, the AI provider layer, all
12 AI agents, the dashboard, notifications, rate limiting, audit logging,
Docker Compose, and the Kubernetes manifests are implemented and tested — see
the root README's "What's implemented" section for specifics and how to
verify each yourself.
