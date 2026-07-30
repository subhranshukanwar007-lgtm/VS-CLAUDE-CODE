---
name: script
description: Write a shoot-ready content package - viral hook options, a timed script, the Higgsfield prompt, B-roll directions and on-screen captions. Use when the user asks for a script, a video idea, today's content, or what to post.
---

# Script

One topic in, a package that can be shot today out.

## What the creator already has

They have trained their own avatar and cloned voice inside Higgsfield. So the job
here is everything *around* the generation — the hook, the script, the shot list,
the captions. Not the face, not the voice.

## Build the package

**Hooks — three options, strongest first.**
Name a *specific situation*, not a condition. "Back pain" is a topic. "The back
pain from sitting nine hours at a desk" is someone's Tuesday. The second stops the
scroll because they recognise themselves in it.

**Script — timed beats.** Each beat carries three different things:

| | |
|---|---|
| `spoken` | What the avatar says. Speech, not prose: contractions, short sentences, no bullet points, no emoji |
| `caption` | On-screen text. 3–7 words, punchy. **Not a transcript** of the spoken line |
| `broll` | A concrete shot. "Close-up of oats being poured into a bowl", never "healthy food imagery" |

Beats run from 0 to the target duration with no gaps. **The first beat is the
hook and is at most 3 seconds** — the first two seconds decide whether anyone
watches at all.

**Higgsfield prompt.** Framing, camera movement, lighting, pacing, delivery
energy. **Never describe the person** — no face, age, hair, body or clothing. The
creator's trained avatar supplies all of that, and a prompt that also describes a
person fights it.

**Then:** overall B-roll notes, the post caption, one CTA, and 5–8 hashtags.

## Language

Default to the user's `reply_language` setting. For this creator that's usually
**Hinglish in Roman script** — Hindi mixed with English, written in Latin
characters, the way people actually text. Never Devanagari unless asked.

## Hard rules

- **One idea per video.** Don't cram.
- **Never invent a statistic, study or medical claim.** If a number would make a
  line stronger, rewrite the line without the number. This is not a style
  preference — being caught inventing one costs more credibility than a month of
  posting earns.
- **Never promise an outcome.** Show what someone did; don't promise what the
  next person gets.
- Everything must be usable as written. No placeholders, no "insert your hook
  here".

## In the app

`POST /api/v1/video/script-package` does this end to end and saves the result.
This skill is the same job done conversationally, when the user wants to iterate
before committing.
