"""Grounded summaries for the selected stories only, with Groq.

- Runs after grouping and ranking, so only the ~10 stories that make the paper are sent.
- Stories go in batches (default 5 per call) and results are cached per story, so a regenerated paper
  reuses earlier summaries and a typical paper costs two calls.
- Input is feed metadata only: each report's headline and feed description. No article pages.
- Every result goes through grounding.check(); a story that fails, or any API error, falls back to its
  source headlines with links. The paper is always produced.
- The API key is read from the server environment and never sent to the browser.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from .grounding import check, roman_is_english

PROMPT_VERSION = "v5"  # v3: Roman Urdu added; v4: Roman Urdu example, fewer sources per story
MODEL = os.environ.get("SUBAH_MODEL", "openai/gpt-oss-120b")
BATCH_SIZE = int(os.environ.get("SUBAH_AI_BATCH", "5"))
MAX_CALLS = int(os.environ.get("SUBAH_MAX_AI_CALLS", "3"))
# Groq's free tier refuses any request whose input plus reserved output is over this many tokens (and limits
# tokens per minute to the same number), so batches are sized from an estimate and output is reserved per story.
TOKEN_LIMIT = int(os.environ.get("SUBAH_AI_TOKEN_LIMIT", "8000"))
OUTPUT_PER_STORY = 650  # English, Urdu and Roman Urdu headline and summary, JSON, and the model's reasoning
OUTPUT_BASE = 500
RATE_WAIT_MAX = float(os.environ.get("SUBAH_AI_RATE_WAIT", "40"))  # seconds to wait once when rate limited
CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "cache" / "summaries.json"

SYSTEM = """You write short summaries for Subah, a morning news paper read in Pakistan.

Each story comes with the headlines and feed descriptions published by several outlets about the same event.
For each story write a neutral headline (at most 14 words) and a summary of one or two sentences (at most 55 words) in English, then the same headline and summary in Urdu, then in Roman Urdu.

Roman Urdu is the Urdu language written in Latin letters, the way Pakistanis text. It is NOT English: translate the meaning into Urdu words, then write them in Latin letters. Example: English "Government keeps petrol price unchanged, raises diesel by Rs3" becomes Roman Urdu "Hukumat ne petrol ki qeemat barqarar rakhi, diesel Rs3 mehnga kar diya". Keep names, numbers and well-known terms (petrol, AQI, IMF) as they are; every other word must be Urdu. Capitalise only the first word and proper names of people, places and organisations, spelled as the English summary spells them; ordinary Urdu words stay lowercase, even titles and terms such as wazir-e-azam, hukumat, adalat.

