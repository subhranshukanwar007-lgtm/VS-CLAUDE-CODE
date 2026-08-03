---
name: pipeline
description: Work the leads the content brought in - score them, prepare the calls, draft the follow-ups, and source outbound B2B leads from Apollo. Use when the user asks to work the pipeline, handle leads, prepare follow-ups, do the outreach, or find new leads.
---

# Pipeline

`/daily-run` puts content out. This picks up what comes back.

Order matters and it is not negotiable: **inbound before outbound.** Someone who
commented on a reel an hour ago is worth more than a hundred names from a
database, and they go cold in a day. Never start with Apollo while hot leads sit
unanswered.

## Before you start

Access token from `POST {API}/api/v1/auth/login`. Credentials come from the user
or their environment — never into a file, a commit, or a message.

---

## Stage 1 — The people already raising their hand

```
GET /api/v1/dashboard/command-center
GET /api/v1/leads?intent=hot
GET /api/v1/automation/dm-queue/summary
```

**Check the DM queue first.** If `failed` is above zero, the auto-DM is broken
and every person who commented today got nothing. That outranks everything else
in this skill. `GET /api/v1/automation/dm-queue?status=failed` carries Meta's own
error text — read it, fix the cause, then
`POST /api/v1/automation/dm-queue/{id}/retry`.

Common causes, in order of likelihood: the token expired, the account is missing
`instagram_manage_messages`, or the 7-day window closed. The first two are
fixable and the third is not — say which.

**Then the hot leads.** HOT means the AI found a real buying signal in their own
words: they asked the price, asked how to join, asked about availability. That is
the moment a human conversation is worth having, and it decays in hours.

If a lead's intent looks stale, `POST /api/v1/leads/{id}/score-intent` re-reads
their messages.

## Stage 2 — Prepare the calls

**There is no dialer in this system and nothing here places a call.** No voice
provider is connected — no Twilio, no Exotel, no Bland, no Vapi. Anything
claiming a call was made would be a lie. Say this plainly if the user expects
otherwise; adding one is a real, separate piece of work with its own cost and its
own consent rules.

What this stage genuinely does: hand the user a ready call, so the only thing
left is pressing dial.

For each hot lead, create a task:

```
POST /api/v1/tasks
{"title": "Call <name> — asked about pricing", "lead_id": ..., "due_date": today}
```

And in the task description put a brief they can read on the phone:

- **What they actually said**, quoted. Not a summary — their words.
- **Which post they came from**, if `source_post_id` is set. "You commented on
  the desk-posture reel" opens a conversation that "hi, saw your comment" doesn't.
- **The one question to open with.** A question, not a pitch.
- **The price to name**, from their coaching tiers. Naming it late reads as
  hedging.

Keep it under a screen. A brief nobody reads is a brief that didn't exist.

## Stage 3 — Follow up the ones who went quiet

```
POST /api/v1/leads/{id}/follow-up
```

Drafts a follow-up in their language and files it as a task. A daily Celery beat
already does this for leads gone stale past `follow_up_days`; run it by hand when
the user wants a specific person chased now.

**Drafts, never sends.** The message goes out from the user's own account, in
their own hands. This is deliberate: an automated message to someone who was
mid-conversation is the fastest way to lose them.

The exception is WhatsApp, where the assistant already replies inside the free
24-hour window and hands off the moment someone asks to buy.

## Stage 4 — Outbound (Apollo)

Read this before running it, because the mismatch is the whole point.

**Apollo is a B2B database.** It searches by job title, company, industry,
headcount. It cannot find "a 28-year-old in Pune who wants to lose 10kg" — that
person has no company record, and consumers aren't in it.

So Apollo is useful for exactly one thing here, and it is not the Instagram
audience:

| Works | Doesn't |
|---|---|
| Gym and studio owners (partnerships, referral deals) | Individual coaching clients |
| Corporate HR / people ops (corporate wellness programmes) | Anyone who found them through a reel |
| Other coaches (collaborations, licensing) | Their actual ₹5K–₹50K buyer |

Corporate wellness is genuinely worth having — one HR contract is worth many
individual clients, and it's a different product from the coaching they sell on
Instagram. **Treat it as a second business line and say so.** If the user
expected Apollo to find Instagram-type buyers, tell them it can't before spending
their credits.

If they want it:

1. `mcp__Apollo_io__apollo_mixed_people_api_search` — filter by title and
   geography. Start with **one** narrow search, not a broad one; a wide search
   burns credits and returns noise.
2. Show the user the list **before** importing anything.
3. Import the ones they approve:
   ```
   POST /api/v1/leads
   {"full_name": ..., "email": ..., "country": "IN", "source": "outbound",
    "tags": "apollo, corporate-wellness"}
   ```
   `source: "outbound"` matters. It keeps these out of the unattributed-lead
   count, so the number that says "your post attribution is broken" stays honest.

### On cold email

Apollo can send sequences (`apollo_emailer_*`). Before touching it:

- It needs a **connected mailbox**, and sending cold volume from their main
  domain can damage deliverability for their real mail. A separate sending domain
  is the standard answer.
- **GDPR applies to EU contacts** — the user wants worldwide, so this is not
  hypothetical. India has no equivalent enforcement; the EU does.
- A generic sequence to a bought list performs badly and burns the domain. If
  the user wants outbound email, fewer and personal beats more and templated.

Do not start a sequence without the user explicitly asking for that specific
sequence. Ask, then send.

---

## Stage 5 — Report

- DM queue: sent / failed today, and whether anything is broken **right now**
- Hot leads: how many, and how many now have a call task
- Follow-ups drafted, waiting for them to send
- Outbound: how many imported, from which search, and what it cost

Then one line: **what to do first.** Not a list — the single next action.

---

## What this does not do

- **No calls placed.** No voice provider is connected.
- **No messages sent on the user's behalf**, except the WhatsApp assistant's
  replies inside the free window and the comment auto-DM they configured.
- **No consumer lead sourcing.** Apollo is B2B; consumers aren't in it, and no
  legitimate database has them.
- **No lead scraping from Instagram followers.** Meta's API doesn't expose them
  and scraping them risks the account they're building.
