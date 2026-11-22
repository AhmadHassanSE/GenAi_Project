"""The last page: three takeaways and a three-question quiz, built only from the day's checked summaries.

With the AI: one call (on top of the summaries) writes three one-sentence takeaways and three multiple-choice
questions in English, Urdu and Roman Urdu. Code then checks each one against the sources of the story it is
about, exactly as summaries are checked:
- a takeaway, and a question with its correct answer, may only use numbers and names its story's sources use;
- a question is dropped when a wrong option could also be true (it uses only numbers and names from the
  sources), when two options are the same, or when the answer index is out of range.
Roman Urdu that is really English, or fails the check, is dropped on its own; pages then show English.

Without the AI, or when too few questions pass, the quiz is filled with questions built in code from facts the
paper itself states (how many outlets reported a story), so the page always has a quiz and every answer is
true by construction. Takeaways come only from the AI; without it the page keeps its "top three" list.
"""
from __future__ import annotations

import json
import os
import re

from .grounding import _names, _numbers, check, roman_is_english
from .textnorm import fold

LANGS = ("en", "ur", "ro")
ENABLED = os.environ.get("SUBAH_QUIZ", "on").lower() not in ("off", "0", "false")

SYSTEM = """You write the last page of Subah, a morning news paper read in Pakistan.

You get today's top stories, each with its id, headline and checked summary.
1. Write exactly three takeaways: one sentence each (at most 25 words), each about a different story, saying the single most useful fact.
2. Write exactly three multiple-choice questions, each about a different story, with three short options and exactly one correct answer. The correct answer must be stated plainly in that story's summary. The two wrong options must be clearly false according to the summary: a different number, place or person that the story does not mention. No trick questions, no opinions, nothing that needs outside knowledge.

Use only facts from that story's summary; copy numbers and names exactly as they appear there.
Write every takeaway, question and option in English, in Urdu, and in Roman Urdu (the Urdu language in Latin letters, the way Pakistanis text; not English; keep names, numbers and terms like AQI or IMF as they are; capitalise only the first word and proper names).
Use each story's id in "story". "answer" is the index (0, 1 or 2) of the correct option, the same in every language."""

_TEXT3 = {"type": "array", "items": {"type": "string"}}
SCHEMA = {
    "type": "object",
    "properties": {
        "takeaways": {"type": "array", "items": {
            "type": "object",
            "properties": {"story": {"type": "string"}, "en": {"type": "string"}, "ur": {"type": "string"}, "ro": {"type": "string"}},
            "required": ["story", "en", "ur", "ro"], "additionalProperties": False}},
        "quiz": {"type": "array", "items": {
            "type": "object",
            "properties": {"story": {"type": "string"},
                           "question_en": {"type": "string"}, "question_ur": {"type": "string"}, "question_ro": {"type": "string"},
                           "options_en": _TEXT3, "options_ur": _TEXT3, "options_ro": _TEXT3, "answer": {"type": "integer"}},
            "required": ["story", "question_en", "question_ur", "question_ro", "options_en", "options_ur", "options_ro", "answer"],
            "additionalProperties": False}},
    },
    "required": ["takeaways", "quiz"],
    "additionalProperties": False,
}

UR_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


# --------------------------------------------------------------------------- checks
def _as_summary(en: str, ur: str, ro: str, sources: list[dict]) -> dict:
    """Shape a takeaway or a question so the summary check can read it."""
    out = {"headline_en": en, "summary_en": en, "headline_ur": ur, "summary_ur": ur,
           "used_sources": [sources[0]["id"]] if sources else []}
    if ro:
        out.update(headline_ro=ro, summary_ro=ro)
    return out


def _texts(en: str, ur: str, ro: str, sources: list[dict]) -> dict | None:
    """The three languages if English and Urdu pass the source check; Roman Urdu kept only if it passes too."""
    out = _as_summary(en, ur, ro, sources)
    if ro and roman_is_english(out):
        ro = ""
        out = _as_summary(en, ur, "", sources)
    problems = check(out, sources)
    if problems and all("Roman Urdu" in p for p in problems):
        ro, problems = "", []
    if problems:
        return None
    return {"en": en.strip(), "ur": ur.strip(), "ro": ro.strip() or None}


def _could_be_true(option: str, sources: list[dict]) -> bool:
    """A wrong option made only of numbers and names the sources use might also be right."""
    has_facts = bool(_numbers(option) or _names(option))
    corpus = " " + fold(" ".join(f"{s.get('title', '')} {s.get('description', '')}" for s in sources)) + " "
    nums = _numbers(corpus)
    return has_facts and all(n in nums for n in _numbers(option)) and all(f" {fold(w)} " in corpus for w in _names(option))


def check_takeaway(t: dict, sources: dict[str, list[dict]]) -> dict | None:
    src = sources.get(t.get("story"))
    if not src:
        return None
    texts = _texts(t.get("en") or "", t.get("ur") or "", t.get("ro") or "", src)
    return {"story": t["story"], **texts} if texts else None


