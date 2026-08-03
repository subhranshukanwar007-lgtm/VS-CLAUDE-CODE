---
name: scout
description: Research what competitors are actually advertising, from public Meta Ad Library data. Use when the user asks what competitors are doing, wants competitor research, asks for their Monday scout, or wants to know what hooks and offers are working in their niche right now.
---

# Scout

Find what competitors are genuinely running, from public ad data rather than
guesswork.

## Why this uses the Ad Library and not "AI competitor analysis"

A competitor's organic reach, engagement rate and campaign performance are
**private**. No tool can read them, and anything claiming to is guessing from
their public website.

What *is* public, by law, is every ad currently running. The Meta Ad Library
shows the creative, the advertiser, and when each ad started. That's real
intelligence, and it's free.

## Run it

1. Call `mcp__meta_ad__ads_library_search` with `ad_active_status: "ACTIVE"` and
   the user's country. Use two or three different search terms covering their
   niche — pull at least 20 ads total.
2. Group results by `page_name`. An advertiser running several ads at once is
   **testing**; note what varies between them (hook, offer, angle).
3. Compute each ad's age from `ad_delivery_start_time`. **Flag anything running
   more than 30 days.** Ad longevity is the only public signal of profitability
   available — an ad that's been live for two months is spending money and
   staying live, which means it's earning it back.
4. Read `ad_creative_link_title` for the actual hooks. Several titles separated
   by `|` in one ad means that advertiser is split-testing headlines.

## Report

Three things worth acting on. Not a summary of everything found.

For each: what they're doing, why it's working, and what the user should do
about it. Then name the **one angle they're not using** and write it as a
ready-to-use hook in their audience's language.

## Rules

- Report only what the Ad Library actually returned. If asked about a
  competitor's reach or conversion rate, say plainly that it's private and
  unknowable.
- Never invent a statistic, study or health claim.
- If the tool is unavailable or returns nothing, say so rather than guessing at
  what competitors might be doing.
