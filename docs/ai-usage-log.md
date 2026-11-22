# AI Usage Log

A record of every meaningful use of AI tools while building the project.

## Tools used

| Tool | Used for |
|------|----------|
| Claude Code (Claude Opus 5.5) | Front-end design and code, backend pipeline, tests, fixtures, docs |
| Groq API, model openai/gpt-oss-120b (in the product) | Writing grounded English and Urdu summaries of the selected stories |
| paraphrase-multilingual-mpnet-base-v2 (local, in the product) | Embeddings for grouping reports across English and Urdu |

## Log

| Time | Member | Tool | What it was asked | What was accepted / changed / rejected | How it was verified |
|------|--------|------|-------------------|----------------------------------------|---------------------|
| 2026-11-10 | (fill in) | Claude Code | Design and build the first UI from the idea plan and the reference site | Accepted as a starting point; later cut to the MVP scope | Viewed in the browser |
| 2026-11-10 | (fill in) | Claude Code | Apply the MVP scope decisions; build the backend | Accepted; coverage labels, rule-based tags and the mechanical ranking follow the MVP scope | 48 automated tests; live feed run read by hand |
| 2026-11-10 | (fill in) | Claude Code | Tune grouping | First setting rejected after a live run chained unrelated stories; switched to a larger model and retuned | Threshold sweep on the fixed set and on real feeds (testing.md) |
| 2026-11-10 | (fill in) | Claude Code | Write fixture feeds | Accepted; clearly marked synthetic | Used only in tests and offline demos |
| 2026-11-10 | (fill in) | Claude Code | Never show "no summary"; close source lists by default; add read-aloud | Accepted: one retry with the rejection reasons, then the outlet's own words; browser voices for audio | 2 new tests; live paper checked: 7 summaries, 3 credited quotes, no "no summary" text |
| 2026-11-10 | (fill in) | Claude Code | Add accounts, $3 and $8 plans, and gift papers by Gmail | Accepted; checkout kept as a prototype with no payment; sending through a Gmail app password | 13 new tests; sign-up, checkout and gift page checked in the browser with test accounts |
| 2026-11-10 | (fill in) | Claude Code | Fix the MongoDB connection | The first database login was rejected; a second database user worked and was set as a Space secret | Connection test; a test account written, read back and deleted; live `/api/health` reports MongoDB connected |
| 2026-11-22 | (fill in) | Claude Code | Check the build against the project proposal; add Roman Urdu and topic balance; fix doc placeholders | Accepted; Roman Urdu written by the AI in the same call and checked in code; topic cap kept mechanical and published | 10 new tests; full suite (76 passing) |

## Reflection

### Where AI helped most

Building the whole pipeline and its tests quickly, and writing synthetic English and Urdu fixtures with known answers.

### Where AI was wrong or misleading

- The first grouping threshold was tuned only on synthetic fixtures and over-merged real news. A live run caught it.
- A first Urdu keyword list included "چینی", which means both sugar and Chinese.
- An automated CSS cleanup broke a stylesheet; a browser check caught it.
- The Basic plan's feature list promised settings saved to the account before the pages used that feature; caught on review, listed as open, and later built (FR-22).
- A first script that waited for the Space to restart stopped too early, because the status text it matched also appeared in another field; checking the live health endpoint instead fixed it.

### What we did not delegate to AI

Deciding what counts as an outlet, the ranking formula, what the coverage label may claim, and whether a summary is allowed through (the grounding check is code, not a model).