def check_question(q: dict, sources: dict[str, list[dict]]) -> dict | None:
    src = sources.get(q.get("story"))
    a = q.get("answer")
    opts = {l: [str(o).strip() for o in (q.get(f"options_{l}") or [])] for l in LANGS}
    if not src or not isinstance(a, int) or len(opts["en"]) != 3 or len(opts["ur"]) != 3 or not 0 <= a < 3:
        return None
    if len({fold(o) for o in opts["en"]}) != 3 or any(not o for o in opts["en"] + opts["ur"]):
        return None
    # the question with its correct answer must be supported by the story's sources
    qa = _texts(f"{q.get('question_en', '')} {opts['en'][a]}", f"{q.get('question_ur', '')} {opts['ur'][a]}",
                f"{q.get('question_ro', '')} {opts['ro'][a]}" if len(opts["ro"]) == 3 else "", src)
    if not qa:
        return None
    if any(_could_be_true(o, src) for k, o in enumerate(opts["en"]) if k != a):
        return None
    ro_ok = qa["ro"] is not None and len(opts["ro"]) == 3 and all(opts["ro"])
    # models tend to put the right answer first: turn the options, the same way in every language
    turn = sum(map(ord, q["story"])) % 3
    opts = {l: (o[turn:] + o[:turn]) if len(o) == 3 else o for l, o in opts.items()}
    a = (a - turn) % 3
    return {"story": q["story"], "answer": a, "source": "ai",
            "question": {"en": q["question_en"].strip(), "ur": q["question_ur"].strip(),
                         "ro": q["question_ro"].strip() if ro_ok else None},
            "options": {"en": opts["en"], "ur": opts["ur"], "ro": opts["ro"] if ro_ok else None}}


# --------------------------------------------------------------------------- questions built in code
def outlet_question(story: dict) -> dict:
    """How many outlets reported this story? The answer is the paper's own count; the other two options are
    counts the paper does not show for it."""
    n = story["outlet_count"]
    # where the right answer sits (lowest, middle, highest) varies by story, so it cannot be guessed
    shapes = [(n + 2, n + 4), (n - 2, n + 2), (n - 4, n - 2)]
    usable = [s for s in shapes if min(s) >= 1]
    wrong = usable[int(story["id"].lstrip("s")[:6] or "0", 16) % len(usable)] if usable else (n + 2, n + 4)
    options = sorted({n, *wrong})
    head = story.get("summary") or {}
    title = {l: ((head.get(l) or head.get("en") or {}).get("headline") or story["headline"].get(l) or story["headline"]["en"])
             for l in LANGS}
    return {"story": story["id"], "answer": options.index(n), "source": "rules",
            "question": {"en": f"How many outlets reported this story? “{title['en']}”",
                         "ur": f"یہ خبر کتنے اداروں نے رپورٹ کی؟ ’{title['ur']}‘",
                         "ro": f"Yeh khabar kitne idaron ne report ki? “{title['ro']}”"},
            "options": {"en": [str(o) for o in options], "ur": [str(o).translate(UR_DIGITS) for o in options],
                        "ro": [str(o) for o in options]}}


# --------------------------------------------------------------------------- the page
def build(stories: list[dict], sources: dict[str, list[dict]], client=None, use_ai: bool = True) -> dict:
    """stories: the edition's stories in paper order. sources: story id -> the sources its summary was checked
    against. client: anything with .complete(payload) -> str; None means build a Groq client if configured."""
    result = {"takeaways": [], "quiz": [], "source": "rules", "calls": 0, "note": ""}
    checked = [s for s in stories if s.get("summary")][:6]
    if use_ai and ENABLED and len(checked) >= 3:
        if client is None:
            from .summarize import GroqClient, ai_configured

            ok, why = ai_configured()
            if ok:
                try:
                    client = GroqClient(system=SYSTEM, schema=SCHEMA, schema_name="subah_closing", max_output=3500)
                except Exception as exc:  # misconfigured: rules only
                    result["note"] = f"AI client unavailable: {type(exc).__name__}"
            else:
                result["note"] = why
        if client is not None:
            # only the checked summaries go to the AI (small enough for the free tier's request limit);
            # the code below still checks everything against each story's sources
            payload = json.dumps({"stories": [{"id": s["id"], "headline": s["summary"]["en"]["headline"],
                                               "summary": s["summary"]["en"]["text"]} for s in checked]}, ensure_ascii=False)
            result["calls"] = 1
            try:
                data = json.loads(client.complete(payload))
                takeaways = [check_takeaway(t, sources) for t in (data.get("takeaways") or []) if isinstance(t, dict)]
                quiz = [check_question(q, sources) for q in (data.get("quiz") or []) if isinstance(q, dict)]
            except Exception as exc:  # any AI failure: rules only, the page still works
                takeaways, quiz = [], []
                result["note"] = f"AI closing page failed: {exc}" if "AIUnavailable" in type(exc).__name__                     else f"AI closing page failed: {type(exc).__name__}"
            seen: set[str] = set()
            for t in takeaways:
                if t and t["story"] not in seen and len(result["takeaways"]) < 3:
                    result["takeaways"].append(t)
                    seen.add(t["story"])
            seen = set()
            for q in quiz:
                if q and q["story"] not in seen and len(result["quiz"]) < 3:
                    result["quiz"].append(q)
                    seen.add(q["story"])
            if result["quiz"] or result["takeaways"]:
                result["source"] = "ai"
    # top up the quiz with questions built in code, about stories not asked about yet
    asked = {q["story"] for q in result["quiz"]}
    for s in stories:
        if len(result["quiz"]) >= 3:
            break
        if s["id"] not in asked:
            result["quiz"].append(outlet_question(s))
            asked.add(s["id"])
    return result
