# What to build next

Ordered by **when it starts to matter**, not by a flat priority score. Building
something before its moment wastes the work; building it after costs you money
you already spent getting there.

Each item says what triggers it, what it costs, and what it's worth.

---

## Stage 0 — Before you pay for anything

**Prove the loop with content you already have.**

Higgsfield is step 1 of the chain, not the whole chain. Post a video you've
already shot, and everything downstream runs for free: publishing, comment
capture, lead creation, intent scoring, the 🔥 alert, and the follow-up
automation. The keyword layer of intent scoring needs no AI key at all — *"kitna
hai"* still fires an alert.

| | Cost |
|---|---|
| Meta APIs (publish, webhooks, comment capture) | free |
| Running the app locally in Docker | free |
| ngrok, for a public webhook URL | free tier is enough |
| Intent scoring, keyword layer | free |
| Higgsfield (AI avatar video) | subscription |
| An AI key (scripts, captions, AI intent pass) | ~$5 covers months at this volume |

**Done when:** a real comment on a real post produced a real 🔥 alert on your
phone. At that point the machine is proven and paying for the top of the funnel
is an upgrade rather than a bet.

---

## Stage 1 — The moment people start messaging you

### WhatsApp assistant — built

`app/services/whatsapp_service.py`. Someone messages your WhatsApp Business
number, they become a CRM lead, their words get scored, and the AI answers
questions in your voice and your language.

**It replies and never initiates**, because that is where the cost is: answering
inside the 24-hour window is free, and a click from a Click-to-WhatsApp ad opens
72 free hours. Only business-initiated conversations are billed.

**It stops the moment someone is ready to buy.** Ask the price or say "I want to
join" and the AI hands the conversation to you and alerts you, rather than
negotiating. Automating the close is where this kind of system starts costing
sales.

Needs `WHATSAPP_PHONE_NUMBER_ID` and `WHATSAPP_ACCESS_TOKEN`, plus a dedicated
number that is not already on the WhatsApp app.

### Comment → auto-DM (Instagram private replies) — **built**

This is the mechanic in every "AI social media" reel — *"comment PLAN and I'll
DM you"*. It catches someone at the exact second they raised their hand, which
is when they convert best. Doing it by hand is possible at 5 comments a day and
impossible at 50.

**What Meta allows** (verified against their docs, and it shapes the design):
- A private reply must be sent within **7 days** of the comment
- **One private reply per comment, ever** — Meta enforces this server-side
- If they reply, that opens a normal **24-hour window** for free conversation

**How it works.** The Meta webhook writes a `private_replies` row for *every*
comment — PENDING if it matched a trigger keyword, SKIPPED if not — and does no
network call at all. A Celery task every 30 seconds sends the PENDING ones. The
split matters: Meta retries webhooks it thinks were slow, and the unique
constraint on `comment_id` is what makes a redelivery harmless. A SKIPPED row is
a decision on the record, so turning the feature on later cannot retro-DM
someone who commented last week.

Keyword matching is word-boundary based: *plan* catches "PLAN" and "plans", not
"planet" and not the "plan" inside "explanation".

`POST /automation/dm-preview` dry-runs a comment and shows the exact message
without sending. It exists because you get one private reply per comment — there
is no way to test on a real comment and then fix the wording.

**Not built:** the Settings UI for the queue. The API is there
(`/automation/dm-queue`, `/summary`, `/{id}/retry`); nothing renders it yet.

**Needs:** `instagram_manage_messages` (Instagram) or `pages_messaging`
(Facebook) on the connected account's token.

---

## Stage 2 — The moment you want to know what's working

### Automatic metrics from Instagram Insights

**Trigger:** you've published 10+ posts and want a real answer to "what's
working".

**Why now:** the dashboard has a place for followers, reach and views, and
nothing fills it. Your goal-performance report already traces leads back to
posts, which is the harder half — but without reach numbers you can't tell
whether a post underperformed because the content was weak or because it barely
got shown.

**Shortest path:** Coupler.io's `instagram-insights` source on a schedule. You
have no Coupler.io account connected yet — connect one at
https://app.coupler.io/app/source/connections/new and the wiring is small.