Use only facts stated in that story's sources. Do not add background, causes, consequences, predictions, advice or opinion, and nothing you know from elsewhere, even if you are confident it is true. Copy numbers, names and places exactly as the sources give them: in English, spell every name the way an English source spells it, do not turn a place into an adjective (write "Turkiye", not "Turkish"), and leave out any name that appears only in an Urdu source. If the sources disagree, say that reports differ. If the sources are thin, a summary that restates the main headline is fine.
The Urdu and the Roman Urdu must say exactly what the English says, with no added facts. In Roman Urdu use Western digits, write sentence case (capitalise only the first word and names), and spell every name exactly as the English summary does.
In used_sources, list the ids of the sources your summary relies on."""

SCHEMA = {
    "type": "object",
    "properties": {
        "stories": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "headline_en": {"type": "string"},
                    "summary_en": {"type": "string"},
                    "headline_ur": {"type": "string"},
                    "summary_ur": {"type": "string"},
                    "headline_ro": {"type": "string"},
                    "summary_ro": {"type": "string"},
                    "used_sources": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "headline_en", "summary_en", "headline_ur", "summary_ur", "headline_ro", "summary_ro",
                             "used_sources"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["stories"],
    "additionalProperties": False,
}


class AIUnavailable(Exception):
    pass


def estimate_tokens(text: str) -> int:
    """A deliberately high estimate: Urdu script costs about one token per two characters, Latin about one per
    three and a half."""
    urdu = sum(1 for ch in text if "؀" <= ch <= "ۿ")
    return int(urdu / 2 + (len(text) - urdu) / 3.5) + 1


def output_budget(stories: int) -> int:
    return OUTPUT_BASE + OUTPUT_PER_STORY * max(1, stories)


def make_batches(items: list[dict], batch_size: int, limit: int = TOKEN_LIMIT) -> list[list[dict]]:
    """Consecutive batches of at most batch_size stories whose estimated input plus reserved output stays under
    the service's per-request limit, with a 10% margin. A story too big on its own still goes alone; the service
    then refuses it and that story falls back to its sources."""
    room = int(limit * 0.9) - estimate_tokens(SYSTEM)
    batches, cur, used = [], [], 0
    for it in items:
        cost = estimate_tokens(json.dumps(it, ensure_ascii=False))
        if cur and (len(cur) >= batch_size or used + cost + output_budget(len(cur) + 1) > room):
            batches.append(cur)
            cur, used = [], 0
        cur.append(it)
        used += cost
    if cur:
        batches.append(cur)
    return batches


def ai_configured() -> tuple[bool, str]:
    if os.environ.get("SUBAH_AI", "on").lower() in ("off", "0", "false"):
        return False, "AI turned off (SUBAH_AI=off)"
    if not os.environ.get("GROQ_API_KEY"):
        return False, "no GROQ_API_KEY set on the server"
    return True, "ok"


class GroqClient:
    """Groq's OpenAI-compatible chat API over httpx. Tests swap in a fake with the same .complete(payload)."""

    URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, model: str | None = None, system: str | None = None, schema: dict | None = None,
                 schema_name: str = "subah_summaries", max_output: int | None = None):
        """system, schema and max_output default to the summaries'; closing.py passes its own."""
        import httpx

        self._httpx = httpx
        self.model = model or MODEL
        self.key = os.environ["GROQ_API_KEY"]
        self.system, self.schema, self.schema_name = system or SYSTEM, schema or SCHEMA, schema_name
        self.max_output = max_output

    def _body(self, payload: str, structured: bool) -> dict:
        try:
            n = len(json.loads(payload).get("stories") or []) or 1
        except ValueError:
            n = 5
        body = {
            "model": self.model,
            "temperature": 0.2,
            "max_completion_tokens": self.max_output or output_budget(n),
            "messages": [
                {"role": "system", "content": self.system},
                {"role": "user", "content": payload},
            ],
        }
        if self.model.startswith("openai/gpt-oss"):
            body["reasoning_effort"] = "low"
        if structured:
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": self.schema_name, "schema": self.schema, "strict": True}}
        else:
            body["response_format"] = {"type": "json_object"}
        return body

    def complete(self, payload: str) -> str:
        httpx = self._httpx
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        last = None
        waited = False
        attempts = [True, False]  # strict schema first; plain JSON mode if the model does not support it
        while attempts:
            structured = attempts[0]
            try:
                resp = httpx.post(self.URL, headers=headers, json=self._body(payload, structured), timeout=90.0)
            except httpx.TimeoutException as exc:
                raise AIUnavailable("the AI took too long to answer") from exc
            except httpx.HTTPError as exc:
                raise AIUnavailable("could not reach the AI service") from exc
            if resp.status_code == 429:
                # the per-minute limit: wait once if the service says it is short, else give up for this paper
                try:
                    wait = float(resp.headers.get("retry-after", "") or 0)
                except ValueError:
                    wait = 0
                if not waited and 0 < wait <= RATE_WAIT_MAX:
                    waited = True
                    time.sleep(wait + 0.5)
                    continue
                raise AIUnavailable("rate limited or out of free quota")
            if resp.status_code == 413:
                raise AIUnavailable("request too large for the AI service's limit")
            if resp.status_code in (401, 403):
                raise AIUnavailable("API key rejected")
            if resp.status_code == 400 and structured:
                last = resp
                attempts.pop(0)
                continue
            if resp.status_code >= 400:
                raise AIUnavailable(f"AI service error {resp.status_code}")
            data = resp.json()
            choice = (data.get("choices") or [{}])[0]
            if choice.get("finish_reason") == "length":
                raise AIUnavailable("response was cut off")
            text = (choice.get("message") or {}).get("content") or ""
            if not text.strip():
                raise AIUnavailable("empty response")
            return text
        raise AIUnavailable(f"AI service error {last.status_code if last is not None else 'unknown'}")


def _signature(item: dict) -> str:
    ids = ",".join(sorted(s["id"] for s in item["sources"]))
    return hashlib.sha1(f"{PROMPT_VERSION}|{MODEL}|{ids}".encode("utf-8")).hexdigest()[:16]


