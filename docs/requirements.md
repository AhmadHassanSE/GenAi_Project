# Requirements

## Problem statement

People in Pakistan, and their families abroad, read the same story five times across apps and WhatsApp groups and still cannot tell how widely it was reported or where it came from. Feeds are built to keep them scrolling.

Subah is a morning paper for one reader: the day's top stories, grouped across Pakistani and world newsrooms, each showing how many outlets reported it and linking every report, in English or Urdu, in large print if wanted. Then it ends.

## Users

- **Reader in Pakistan** who wants the day's news in a few minutes, in English or Urdu.
- **Family member abroad** who sets up a large-print Urdu paper for a parent at home.
- **Course evaluators and demo audience**, using test reader profiles.

## Functional requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | Read the feeds on a published outlet list; use only feed metadata (headline, description, link, time) | Must | Done: 20 outlets, 25 feeds; newest 60 items kept per feed |
| FR-02 | Group reports of the same event across outlets and across English and Urdu | Must | Done (retuning on real feeds, see testing.md) |
| FR-03 | Label each story with the count of distinct outlets ("Reported by N outlets") | Must | Done |
| FR-04 | Rank stories by a published mechanical formula and keep the top ten | Must | Done; topic balance added after the first MVP (FR-24) |
| FR-05 | Summarise only the selected stories, only from their source metadata, and link every source | Must | Done |
| FR-06 | Check every summary against its sources in code; drop it on any unsupported number or name | Must | Done |
| FR-07 | Show the source headlines with links when the AI is unavailable, fails or is out of quota | Must | Done |
| FR-08 | Rule-based "For you" tags for the reader's chosen city and topics, showing the matched word | Must | Done |
| FR-09 | English and Urdu (right to left, Nastaliq), and large print | Must | Done; Roman Urdu added after the first MVP (FR-23) |
| FR-10 | "Generate today's paper now" action | Must | Done |
| FR-11 | Last page with today's top three and their sources | Should | Done |
| FR-12 | Gift paper preview for a parent: their city, topics, language and print size | Should | Done; since extended to real sending by email (FR-21) |
| FR-13 | Publish the outlet list and the ranking formula | Must | Done (`/sources.html`) |
| FR-14 | Handle malformed, empty and duplicate feed data without crashing | Must | Done |
| FR-15 | Reader picks stories from today's top 12 on cards (pass, love, keep); the paper shows loved stories first, then kept, each group in formula order | Should | Done |
| FR-16 | When no checked summary is available, quote the outlet's own feed description, credited and linked, instead of an empty "no summary" note; retry a rejected summary once with the reasons first | Must | Done |
| FR-17 | Source lists start closed and open on click | Should | Done |
| FR-18 | Read the paper aloud (whole paper or one story) with the browser's own voices, Urdu where the device has a voice | Could | Done (added after the first MVP) |
| FR-19 | Sign up, log in and log out | Should | Done (added after the first MVP) |
| FR-20 | Two plans: Basic $3 a month (3 gift emails a month) and Plus $8 a month (30 gift emails, 15 stories to pick from, a note on gifts) | Should | Done as a prototype checkout: no payment is taken (added after the first MVP) |
| FR-21 | Send a gift paper by email through Gmail, re-ranked for the recipient's city and topics, with a preview of the exact email | Should | Done; sending needs a Gmail app password on the server (added after the first MVP) |
| FR-22 | Save the reader's settings to their account and restore them on another device | Should | Done: saved on every change while logged in; restored on log-in or on a new device |
| FR-23 | Roman Urdu as a third reading language: AI-written, grounding-checked Roman Urdu headline and summary per story; English shown, and labelled, for any story without one | Should | Done (added after the first MVP): paper, setup page, last page, gift page and gift email |
| FR-24 | Topic balance: no section (a story's first topic) fills more than 30% of the paper, rounded up (3 of 10); held-back stories return only if the paper would otherwise be short | Should | Done (added after the first MVP) |

## Non-functional requirements

| ID | Category | Requirement | Target | How measured | Result |
|----|----------|-------------|--------|--------------|--------|
| NFR-01 | Accuracy | Pairwise grouping errors on the fixed set | 0 | `test_grouping.py` | See testing.md |
| NFR-02 | Honesty | Summaries with a claim not in the sources reaching the reader | 0 | grounding check plus `test_summaries.py` | 0 in tests |
| NFR-03 | Availability | Paper generated when the AI fails | 100% | `test_paper_generates_*` | 100% in tests |
| NFR-04 | Cost | AI calls per paper | at most 3 | `edition.ai.calls`, `SUBAH_MAX_AI_CALLS` | 2 for 10 stories (batches of 5); 0 on cache hits |
| NFR-05 | Speed | Generate-now time from live feeds | under 30 s | `edition.stats.timings_ms` | See testing.md |
| NFR-06 | Security | No secret in the repository or in any API response | none | `.gitignore`, `test_health_has_no_secrets` | Pass |
| NFR-07 | Accessibility | Keyboard use, visible focus, reduced motion respected | all pages | manual check | Pass on manual check |
| NFR-08 | Security | Passwords never stored or returned in plain text | none | `test_password_is_hashed_and_checked`, `test_signup_sets_a_session_cookie_and_me_works` | Pass |
| NFR-09 | Abuse | Gift emails per account per month | 3 (Basic), 30 (Plus) | `test_gift_is_sent_and_counted` | Pass |

## Constraints

- Feed metadata and links only; no scraping of article pages.
- AI quota is limited: group first, summarise only the ten selected stories, batch and cache.
- API keys live only in the server environment.
- Test reader profiles only; no real personal data.
- Data: the app supports live feeds, a saved snapshot, or the bundled synthetic fixtures (`SUBAH_SOURCE`).

## Assumptions

- Outlets keep their public RSS feeds available.
- One reader's settings (city, up to five topics, language, print size) are enough to tailor a paper.

## Out of scope

Payments, audio edition, quiz, Roman Urdu, accounts, real delivery by email or WhatsApp, viral-claim labelling, AI judgement of importance, AI predictions about a reader's costs.

(First MVP scope. Accounts, prototype payments, gift email, read-aloud, Roman Urdu and topic balance were added later: see Changes after the first MVP.)

## Changes after the first MVP

Added after the first MVP (2026-11-10). The tables above note each addition; where the first scope differs, this section describes the current build.

- **Accounts:** readers can sign up and log in. Stored per account: name, email, a salted password hash, plan, and a log of gift emails sent. Test accounts only during the course demo.
- **Payments (prototype):** a pricing page with Basic ($3 a month) and Plus ($8 a month). Choosing a plan activates it for 30 days; no card is asked for and nothing is charged. A payment provider is needed before launch.
- **Gift papers by email:** the gift page now sends the recipient's paper through Gmail instead of only previewing it. The recipient's email address is used to send that one message and is kept in the sender's gift log.
- **Audio:** a read-aloud button uses the browser's built-in voices. No audio files are made and no extra service is used.
- **Roman Urdu (FR-23):** the third language from the original proposal. The AI writes a Roman Urdu headline and summary in the same call as English and Urdu (no extra calls). Code checks every number in it, and every capitalised name inside a sentence, against the sources; a failed Roman Urdu fails the whole story, as for English and Urdu. A story with no Roman Urdu shows its English text with a note saying so. Interface text on the paper, setup, last and gift pages, and the gift email, is in Roman Urdu; topic and city names stay in English.
- **Topic balance (FR-24):** from the original proposal's ranking. Still mechanical and published: no section takes more than 3 of 10 places. It changes which stories make the paper on a one-topic day, never the order of those that do.
- **Not changed:** the coverage label, the published outlet list, the grounding check and the no-AI fallback work exactly as in the first MVP; the ranking formula is unchanged apart from the published topic-balance rule. Paying does not change which stories a reader sees or their order.
