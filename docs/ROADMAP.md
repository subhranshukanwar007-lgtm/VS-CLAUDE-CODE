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

**Status:** outbound publishing is not implemented (scheduling engine is real
and tested; `app/integrations/log_publisher.py` is the working default —
marks a post published, logs it, no network call). **Inbound comment capture
is implemented** for Instagram/Facebook: register your business account's ID
(Settings → Connected accounts, or `POST /social-accounts`) and configure a
Meta webhook pointing at `/api/v1/webhooks/meta` (see `.env.example` for the
setup steps) — comments on your posts get verified via Meta's real
X-Hub-Signature-256 HMAC scheme and turned into CRM leads automatically
(`app/services/engagement_service.py`), deduped per commenter so repeat
engagement adds a note instead of a duplicate lead. This can't be tested
fully end-to-end without a real Meta Developer App and a public HTTPS URL for
the callback, which this repo can't provide on its own.

**To add outbound publishing for a platform:**
1. Implement OAuth connect flow, storing tokens on `SocialAccount`
   (`app/models/social_account.py` already has the fields — the current
   `/social-accounts` API only sets `handle`/`external_account_id` today, not
   tokens; a real OAuth flow would populate those too).
2. Subclass `Publisher` (`app/integrations/base.py`) using that platform's
   official API to actually post.
3. Register it in `app/integrations/registry.py`.

Nothing else in the scheduling pipeline (`scheduler_service.py`,
`workers/tasks.py`, the calendar UI) needs to change.

## AI Video Engine

This originally covered two different things — **generating** new video from a
prompt, and **analyzing/editing** video someone already has (paste URL,
download, scene split, speech/emotion/object detection, virality score,
auto-improve). Their status now differs:

### Generation — built

`app/services/video/` + `app/services/video_service.py` + the `/video/*` API +
the AI Video Studio page. Submit a prompt (optionally with a source image for
image-to-video), poll until it's ready, preview it, attach it to a post. Two
pluggable providers ship: Replicate (verified against Replicate's own API
docs) and Higgsfield (verified against Higgsfield's own docs — base URL, auth
scheme, and the `soul` model line are confirmed real; the exact request
fields for *training* a persistent avatar on your specific face/photos, and
for voice cloning specifically, weren't independently confirmed from public
docs, so those go in via the generic `extra_params` passthrough rather than a
bespoke UI — fill them in per your own Higgsfield dashboard once you have an
account, and treat that mapping as unverified until you've confirmed it
against a real response).

### Download/analyze an existing video — not built

Paste-a-URL download, scene splitting, Whisper transcription, emotion/object
detection, camera-movement analysis, virality scoring, and "generate a better
version" of existing footage are all still not built. `apps/video-editor` is
a separate, working, purely client-side trim/caption/export tool (FFmpeg.wasm)
that predates this build-out — it is not wired into the dashboard, and it has
no AI analysis layer.

**Suggested path:** a new `apps/api` module using `ffmpeg-python` for
scene/shot splitting, `openai-whisper` (or the OpenAI Whisper API) for speech
recognition, and a hosted object-detection API or a YOLO model server for
object/camera-movement analysis, with results stored against a new `VideoAsset`
model. This is real infrastructure work (GPU or a hosted inference API) and
remains out of scope.

## Automation Builder / Workflow Builder (visual, drag-and-drop)

**Status:** not built as a general visual builder. What exists is one concrete,
hardcoded automation of this shape — CRM lead follow-up (`services/followup_service.py`,
wired into `celery_app.py`'s `beat_schedule` as `lead-follow-up-automation`):
detect a condition (lead inactive for N days), draft with AI, and act (create a
task + notify). It's a real trigger→condition→action pipeline, just not a
generic or user-configurable one yet.

**Suggested path:** a `Workflow` model (trigger type, condition, action) plus
a Celery task that evaluates workflows on relevant events (lead created, post
published, etc. — the `notify()` call sites in `app/api/v1/` are exactly where
you'd also fire workflow evaluation).

## Email marketing, WhatsApp integration, calendar meeting booking

**Status:** not built. `notification_service.py` only creates in-app
notifications today — lead follow-ups, for example, create a task and an
in-app notification, not an actual outbound email. Wiring in an email
provider (Postmark/SES/SendGrid) or WhatsApp Business API is a matter of
adding a new notification "channel" and calling it from the same `notify()`
call sites. Booking an actual meeting on someone's calendar (as opposed to
scheduling a *content* post, which is already built) needs Google Calendar
OAuth scopes beyond the sign-in scope currently used, plus a
`CalendarEvent`-style model — a distinct feature from the content scheduler.

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
