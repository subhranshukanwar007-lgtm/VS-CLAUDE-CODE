# Your Cowork team

The app runs the machine: generate, approve, publish, capture, score, follow up.
It does the same thing well every day and never gets tired.

What it can't do is *change its mind*. It won't notice a competitor's new angle,
won't tell you a hook has gone stale, won't push back when you're about to post
something that damages trust. That's what this file is for.

Paste **The brief** below into Cowork once. Then use the routines — each is a
prompt you can paste as-is.

---

## The brief

> Copy everything in this block into your Cowork project instructions.

```
I'm a health and fitness creator building an online coaching business from India.
My audience is mostly Indian, aged 22-40, on Instagram. They read Hinglish
(Hindi in Roman script) more comfortably than formal English.

I sell online coaching: 12-week transformation programmes, nutrition plans, and
1:1 premium coaching, priced ₹5,000-₹50,000.

I run a system called Social Media AI OS (repo: VS-CLAUDE-CODE, branch
claude/ai-social-media-os-5yb5rf). It handles automatically: generating video
with my AI avatar via Higgsfield, publishing to Instagram/Facebook/Threads,
turning comments into CRM leads, scoring their buying intent, and alerting me
when someone is ready to talk.

So do NOT help me with things the system already does. Help me with the things
it can't:

1. RESEARCH — what competitors are running, what's changed on the platforms,
   what's actually working right now in my niche.
2. JUDGEMENT — is this hook good, is this claim safe to make, is this offer
   priced right.
3. REVIEW — look at what I published and tell me what to stop doing.

How I want you to work with me:

- Lead with the recommendation, then the reasoning. I don't want a list of
  options with no opinion.
- Tell me when I'm wrong. If a plan of mine is bad, say so in the first line.
- Never invent a statistic, study, or health claim. If a number would make a
  line stronger, rewrite the line without the number. This matters more than
  anything else here — see Trust rules below.
- Write copy in Hinglish (Roman script) unless I say otherwise.
- Be brief. I read fast and my English is not perfect. Short sentences.
```

---

## Trust rules

You asked how people come to trust you. Trust is not a tone of voice — it's a set
of things you refuse to do. These are the ones that matter in health content,
where the downside is real:

**Never claim a number you can't source.** "Studies show 80% of people..." is the
fastest way to be caught. One person quoting the actual study in your comments
undoes a month of content. If a line needs a statistic to work, the line is weak
— rewrite it.

**Never promise an outcome.** "Lose 10kg in 30 days" is both unsafe and,
depending on how it's phrased, an advertising violation in most markets. Show
what someone did; don't promise what the next person will get.

**Never use a client's result without written permission**, and never use a
before/after that isn't theirs. This is the single most common way coaches get
reported.

**Say "I don't know" on camera.** Counterintuitively it's the strongest trust
signal available to you, and almost nobody in this niche uses it.

**Don't diagnose.** "This could be a thyroid issue, go get tested" is helpful and
safe. "You have a thyroid issue" is neither.

**Correct yourself publicly when you get something wrong.** One visible
correction buys more credibility than ten confident posts.

The app enforces the mechanical half of this: AI never fabricates output, and the
content generator's prompt explicitly forbids inventing statistics or medical
claims. The judgement half is yours, and it's what the Critic routine is for.

---

## The routines

Four jobs. Each one is a prompt to paste. Run them on the cadence shown, or ask
Cowork to remind you.

### 1. Scout — every Monday

Finds what your competitors are actually doing, from public ad data rather than
guesswork.

```
Run my Monday scout.

1. Search the Meta Ad Library for active ads in India in the fitness/health
   coaching niche. Pull at least 20.
2. For each advertiser running more than one ad, tell me what they're testing —
   the different hooks, the different offers.
3. Flag any ad that has been running more than 30 days. Longevity is the only
   public signal of profitability we get; a long-running ad is a proven ad.
4. Tell me the ONE angle in there I'm not using, and why it would work for my
   audience.

Don't summarise everything. I want the three things worth acting on.
```

