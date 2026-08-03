---
name: verify
description: Check whether a claim, platform change, tool or viral post is actually true before acting on it. Use when the user shares a reel, article, or claim and wants to know if it's real, or asks what something actually costs or allows.
---

# Verify

Check a claim against the primary source before anyone builds on it.

## Run it

1. **Is it true?** Check the platform's own documentation — developers.facebook.com,
   docs.threads.com, the vendor's pricing page. Not a blog post summarising them,
   not another creator's video.
2. **If it's a tool or API:** what does it actually cost, what are the rate
   limits, and does access require approval? These three are where marketing
   claims and reality most often diverge.
3. **If the claim is overstated, write the honest version.** Usually there's a
   real, smaller, genuinely useful thing underneath the exaggeration — find it.
4. **Should the user care?** Yes or no, then one sentence of why.

## Claims that come up repeatedly, already checked

These have been verified against primary sources. Re-check if a while has
passed, but don't re-litigate them from scratch:

- **"AI can reveal a competitor's best-performing campaigns from a link"** —
  false. That data is private. The real version is the Meta Ad Library, which is
  public, free, and shows every ad currently running.
- **X / Twitter API** — no free tier for new developers since 2026-02-06.
  Pay-per-use, roughly $0.015 per post and $0.20 with a link.
- **Threads** — has `/keyword_search`, publishing, and a 500-character cap. Has
  **no DM API** and **no Stories**.
- **Quora** — has never published a public API.
- **Reddit** — free tier reads at 100 queries/minute; *writing* needs manual
  OAuth approval, self-serve signup is closed, and the free tier is
  non-commercial.
- **Instagram private replies** (comment → DM) — real and supported. 7-day
  window, exactly one reply per comment, ever.

## Rule

If only secondhand sources can be found, say the claim is **unverified** rather
than repeating it. "I couldn't confirm this from the platform's own docs" is a
complete and useful answer.
