# Start here — the whole process, step by step

This is the operating manual for your system. Follow it in order. Steps marked
**[you]** need you; steps marked **[automatic]** happen on their own once set up.

Rough timings: Part 1 takes about 15 minutes, Part 2 about 30 minutes on
Higgsfield's site, Part 3 about an hour of form-filling in Meta's dashboard.
Parts 1 and 2 work without Part 3.

---

## Part 1 — Get it running on your computer

### Step 1 [you] — Install the two things you need

- **Docker Desktop** — https://www.docker.com/products/docker-desktop
- **VS Code** — https://code.visualstudio.com

Start Docker Desktop and wait until it says "running".

### Step 2 [you] — Download the code

Open a terminal and paste this, one block:

```bash
git clone https://github.com/subhranshukanwar007-lgtm/VS-CLAUDE-CODE.git
cd VS-CLAUDE-CODE
git checkout claude/ai-social-media-os-5yb5rf
code .
```

### Step 3 [you] — Create your settings file

```bash
cp apps/api/.env.example apps/api/.env
```

Open `apps/api/.env` in VS Code. Change one line to any long random text:

```
SECRET_KEY=type-any-long-random-text-here-at-least-32-characters
```

> Keep this value. If you change it later, every connected social account has to
> be reconnected — access tokens are encrypted with a key derived from it.

### Step 4 [you] — Start it

```bash
docker compose up --build
```

First run takes about 5 minutes. Leave this terminal open — closing it stops the app.

### Step 5 [you] — Create your account

1. Open **http://localhost:3000**
2. Click **Register**, enter your name, email, password
3. You land on the **Command Center**

You now have a working app. Everything below adds power to it.

### Later: getting my updates

```bash
# Ctrl+C in the terminal to stop, then:
git pull origin claude/ai-social-media-os-5yb5rf
docker compose up --build
```

Your account, leads, and posts survive. Your `.env` is never touched.

---

## Part 2 — Your AI avatar and voice (Higgsfield)

### Step 6 [you] — Buy and set up Higgsfield

On https://cloud.higgsfield.ai:

1. Buy a subscription
2. Upload your photo → create your **avatar**
3. Record a voice sample → create your **voice clone**
4. Go to the API section → copy your **API key** and **API secret**

### Step 7 [you] — Paste the keys in

In `apps/api/.env`:

```
HIGGSFIELD_API_KEY=paste-your-key
HIGGSFIELD_API_SECRET=paste-your-secret
```

Also paste at least one AI provider key, for captions and lead analysis:

```
OPENAI_API_KEY=sk-...
```

Restart: `Ctrl+C`, then `docker compose up`.

> Honest note on avatar/voice: Higgsfield's public docs confirm the base URL,
> the auth scheme, and the model line. They do **not** document the exact field
> names for pointing a generation at *your specific* trained avatar and voice.
> The app passes those through an **Extra params** box on the Video page — once
> you can see the field names in your own Higgsfield dashboard, put them there.
> I flagged this rather than guessing field names that would silently fail.

### Step 8 [you] — Make your first video

1. **Video** in the sidebar
2. Type what the video should show
3. Pick **Higgsfield**
4. Tap **Generate** — one tap, that's it

### Step 9 [automatic] — It finishes by itself

The app checks every 30 seconds and the video appears when ready (usually
30 seconds to a few minutes). No refreshing.

If a key is missing or Higgsfield errors, you get a clear red message with the
real reason. **You will never see a fake video.**

### Step 10 [you] — Turn it into a post

1. Tap **Generate thumbnail** (optional)
2. Tap **Create post from this video**
3. Add your caption and CTA — "comment PLAN for my program"
4. Save it

It's now a draft in your **Content Calendar**.

---

## Part 3 — Connect Instagram, Facebook and Threads

This is what makes posting and lead capture automatic. It's free, but it's the
most tedious part: Meta's dashboard is a lot of forms.

### Step 11 [you] — Create a Meta app

