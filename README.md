# Subah (صبح)

> An AI-powered daily news briefing for Pakistan · Generative AI course project
> Group: Rana Ahmad Hassan (23L-3048), M. Sameer Mufti (23i-3061)

**🌐 Live website: [https://ranaahmad3048-subah.hf.space](https://ranaahmad3048-subah.hf.space)**

Quick links: [Today's paper](https://ranaahmad3048-subah.hf.space/paper.html) · [Make my paper](https://ranaahmad3048-subah.hf.space/onboard.html) · [For family (gift by email)](https://ranaahmad3048-subah.hf.space/gift.html) · [Pricing](https://ranaahmad3048-subah.hf.space/pricing.html) · [Log in / Sign up](https://ranaahmad3048-subah.hf.space/account.html) · [Our sources](https://ranaahmad3048-subah.hf.space/sources.html)

## What it does

A morning paper for one reader: the day's top ten stories, grouped across Pakistani and world newsrooms, each labelled with how many outlets reported it and linking every report, in English, Urdu or Roman Urdu, in large print if wanted. Then it ends.

## Problem and user

People in Pakistan, and their families abroad, see the same story many times across apps and WhatsApp groups and cannot tell how widely it was reported or where it came from. Subah is for a reader who wants the news in a few minutes, and for a son or daughter abroad setting up a large-print Urdu paper for a parent at home.

## Live deployment

- **URL / install link:** https://ranaahmad3048-subah.hf.space (Space page: https://huggingface.co/spaces/RanaAhmad3048/subah)
- **Platform:** Hugging Face Spaces, Gradio SDK on free ZeroGPU hardware. The site and API are served at the root by our FastAPI app; a small Gradio page at `/gradio` exists only for the Space's hardware check (`server/space_app.py`). The app never uses the GPU.

## Quick start (under 5 minutes)

1. Open the live URL. Scroll the front page: the clustering scene and "Then we pick ten" show how grouping and ranking work.
2. Click **Make my paper**, choose **Test reader A**, then **Next: topics**, then **Generate today's paper**.
3. On the paper: each story shows **Reported by N outlets**, its sources with links, **For you** tags with the word that matched, and why it is here. Switch to **اردو**, **Roman** (Roman Urdu) and **large print** in the top bar. **Generate today's paper now** rebuilds it.
4. Open **Our sources** to see the outlet list and the ranking formula, and **Finish today's paper** for the last page.
5. Open **Pricing**, choose **Plus** and sign up with a test email. Checkout is a prototype: nothing is charged. Then on **For family**, enter a recipient email you own and **Send their paper**, or **Preview the email** without sending.

## Test accounts

Reading the paper needs no account. Use the built-in test readers on the setup page:

| Role | Setting | Notes |
|------|---------|-------|
| Test reader A | Lahore; prices, weather and smog; English | |
| Test reader B | Karachi; money and economy, jobs and tech; Urdu | |
| Test reader C | Rawalpindi; health, cricket; Urdu; large print | |

Test profiles only. Settings stay in the browser.

To try plans and gift emails, sign up on **Log in > Sign up** with a test name and an email you own. Plans: **Basic $3 a month** (3 gift emails a month) and **Plus $8 a month** (30 gift emails a month, 15 stories to pick from, a personal note on gifts). Checkout activates a plan for 30 days without taking a payment.

## Run locally

### Prerequisites

Python 3.11 or later. About 1.5 GB of free disk for the grouping model, downloaded on first run.

### Setup

```bash
python -m venv .venv
.venv/Scripts/activate      # Windows; on macOS or Linux: source .venv/bin/activate
pip install -r server/requirements.txt
cp .env.example .env        # then add your API key if you have one
```

### Environment variables

`GROQ_API_KEY` (optional: without it, stories show source headlines with links; get one at console.groq.com), `SUBAH_SOURCE` (`live`, `snapshot` or `fixtures`), `SUBAH_AI_BATCH`, `SUBAH_MAX_AI_CALLS`, `SUBAH_MODEL`, `SUBAH_AI`, `MONGODB_URI` and `SUBAH_DB` (accounts; without them accounts live in memory), `GMAIL_USER` and `GMAIL_APP_PASSWORD` (gift emails; a Google app password, not the account password), `SUBAH_SITE_URL`, `SUBAH_SCHEDULE`, `SUBAH_PRINT_AT`, `SUBAH_SEND_AT` (morning run). See `.env.example`.

### Run

```bash
uvicorn server.app:app --port 8000
```

Open http://localhost:8000. Without a server, the pages in `web/` still open from disk using the bundled sample paper.

Useful tools: `python -m server.tools.check_feeds` checks every feed; `python -m server.tools.export_static` refreshes the bundled sample files.

### Evaluation sheets

`python -m server.tools.evaluate` builds the sheets for the proposal's evaluation and scores them once people fill them in: 200 article pairs for grouping precision and recall (`eval/pairs.csv`, labelled by hand), and the summary audit with native-speaker ratings (`eval/audit.csv`, one row per AI summary; add each day's paper with `audit-add`). See the tool's help for the steps.

### Run tests

```bash
bash scripts/test.sh
```

91 tests. See [docs/testing.md](docs/testing.md) and [docs/evaluation-checks.md](docs/evaluation-checks.md).

## Deploy (free, Hugging Face Spaces)

One-time setup, about 10 minutes:

1. Create a free account at huggingface.co, then **New Space**: name `subah`, SDK **Gradio**, template **Blank**, hardware **ZeroGPU (Free)** (free accounts cannot choose CPU basic for new Spaces, and Docker Spaces need PRO), visibility **Public**.
2. In the Space: **Settings > Variables and secrets > New secret**, add `GROQ_API_KEY`, `MONGODB_URI`, `GMAIL_USER` and `GMAIL_APP_PASSWORD`. They live only there. In MongoDB Atlas, **Network Access** must allow `0.0.0.0/0`, because the Space has no fixed address.
3. In your Hugging Face account: **Settings > Access Tokens > Create new token**, type **Write**. Copy it.
4. Deploy, either way:
   - **From your computer:** `HF_TOKEN=<token> HF_SPACE=<your-username>/subah bash scripts/deploy_space.sh`
   - **Automatically from GitHub:** in this repository, **Settings > Secrets and variables > Actions**: add the secret `HF_TOKEN` and the variable `HF_SPACE` = `<your-username>/subah`. Every push to `main` then deploys (`.github/workflows/deploy.yml`); you can also run it from the Actions tab.

The first start takes a few minutes (it installs packages and downloads the 1.1 GB grouping model). After a restart or a long idle, the first paper takes up to a minute while the model loads; open the site a few minutes before a demo.

## Known limitations

- **Content licensing:** Subah shows headlines, short feed descriptions and links, with credit, and never copies articles. Licences with publishers are not yet agreed; that must happen before a public launch.
- **Data sources:** the app can run on live feeds, a saved snapshot or the bundled synthetic fixtures (`SUBAH_SOURCE`).
- Grouping was tuned on one real day of feeds and a fixed test set; ongoing stories can collect several related developments into one group.
- AI summaries use Groq (`openai/gpt-oss-120b`) on the free tier. On a real day 9 of 10 stories passed the source check in 2 calls; the free tier has per-minute token limits, so very fast repeated generations may fall back to headlines until the minute resets.
- Urdu and Roman Urdu AI output still needs review by an Urdu speaker. A story the AI wrote no Roman Urdu for is shown in English, with a note.
- Payments are a prototype: choosing a plan activates it without charging. A payment provider (for example Stripe) is needed before launch.
- Gift emails and morning emails go out from one Gmail account, which Google limits to about 500 messages a day; the morning run stops at 400.
- The morning run lives inside the web server: a free Hugging Face Space that has gone to sleep prints and sends nothing until someone opens it (it catches up until 11:00).
- Scope note: the first MVP left out payments; plans and gift emails were added later.

## Proposal vs. build

How each item in the project proposal ended up. "Changed in MVP scope" means we cut or changed it when we fixed the MVP scope, for the reason given. The full list is in [docs/requirements.md](docs/requirements.md).

| Proposal item | Status | Where |
|---|---|---|
| Overnight ingestion of 20 to 30 outlets | Built: 20 outlets with working feeds (25 feeds; 3 more outlets listed but paused), newest 60 items per feed; article text is not fetched (feed metadata only, for licensing) | `server/outlets.json`, `/sources.html` |
| Multilingual embeddings and clustering across English and Urdu | Built | `embed.py`, `group.py` |
| Ranking by outlets, recency and topic balance | Built: outlets plus the reader's city and topics; recency breaks ties; no section over 3 of 10 | `rank.py`, `/sources.html` |
| Grounded summaries with sources | Built; sources are linked for each story, not for each claim | `summarize.py`, `grounding.py` |
| "Why it matters" and "what is not yet known" | Changed in MVP scope: removed, because feed descriptions are too short to say what is unknown without the model guessing | |
| Confirmed / Single source / Unconfirmed badges, reliability tiers | Changed in MVP scope: replaced by "Reported by N outlets", a count rather than a verdict | `group.py`, `/sources.html` |
| Factuality check (second LLM pass or entailment model) | Built as a deterministic code check on numbers and names, with one retry | `grounding.py` |
| "For you" line and fuel-price table | Rule-based "For you" tags showing the matched word; no price table (scope decision: no AI predictions about a reader's costs) | `tags.py` |
| English, Urdu and Roman Urdu; large print | Built | Paper page language switch |
| Delivery by web, and WhatsApp or email at 7 am | Built for email: the paper is printed at 06:30 and emailed at 07:00 (Lahore time) to readers who turn on "Email me my paper" on their account; gift papers by email. No WhatsApp yet | `scheduler.py`, `mailer.py`, `/account.html` |
| "You're done for today" | Built | `/end.html` |
| Phase 2: audio | Built with the browser's own voices | Paper page, Listen |
| Phase 2: gift papers | Built: $3 and $8 plans (prototype checkout, no payment) and gift email | `/pricing.html`, `/gift.html` |
| Phase 2: three takeaways and a quiz | Partly: the last page repeats the top three; no quiz | `/end.html` |
| Phase 2: team briefs | Not built | |
| Evaluation: 200 hand-labelled pairs, 100-summary audit, native-speaker rating, 30 to 50-user pilot | Tooling built, labelling to do: `server/tools/evaluate.py` made a 200-pair sheet from the real feeds (`eval/pairs.csv`) and the summary audit sheet (`eval/audit.csv`, 7 of 100 so far); both need people to fill them in. Also 528 labelled pairs on the synthetic fixed set. Pilot not yet run | [docs/testing.md](docs/testing.md), `eval/` |

## Documentation

- [Requirements](docs/requirements.md)
- [Design](docs/design.md)
- [Testing](docs/testing.md)
- [AI usage log](docs/ai-usage-log.md)
- [Evaluation checks](docs/evaluation-checks.md)

## Group members

| Name | Roll number |
|------|-------------|
| Rana Ahmad Hassan | 23L-3048 |
| M. Sameer Mufti | 23i-3061 |