def _load_cache(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_cache(path: Path, cache: dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass


@dataclass
class SummaryRun:
    results: dict = field(default_factory=dict)  # story id -> {"status": "ai"|"fallback", "reason", "en", "ur", "used_sources"}
    calls: int = 0
    cache_hits: int = 0
    enabled: bool = False
    note: str = ""
    retried: int = 0
    roman_dropped: int = 0

    def stats(self) -> dict:
        statuses = [r["status"] for r in self.results.values()]
        return {
            "enabled": self.enabled,
            "model": MODEL if self.enabled else None,
            "calls": self.calls,
            "call_budget": MAX_CALLS,
            "cache_hits": self.cache_hits,
            "retried": self.retried,
            "roman_dropped": self.roman_dropped,
            "summarised": statuses.count("ai"),
            "fallback": statuses.count("fallback"),
            "note": self.note,
        }


def summarize(items: list[dict], client=None, cache_path: Path | None = CACHE_PATH, max_calls: int = MAX_CALLS,
              batch_size: int = BATCH_SIZE) -> SummaryRun:
    """items: [{"id": story id, "sources": [{"id","outlet","lang","title","description"}]}]"""
    run = SummaryRun()
    ok, why = (True, "ok") if client is not None else ai_configured()
    if not ok:
        run.note = why
        for it in items:
            run.results[it["id"]] = {"status": "fallback", "reason": why}
        return run
    run.enabled = True
    cache = _load_cache(cache_path) if cache_path else {}

    todo = []
    for it in items:
        hit = cache.get(_signature(it))
        if hit and not check(hit, it["sources"]):
            run.results[it["id"]] = {"status": "ai", "reason": "cached", **_public(hit)}
            run.cache_hits += 1
        else:
            todo.append(it)

    if todo and client is None:
        try:
            client = GroqClient()
        except Exception as exc:  # SDK missing or misconfigured
            run.note = f"AI client unavailable: {type(exc).__name__}"
            client = None

    def run_batch(batch: list[dict], problems: dict | None = None) -> None:
        stories = []
        for it in batch:
            entry = {"id": it["id"], "sources": it["sources"]}
            if problems and problems.get(it["id"]):
                entry["rejected_because"] = problems[it["id"]]
            stories.append(entry)
        body = {"stories": stories}
        if problems:
            body["note"] = ("A previous summary for each of these stories was rejected for the reasons in rejected_because. "
                            "Write it again using only names and numbers that appear, spelled the same way, in that story's "
                            "sources. Leave out anything else.")
        payload = json.dumps(body, ensure_ascii=False)
        run.calls += 1
        try:
            raw = client.complete(payload)
            parsed = json.loads(raw)
            outs = {o.get("id"): o for o in parsed.get("stories", []) if isinstance(o, dict)}
        except AIUnavailable as exc:
            outs, err = {}, str(exc)
        except (ValueError, TypeError, AttributeError):
            outs, err = {}, "response was not valid JSON"
        except Exception as exc:  # any other failure must not stop the paper
            outs, err = {}, f"AI error: {type(exc).__name__}"
        else:
            err = "story missing from the AI response"
        for it in batch:
            out = outs.get(it["id"])
            if out is None:
                run.results[it["id"]] = {"status": "fallback", "reason": err}
                continue
            if roman_is_english(out):  # English copied into the Roman Urdu fields: drop only the Roman Urdu
                out = {k: v for k, v in out.items() if not k.endswith("_ro")}
                run.roman_dropped += 1
            found = check(out, it["sources"])
            if found and all("Roman Urdu" in p for p in found):
                # only the Roman Urdu failed: drop it, keep the checked English and Urdu
                out = {k: v for k, v in out.items() if not k.endswith("_ro")}
                run.roman_dropped += 1
                found = []
            if found:
                run.results[it["id"]] = {"status": "fallback", "reason": "grounding check failed: " + "; ".join(found[:3]),
                                         "problems": found[:5]}
                continue
            cache[_signature(it)] = out
            run.results[it["id"]] = {"status": "ai", "reason": "summarised" if not problems else "summarised on retry", **_public(out)}

    for batch in make_batches(todo, batch_size):
        if client is None:
            reason = run.note or "AI client unavailable"
        elif run.calls >= max_calls:
            reason = "AI call budget for this paper used up"
        else:
            reason = None
        if reason:
            for it in batch:
                run.results[it["id"]] = {"status": "fallback", "reason": reason}
            continue
        run_batch(batch)

    # one retry for stories whose summary failed the source check, told exactly what was rejected
    retry = [it for it in todo if run.results.get(it["id"], {}).get("problems")]
    if retry and client is not None:
        reasons = {it["id"]: run.results[it["id"]]["problems"] for it in retry}
        for batch in make_batches(retry, batch_size):
            if run.calls >= max_calls:
                break
            run_batch(batch, reasons)
            run.retried += len(batch)
    for r in run.results.values():
        r.pop("problems", None)
    if cache_path:
        _save_cache(cache_path, cache)
    return run


def _public(out: dict) -> dict:
    pub = {
        "en": {"headline": out["headline_en"].strip(), "text": out["summary_en"].strip()},
        "ur": {"headline": out["headline_ur"].strip(), "text": out["summary_ur"].strip()},
        "used_sources": list(out.get("used_sources") or []),
    }
    ro_head, ro_text = (out.get("headline_ro") or "").strip(), (out.get("summary_ro") or "").strip()
    if ro_head and ro_text:  # optional: without it the Roman Urdu reader gets the English text
        pub["ro"] = {"headline": ro_head, "text": ro_text}
    return pub