1. Go to https://developers.facebook.com → **My Apps** → **Create App**
2. You need an **Instagram Business or Creator** account (not a personal one)
3. Link it to a **Facebook Page**
4. For Threads: link your Instagram Business account to your Threads profile

### Step 12 [you] — Set up the webhook

In your Meta app → **Products** → **Webhooks**:

- Subscribe to your Page / Instagram account's **`comments`** field
- Callback URL: `https://your-public-domain.com/api/v1/webhooks/meta`
- Invent any string as the verify token

> **`localhost` will not work here.** Meta has to reach your server from the
> internet. For testing, use a tunnel like `ngrok http 8000` and paste the
> `https://` URL it gives you.

Then in `apps/api/.env`:

```
META_APP_SECRET=from-your-app-dashboard
META_WEBHOOK_VERIFY_TOKEN=the-string-you-invented
```

### Step 13 [you] — Register your account in the app

**Settings** → **Connected accounts** → add your Instagram Business Account ID.

### Step 14 [you] — Choose your automation settings

All in **Settings**, all editable in the browser, no code:

| Setting | What it does |
|---|---|
| **Auto-publish** (per platform) | Off = you approve each post. On = posts go out alone |
| **Auto-DM message** | What gets sent when someone comments your keyword |
| **Trigger keywords** | e.g. `PLAN, GUIDE, START` |
| **Threads keywords** | Topics to watch for people asking questions |
| **Reply language** | English, **Hinglish (Roman script)**, or Hindi |
| **Follow-up days** | How long a quiet lead waits before being chased |
| **Posts per day** | Your cadence |

**Auto-publish starts OFF for every platform, on purpose.** A brand-new account
posting AI video unattended every day is how accounts get restricted. Approve
manually for the first week or two, then turn it on once you trust the output.

---

## Part 4 — The loop, once it's all connected

This is what runs without you.

### Step 15 [automatic] — Your post goes out

Every 60 seconds the app checks for posts that are due.

- Auto-publish **on** → publishes to Instagram / Facebook / Threads for real
- Auto-publish **off** → the post moves to your Command Center as
  "Waiting for your approval". You tap **Approve** and it goes out.

### Step 16 [automatic] — Comments become leads

Someone comments on your post → Meta notifies your app → they appear in your
CRM as a lead, tagged `engagement`.

Repeat commenters are matched to their existing lead, so you get one contact
with a history, not five duplicates.

### Step 17 [automatic] — Buying intent gets scored, instantly

Every comment is read and scored:

| Score | What it means |
|---|---|
| 🔥 **HOT** | Asked the price, how to join, availability, or for a link |
| **WARM** | Asked a real question about your topic |
| **COLD** | A compliment or an emoji |

Hinglish counts — *"bhai kitna hai ye"* scores HOT, same as *"what's the price"*.

### Step 18 [automatic] — You get told when to talk

The moment someone turns HOT: **🔥 Priya is ready to talk** — with the reason
they were flagged. They go to the top of your Command Center.

Three things worth knowing about how this behaves:

- You're alerted **once** per person, not every time they comment again
- A score is **never lowered** — someone who asked the price last week stays hot
  even if their newest comment is just 🔥
- Someone who has said nothing is left **unscored**, not marked cold

### Step 19 [you] — Have the conversation

This part stays human, on purpose. Automated closing reads as spam and doesn't
convert. Open the lead, see what they asked, reply yourself.

The **Sales** agent can help — it reads your actual hot leads by name and
suggests what to say.

### Step 20 [automatic] — Quiet leads get chased

Once a day, any lead with no activity for N days (your setting, default 5) gets
an AI-drafted follow-up message plus a reminder task. You approve and send.

---

## Your screens

