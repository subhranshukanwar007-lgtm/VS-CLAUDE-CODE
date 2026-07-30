---
name: review
description: Weekly performance review from the app's own numbers - which content goal produced leads, what to stop making, and the one change for next week. Use when the user asks for a weekly review, asks what's working, or wants to know what to change.
---

# Review

Read what actually happened, from real data rather than impressions.

## Get the numbers

Ask the user to paste their goal performance from Command Center, or if the API
is reachable locally, `GET /api/v1/goals/performance`.

The key figures are per content goal (reach / leads / sales / trust / saves):
`leads_per_post`, `hot_leads`, `won_value`, and `unattributed_leads`.

## Read them correctly

- **Rank by `leads_per_post`, never by raw `leads`.** Otherwise whichever goal
  they posted most often always looks like the winner, which is a measurement
  artefact rather than an insight.
- **`unattributed_leads`** are leads with no source post — DMs, manual entries,
  or posts published outside the app. A high number here means the attribution
  picture is incomplete, and the per-goal numbers should be read with that in
  mind rather than treated as the whole story.
- **A goal with zero published posts tells you nothing.** Don't call it a
  failure; it's untested.

## Report

1. Which goal earned the most leads per post.
2. What to **stop** making. Be specific and name it.
3. The single change to next week's content that would move the number most.

One recommendation, not five. If the data is too thin to conclude anything, say
that plainly — "you have four published posts, that's not enough to tell" is a
more useful answer than a confident pattern read from noise.