Why this works: an ad that's been live for two months is spending money and
staying live, which means it's making money back. That's a real signal, and it's
public. A competitor's *organic* performance is not public — anyone selling you
"AI competitor analysis" of someone's reach is selling you a guess.

### 2. Critic — before anything big

Run this on a hook, an offer, or a price change before you commit.

```
Be my critic. Here's what I'm about to publish:

[paste the hook / script / offer]

1. What's the strongest reason this fails? Give me the real one, not a soft one.
2. Is there any claim here I can't back up? Quote it back to me.
3. Would this survive someone hostile in the comments? What would they say?
4. Rewrite the weakest line.

If it's actually good, say so in one line and stop. Don't manufacture criticism.
```

The last line matters. An assistant that always finds something wrong is as
useless as one that always approves.

### 3. Editor — every Sunday

Reviews what actually happened, using your own numbers rather than impressions.

```
Weekly review.

Here's my goal performance from the app (Command Center → I'll paste it):
[paste the leads-per-goal numbers]

1. Which content goal earned the most leads per post? Not the most leads — per
   post.
2. What should I stop making?
3. What single change to next week's content would move the number most?

One recommendation, not five.
```

The app already computes leads-per-post per goal, so this routine is reading real
data, not vibes. That distinction is the whole point of having built the
attribution.

### 4. Researcher — when something changes

```
Research this properly before I act on it:

[paste the claim, the platform change, the tool, or the reel someone sent me]

1. Is it true? Check the primary source — the platform's own docs, not a blog
   post about them.
2. If it's a tool or API: what does it actually cost, and what are the limits?
3. What's the honest version of the claim, if the claim is overstated?
4. Should I care? Yes or no, then why.
```

You've already seen why this one earns its place. Of the reels you sent me, one
claimed pasting a link into Claude reveals a competitor's best-performing
campaigns. That data is private and no tool can read it. The honest version — the
Meta Ad Library — is genuinely useful, free, and public. The difference between
those two is exactly what this routine catches.

---

## What we should do better

Ranked by what would move revenue soonest, not by what's most fun to build.

**1. Fill the metrics automatically.** Your dashboard has a place for followers,
reach and views, and nothing fills it yet. Every "what's working" answer is
weaker for it. Coupler.io's Instagram Insights source is the shortest path —
connect an account and this becomes real.

**2. Turn comments into DMs.** The mechanic in every reel you sent me — "comment
PLAN and I'll DM you" — is fully supported by Meta's API as a private reply
(7-day window, one reply per comment). The model and settings are built; the
sender isn't. This is the single highest-conversion feature left, because it
catches people at the exact moment they raised their hand.

**3. Answer questions on Threads.** Threads keyword search is free and public.
Finding people asking your exact question, and replying publicly with a real
answer, is the cheapest reach available to you right now — and unlike DMs, every
reader of that thread sees you being useful.

**4. Send real emails.** Follow-ups currently create a task and an in-app alert.
Nothing leaves your machine. A lead who goes quiet stays quiet.

**5. Ad boosting with country targeting.** You want leads outside India. No code
can make your leads American — only reach can, and paid reach is the only lever
that lets you choose the country. This is where the Scout routine pays for
itself: you'll be buying attention against advertisers whose hooks you've already
studied.

---

## The division of labour

| | The app | Cowork |
|---|---|---|
| Runs on a schedule | ✅ every 30–60 seconds | on your cadence |
| Publishes, captures, scores, alerts | ✅ | — |
| Notices a competitor's new angle | — | ✅ |
| Tells you a hook has gone stale | — | ✅ |
| Pushes back on a bad idea | — | ✅ |
| Verifies a claim before you post it | — | ✅ |
| Never needs you awake | ✅ | — |

The app is the machine. Cowork is the team. Neither replaces the other, and the
part that stays yours — the actual conversation with someone about to buy — is
the part that closes.
