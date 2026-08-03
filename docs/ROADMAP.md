# Roadmap

The original request asked for an exhaustive AI social media operating system:
video editing with scene/speech/emotion/object detection, eight live social
integrations, email/WhatsApp marketing, a visual automation builder,
competitor/trend tracking, and more — genuinely months of work for a team.
This document is the honest accounting of what's built (see the root
[`README.md`](../README.md)) versus what's deliberately left as a next step,
and where each one plugs into the existing architecture.

## Social platform integrations

**Status: outbound publishing is now real for Instagram, Facebook and Threads**
(`app/integrations/meta_publisher.py`), all three through one Meta developer app.
Instagram uses the two-step container flow and polls container status for video
because transcoding is asynchronous; Facebook covers feed/photos/videos plus the
separate Page Stories endpoints; Threads uses `graph.threads.net` and enforces
its 500-character cap. Tokens are encrypted at rest with Fernet
(`app/core/token_crypto.py`).

Publishing is gated behind a per-platform auto-publish toggle that **defaults to
off**: a due post drops back to DRAFT and notifies its owner rather than posting
unattended, and `POST /posts/{id}/publish` is the approve action. That default is
deliberate — a new account posting AI video unattended every day is how accounts
get restricted.

**Still on `LogPublisher`** (marks published, no network call): YouTube, LinkedIn,
Pinterest, TikTok, X.

**X / Twitter is a deliberate omission, not an oversight.** X removed its free
API tier for new developers on 2026-02-06; posting is now pay-per-use at roughly
$0.015 per post and $0.20 for a post containing a link. The `Publisher` interface
makes adding it a single file whenever that cost is acceptable.

**Inbound comment capture** is implemented for Instagram/Facebook: register your
business account's ID (Settings → Connected accounts) and configure a Meta
webhook at `/api/v1/webhooks/meta`. Comments are verified with Meta's real
X-Hub-Signature-256 HMAC and become CRM leads, deduped per commenter. This can't
be exercised end to end without a real Meta app and a public HTTPS callback URL.

**What each platform's API genuinely allows**, since these limits shaped the
design rather than being incidental:

| Platform | Publish | Stories | DMs | Keyword search |
| --- | --- | --- | --- | --- |
| Instagram | yes | yes (`media_type=STORIES`) | yes — private replies to comments: 7-day window, one reply per comment ever | no |
| Facebook | yes | yes (`/photo_stories`, `/video_stories`) | yes | no |
| Threads | yes | **no — Threads has no Stories** | **no — Threads has no DM API at all** | yes (`/keyword_search`) |
| Reddit | n/a | n/a | n/a | free read; **writing needs manual approval**, self-serve signup closed, 2-4 week wait, free tier non-commercial |
| Quora | n/a | n/a | n/a | **no public API has ever existed** |

`GET /automation/capabilities` exposes the publish/Stories columns so the UI can
grey out what it can't actually do instead of offering a toggle that silently
does nothing.

**To add outbound publishing for another platform:**
1. Implement its OAuth connect flow, storing tokens on `SocialAccount` via
   `encrypt_token` (the model has the fields; `/social-accounts` currently only
   sets `handle`/`external_account_id`).
2. Subclass `Publisher` (`app/integrations/base.py`) using that platform's
   official API.
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

**Status:** not built as a general visual builder. What exists is three concrete
trigger→condition→action automations, each real and running on Celery beat:

- **Lead follow-up** (`services/followup_service.py`) — lead inactive for N days
  → AI drafts a message → creates a task + notifies.
- **Buying-intent scoring** (`services/intent_service.py`) — new engagement →
  score the lead's own words → notify on the transition into HOT.
- **Publish or hold** (`services/scheduler_service.py`) — post due → publish if
  auto-publish is on for that platform, otherwise return it to DRAFT and ask.

They're user-configurable through `AutomationSetting` (Settings UI: keywords,
templates, per-platform toggles, cadence, reply language) but not yet composable
into arbitrary new workflows.

**Suggested path:** a `Workflow` model (trigger type, condition, action) plus a
Celery task evaluating workflows on relevant events — the `notify()` call sites
in `app/api/v1/` are exactly where you'd also fire workflow evaluation.

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

**Status:** not built. The Trend and Research personas were removed in the agent
trim (twelve down to six) precisely because they implied monitoring the app
doesn't do — an agent that can only reason about trends you describe to it is
worse than no agent, because it looks like tracking.

Real tracking needs either platform APIs with the right scopes or a scraping
pipeline. The one genuinely open door is **Threads `/keyword_search`**, which is
free and permits finding public posts by keyword; a "Questions Inbox" built on it
(find people asking questions in your niche, AI-draft a public reply, you
approve) is modelled in `app/models/question_opportunity.py` but the search job
and UI are not built yet. Reddit search would slot into the same model, though
posting replies there needs Reddit's manual OAuth approval.

## Lead geography

**Status:** `Lead.country` exists with CRM filtering and Command Center
breakdowns. It is set manually or from ad targeting and is deliberately **never
inferred** — Meta's comment webhook does not include the commenter's country, and
guessing it from a name or language would be worse than leaving it blank.

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
