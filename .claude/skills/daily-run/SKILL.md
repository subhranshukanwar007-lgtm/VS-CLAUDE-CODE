---
name: daily-run
description: The whole content leg in one command - read what's working, pick today's angle, write the hooks and script, generate the video in Higgsfield, check it before it goes out, publish it, and arm the comment-to-DM trigger so the CTA actually fires. Use when the user says run the daily, make today's video, or asks the system to do its job.
---

# Daily run

One command, from "what should I post" to a published reel with the auto-DM
armed behind it.

Nothing here is a black box. Every stage either uses a real API or stops and says
it can't. If a stage fails, **do not fake its output and continue** — report it
and carry on with the stages that still work. A silent half-run is worse than a
loud stop, because the user finds out three days later that nothing posted.

## Before you start

Get an access token once:

```
POST {API}/api/v1/auth/login   {"email": ..., "password": ...}
→ .tokens.access_token
```

`{API}` is `http://localhost:8000` when they're running `docker compose up`.
Credentials come from the user or from their environment — **never** put them in
a file, a commit, or a message. If the API doesn't answer, stop: everything below
needs it.

Check the Higgsfield balance early with `mcp__HIGGSFIELD__balance`. Finding out
there are no credits *after* writing a script wastes the user's time.

---

## Stage 1 — Read what actually happened

Three calls, in parallel:

| | |
|---|---|
| `GET /api/v1/dashboard/command-center` | what needs a human today |
| `GET /api/v1/goals/performance` | which content goal produces leads |
| `GET /api/v1/dashboard/growth-target` | are they on pace for 100K |

**Read `performance` correctly.** Rank by `leads_per_post`, never by raw `leads`
— otherwise whichever goal they posted most often always wins. Ignore any goal
with `published_posts == 0`; no data is not a result.

If `unattributed_leads` is climbing faster than the attributed ones, say so.
That means tracking is broken, not that content is working, and every number
below it is less trustworthy than it looks.

## Stage 2 — Find the angle

Two sources, in this order of trust:

1. **Their own numbers.** The best-performing goal from Stage 1, and which posts
   inside it earned leads. This is the only evidence about *their* audience.
2. **Live competitor ads** — `mcp__meta_ad__ads_library_search`. Public by law,
   and it shows what people are paying to keep running. An ad that has been live
   for months is working; that's a stronger signal than any view count.

**What you cannot get, and must not pretend to:** a competitor's organic reach,
their engagement rate, their save rate, their follower growth. Those are private.
Any "viral hook database" is someone's guess. If you cite a hook, cite where it
came from.

Pick **one** idea. Name a specific situation, not a condition — "the back pain
from sitting nine hours at a desk", not "back pain".

## Stage 3 — Write the package

```
POST /api/v1/video/script-package
{"topic": ..., "platform": "instagram", "duration_seconds": 30}
```

Returns hooks, timed beats (`spoken` / `caption` / `broll`), the Higgsfield
prompt, the post caption, one CTA and hashtags. Language follows their
`reply_language` setting — usually **Hinglish in Roman script**.

Read the `/script` skill's hard rules before accepting the output. The one that
matters most: **never let an invented statistic or medical claim through.** Being
caught on one costs more credibility than a month of posting earns. If a number
would make a line stronger, rewrite the line without the number.

## Stage 4 — Generate the video

The creator has their **own trained avatar and cloned voice** inside Higgsfield.
Check with `mcp__HIGGSFIELD__show_characters` and use theirs. The
`higgsfield_prompt` from Stage 3 describes framing, motion and delivery only — it
never describes a person, because the avatar supplies that.

If unsure which model fits, ask first:
`mcp__HIGGSFIELD__models_explore(action:'recommend')`. Then
`mcp__HIGGSFIELD__generate_video` → `mcp__HIGGSFIELD__jobs_wait` →
`mcp__HIGGSFIELD__show_generation_by_ids` for the finished URL.

> The app's own `POST /api/v1/video/generate` is a *different* path — it calls
> Higgsfield server-side with `HIGGSFIELD_API_KEY` and is what the Video Studio
> page uses. Here you are generating through MCP and handing the app a finished
> URL. Don't run both for one video.

## Stage 5 — Check it before anyone sees it

This is the stage people skip, and it's the cheap one.

- `mcp__HIGGSFIELD__virality_predictor` on the generated video — hook strength,
  retention risk, attention. Treat it as a second opinion, not a verdict.
- **Watch the first two seconds yourself.** They decide whether anyone watches at
  all. If the hook doesn't land in frame one, regenerate that beat rather than
  posting and hoping.
- Run the `/critic` skill on the hook and CTA.

If the check says the hook is weak, go back to Stage 3. Regenerating costs
credits; posting a weak reel costs a day of reach.

## Stage 6 — Publish

```
POST /api/v1/posts
{"platform": "instagram", "format": "reel", "caption": ..., "hashtags": ...,
 "media_url": <the Higgsfield URL>, "goal": <the goal from Stage 1>}
```

Then either:

- `POST /api/v1/posts/{id}/publish` — goes out now, or
- `PATCH` with `scheduled_at` and let the Celery beat publish it (60s cadence).

**Check `GET /api/v1/automation/capabilities` first.** It reports which platforms
can genuinely publish. Instagram, Facebook and Threads work. X, YouTube, TikTok,
LinkedIn and Pinterest do not — offering them would be a promise the app can't
keep.

**Respect the auto-publish toggle.** If `auto_publish` is off for that platform,
leave the post as a draft and tell the user it's waiting for them. Silence means
"ask me", never "post it".

## Stage 7 — Arm the DM trigger

**The stage that makes the whole thing pay.** The caption says "comment PLAN".
If `dm_trigger_keywords` doesn't contain `plan`, nobody gets anything and the
post looks like it worked.

```
GET   /api/v1/automation/settings
PATCH /api/v1/automation/settings  {"dm_trigger_keywords": "plan, guide"}
```

Then **rehearse it**, because Meta allows exactly one private reply per comment
— there is no way to test on a real comment and then fix the wording:

```
POST /api/v1/automation/dm-preview
{"comment": "<the exact CTA word>", "username": "test"}
→ would_send must be true, and `message` is what a real person will receive
```

Read that message out loud in your report. If it still says `{link}` or points at
a dead URL, fix it now — after the post goes out it is too late for everyone who
already commented.

## Stage 8 — Report

Short. What went out, where, with which goal and which trigger word. Then the
one thing you'd change tomorrow, from Stage 1's numbers rather than from taste.

If any stage was skipped, name it and why. **"Everything worked" when something
didn't is the only unforgivable output here.**

---

## What this does not do

State these when they come up rather than letting the user assume:

- **No auto-posting to TikTok, YouTube, X or LinkedIn.** Not wired up.
  Higgsfield has its own TikTok publisher (`mcp__HIGGSFIELD__tiktok_publish`) —
  that's a separate path, outside the app, and it won't appear in the app's
  attribution.
- **No reading of Meta's auto-captions.** No API exposes them.
- **No organic competitor analytics.** Private, for everyone.
- **Posting is not scheduling to the best time.** The app publishes when told.

## After this

`/pipeline` works the leads this post brings in. Run it later the same day, not
immediately — the comments need time to arrive.