**Worth:** turns "which content works" from an estimate into a measurement.

---

## Stage 3 — The moment you want reach you don't have to pay for

### Threads question inbox

**Trigger:** you want growth without an ad budget.

**Why now:** Threads' `/keyword_search` endpoint is free and public. Finding
people asking your exact question, and answering publicly with something
genuinely useful, is the cheapest reach available — and unlike a DM, everyone
reading that thread sees you being useful.

**Already built:** the `QuestionOpportunity` model, and the `threads_keywords` /
`threads_max_per_day` settings. **Missing:** the search job, the AI draft step,
and the inbox UI.

**Honest limits:**
- **Threads has no DM API.** Finding people works; messaging them does not exist.
  Public replies are the only route.
- **Reddit** would slot into the same model, but posting a comment there needs
  Reddit's manual OAuth approval — signup is closed, the wait is 2–4 weeks, and
  the free tier is non-commercial.
- **Quora has never had a public API.** The only alternative is scraping, which
  breaks their terms. A copy-to-clipboard button is the honest maximum.

---

## Stage 4 — The moment you sell outside India

Do these **in this order**. Doing them out of order means generating leads you
cannot charge.

### 4a. Take international payment — first

₹25,000 and UPI do not work for an American buyer. Deals already carry a
`currency` field so the CRM handles it, but you need Stripe or Razorpay
International to actually collect. **Sort this before spending on ads**, or
you'll pay for leads you can't convert.

### 4b. Audience targeting per post

Right now `reply_language` is one global setting, so the app cannot run Hinglish
content for India and English content for the USA side by side. Everything the
AI writes uses one language.

The fix: each post carries a target country and language, so both markets live in
one calendar and are scheduled against their own peak times. Leads captured from
a post inherit its country, which finally makes `Lead.country` fill itself
instead of being typed in.

### 4c. Boost with country targeting

Organic reach will not cross the border on its own — Meta shows your content to
people like your current audience. Paid targeting is the only lever that lets you
choose the country. Pick **one** market, not "worldwide"; broad targeting burns
budget.

**Then measure** with the leads-by-country breakdown that already exists.

**One cost worth planning for:** a second market halves your output per market
unless you double production. Your trained avatar is what makes that cheap — same
script, two languages, two videos, one afternoon. That is the strongest practical
argument for the Higgsfield subscription.

---

## Stage 5 — The moment a quiet lead is costing you money

### Real outbound email

Follow-ups currently create a task and an in-app notification. **Nothing leaves
your machine.** A lead who goes quiet stays quiet unless you happen to open the
app.

Wiring in Postmark, SES or SendGrid means adding one notification channel and
calling it from the `notify()` call sites that already exist. Straightforward —
it just isn't worth doing until you have enough leads for silence to be
expensive.

**Legal note before you send:** cold email to US business contacts is legal under
CAN-SPAM with a working opt-out. Emailing EU consumers without consent is a GDPR
problem. Emailing people who commented on your post and asked for something is
fine everywhere.

---

## Not planned, and why

Written down so nobody re-proposes them later.

| | Why not |
|---|---|
| **X / Twitter posting** | No free tier for new developers since 2026-02-06. ~$0.015/post, $0.20 with a link. The `Publisher` interface makes it one file whenever that's acceptable |
| **Threads DMs** | No DM API exists. Not restricted — absent |
| **Quora** | No public API has ever existed |
| **Reddit replies** | Manual approval, closed signup, 2–4 week wait, non-commercial free tier |
| **Apollo / cold B2B outreach** | Apollo is a B2B contact database. It cannot find consumers who want a fitness coach. Only relevant if the offer pivots to corporate wellness |
| **Competitor organic analytics** | Their reach and campaign performance are private. Nothing can read them. The Meta Ad Library is the real, public, free version — and it's genuinely useful |
| **Trend scraping** | Needs scraping (ToS risk, constant breakage) or paid API access, and it's the least valuable step — you already know your niche |
| **Video analysis** (transcription, scene detection, virality scoring) | Needs GPU infrastructure or paid inference APIs |

---

## The one-line version

Prove the loop free → add Higgsfield → auto-DM → automatic metrics → Threads
answers → international payment → second market → email.