| Screen | What it's for |
|---|---|
| **Command Center** | Start here daily. Who to talk to, what to approve, the money |
| **Analytics** | Followers, views, revenue, best/worst posts, 30-day projection |
| **CRM** | All leads + drag-and-drop pipeline. Filter by intent, country, platform |
| **Content Calendar** | Write and schedule. Approve drafts |
| **AI Content Studio** | Captions, hashtags, scripts |
| **AI Video Studio** | Generate with your avatar → thumbnail → post |
| **AI Agents** | Six specialists (four read your real data) |
| **Settings** | Everything you edit. One page |

### Your six agents

| Agent | Reads your real data? |
|---|---|
| **Content** — hooks, scripts, captions | no |
| **CRM** — pipeline, follow-ups | ✅ yes |
| **Sales** — closing DMs, objections | ✅ yes, your actual hot leads by name |
| **Analytics** — what's working | ✅ yes |
| **Money** — revenue, pricing, is a spend worth it | ✅ yes |
| **Support** — DM and comment replies | no |

Trimmed from twelve. The other six (CEO, Marketing, Designer, Editor, Research,
Trend) were job titles from the original spec that a solo operator never opens,
and the long list buried the useful ones.

---

## What this system does NOT do

Read this so nothing surprises you later.

| Not built | Why |
|---|---|
| **X / Twitter posting** | X removed its free API tier for new developers on 6 Feb 2026. Now ~$0.015 per post, $0.20 with a link. You chose to skip it — the code is structured so adding it later is one file |
| **Threads DMs** | **Threads has no DM API.** Not restricted — it doesn't exist. Same for TikTok and YouTube |
| **Quora** | **No public API has ever existed.** Only scraping, which breaks their terms |
| **Reddit replies** | Searching is free. *Posting* needs Reddit's manual approval — self-serve signup is closed, 2–4 week wait, and the free tier is non-commercial |
| **Sending real emails** | Follow-ups create a task and an in-app notification. No email leaves your machine yet — that needs an email provider wired in |
| **Finding strangers to contact** | Deliberate. People who commented on your video convert far better than strangers, and cold outreach burns your domain |
| **Auto-detecting a lead's country** | Meta's comment webhook doesn't include it. Set it manually, or from your ad targeting. I won't fake a value |
| **YouTube / LinkedIn / TikTok / Pinterest posting** | Each needs its own OAuth and API approval |
| **Video analysis** (transcription, scene detection, virality scoring) | Needs GPU infrastructure or paid inference APIs |

Nothing in this app fakes a result. If a key is missing or a platform rejects
something, you get the real error message — never a fabricated success.

---

## Growing worldwide

You asked about USA and other countries. Be clear-eyed: **no code can make your
leads American.** Which country they come from is decided by who sees your
content, and Meta shows your content to people like your current audience.

Two things actually move this:

1. **Paid boosting with country targeting** — the real lever. Meta ads let you
   target USA/UK/Canada/Australia specifically. This is the "boost" step.
2. **Tracking country per lead** — built. Filter your CRM by country and see the
   breakdown on your Command Center, so you can measure whether the boosting
   is working.

---

## When something breaks

| Problem | Fix |
|---|---|
| Video generation returns 503 | `HIGGSFIELD_API_KEY` / `HIGGSFIELD_API_SECRET` missing from `.env`, or subscription expired |
| Captions return 503 | No AI provider key set. Add `OPENAI_API_KEY` |
| "No connected Instagram account" | Add your account in Settings → Connected accounts |
| "No usable access token — reconnect" | Token expired, or `SECRET_KEY` changed. Reconnect the account |
| Instagram rejects a post | The message is Meta's own words. Usually the media URL isn't publicly reachable |
| No comments arriving | Callback URL must be public HTTPS. `localhost` can't work — use `ngrok` |
| Threads post rejected | 500-character limit, hashtags included |
| Docker: "no space left on device" | `docker system prune -a` |

---

## Your daily routine, once it's running

1. Open **Command Center**
2. Talk to anyone marked 🔥 — they asked to buy
3. Approve the drafts waiting
4. Generate tomorrow's video in **Video Studio** (one tap)
5. Close it

Ten minutes a day. Everything else runs on its own.
