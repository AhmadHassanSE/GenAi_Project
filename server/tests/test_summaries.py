"""Checks: summaries contain no claims absent from the linked sources, and the paper still generates
when the AI fails."""
import json

import pytest

from server.subah.edition import build_edition
from server.subah.grounding import check
from server.subah.summarize import TOKEN_LIMIT, estimate_tokens, make_batches, output_budget, summarize, SYSTEM

SOURCES = [
    {"id": "a1", "outlet": "Dawn", "lang": "en", "title": "Govt keeps petrol price unchanged, raises diesel by Rs3 per litre",
     "description": "The federal government kept the price of petrol unchanged for the next fortnight and increased high-speed diesel by Rs3 per litre."},
    {"id": "a2", "outlet": "Express", "lang": "ur", "title": "پیٹرول کی قیمت برقرار، ڈیزل 3 روپے مہنگا", "description": ""},
]
GOOD = {
    "id": "s1",
    "headline_en": "Petrol price unchanged, diesel up Rs3 per litre",
    "summary_en": "The federal government kept petrol unchanged for the next fortnight and raised high-speed diesel by Rs3 per litre.",
    "headline_ur": "پیٹرول کی قیمت برقرار، ڈیزل ۳ روپے مہنگا",
    "summary_ur": "حکومت نے پیٹرول کی قیمت برقرار رکھی اور ڈیزل 3 روپے فی لیٹر مہنگا کر دیا۔",
    "headline_ro": "Petrol ki qeemat barqarar, diesel Rs3 mehnga",
    "summary_ro": "Hukumat ne agle pandrah din ke liye petrol ki qeemat barqarar rakhi aur high-speed diesel Rs3 fi litre mehnga kar diya.",
    "used_sources": ["a1", "a2"],
}


def test_grounded_summary_passes():
    assert check(GOOD, SOURCES) == []


@pytest.mark.parametrize("field,value,expect", [
    ("summary_en", "Diesel rose by Rs5 per litre.", "number 5"),
    ("summary_en", "Finance Minister Aurangzeb announced the change.", "name 'Finance'"),
    ("summary_en", "The IMF welcomed the decision.", "name 'IMF'"),
    ("summary_ur", "ڈیزل ۷ روپے مہنگا ہو گیا۔", "number 7"),
    ("headline_en", "", "headline_en is empty"),
    ("summary_ro", "Diesel Rs5 mehnga ho gaya.", "number 5 in the Roman Urdu"),
    ("summary_ro", "Hukumat ne kaha ke IMF ne faisle ka khairmaqdam kiya.", "name 'IMF' in the Roman Urdu"),
    ("summary_ro", "", "Roman Urdu headline or summary is empty"),
])
def test_unsupported_claims_are_rejected(field, value, expect):
    out = dict(GOOD, **{field: value})
    problems = check(out, SOURCES)
    assert any(expect in p for p in problems), problems


def test_roman_urdu_is_optional_and_opening_words_are_not_names():
    without = {k: v for k, v in GOOD.items() if not k.endswith("_ro")}
    assert check(without, SOURCES) == []
    # "Hukumat" opens the sentence, so it is not read as a name; "Govt" inside a sentence is a name and is in the sources
    out = dict(GOOD, summary_ro="Hukumat ne kaha ke Govt ne petrol ki qeemat barqarar rakhi.")
    assert check(out, SOURCES) == []


def test_roman_urdu_reaches_the_edition_only_when_written():
    def reply(payload):
        data = json.loads(echo_good(payload))
        data["stories"][0].update(headline_ro="Petrol ki qeemat barqarar", summary_ro="Hukumat ne petrol ki qeemat barqarar rakhi.")
        return json.dumps(data)

    run = summarize(ITEMS[:2], client=FakeClient(reply), cache_path=None)
    assert run.results["s0"]["ro"]["headline"] == "Petrol ki qeemat barqarar"
    assert "ro" not in run.results["s1"]  # no Roman Urdu written: the page shows English for this story


def test_english_in_the_roman_urdu_drops_only_the_roman_urdu():
    def reply(payload):
        data = json.loads(echo_good(payload))
        for s in data["stories"]:
            s.update(headline_ro=s["headline_en"], summary_ro="Diesel went up for the next fortnight, the government said.")
        return json.dumps(data)

    run = summarize(ITEMS[:2], client=FakeClient(reply), cache_path=None)
    assert all(r["status"] == "ai" and "ro" not in r for r in run.results.values())
    assert run.stats()["roman_dropped"] == 2


def test_a_failed_roman_urdu_check_drops_only_the_roman_urdu():
    def reply(payload):
        data = json.loads(echo_good(payload))
        data["stories"][0].update(headline_ro="Diesel 9 rupay mehnga", summary_ro="Hukumat ne diesel 9 rupay mehnga kar diya.")
        return json.dumps(data)

    run = summarize(ITEMS[:1], client=FakeClient(reply), cache_path=None)
    assert run.results["s0"]["status"] == "ai" and "ro" not in run.results["s0"]
    assert run.stats()["roman_dropped"] == 1


def test_batches_fit_the_request_limit():
    long_desc = "پیٹرول کی قیمت " * 120  # Urdu costs more tokens per character
    items = [{"id": f"s{i}", "sources": [dict(SOURCES[1], id=f"a{i}{k}", description=long_desc) for k in range(6)]}
             for i in range(10)]
    batches = make_batches(items, batch_size=5)
    assert [it["id"] for b in batches for it in b] == [it["id"] for it in items]  # order kept, nothing lost
    for b in batches:
        size = estimate_tokens(SYSTEM) + sum(estimate_tokens(json.dumps(it, ensure_ascii=False)) for it in b)
        assert len(b) == 1 or size + output_budget(len(b)) <= TOKEN_LIMIT * 0.9
    assert len(make_batches(ITEMS, batch_size=5)) == 2  # small stories still go five at a time


def test_citing_sources_from_another_story_is_rejected():
    out = dict(GOOD, used_sources=["a1", "zz"])
    assert any("outside this story" in p for p in check(out, SOURCES))


class FakeClient:
    def __init__(self, reply):
        self.reply = reply
        self.calls = 0

    def complete(self, payload):
        self.calls += 1
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply(json.loads(payload)) if callable(self.reply) else self.reply


def echo_good(payload):
    stories = []
    for s in payload["stories"]:
        src = s["sources"][0]
        stories.append({"id": s["id"], "headline_en": src["title"], "summary_en": src["title"],
                        "headline_ur": src["title"], "summary_ur": src["title"], "used_sources": [src["id"]]})
    return json.dumps({"stories": stories})


ITEMS = [{"id": f"s{i}", "sources": [dict(SOURCES[0], id=f"a{i}")]} for i in range(7)]


def test_batches_and_call_budget():
    client = FakeClient(echo_good)
    run = summarize(ITEMS, client=client, cache_path=None, batch_size=5, max_calls=3)
    assert client.calls == 2  # 7 stories in batches of 5
    assert run.stats()["summarised"] == 7

    client = FakeClient(echo_good)
    run = summarize(ITEMS, client=client, cache_path=None, batch_size=5, max_calls=1)
    assert client.calls == 1
    assert run.stats()["fallback"] == 2
    assert "budget" in run.results["s6"]["reason"]


def test_cache_avoids_repeat_calls(tmp_path):
    cache = tmp_path / "c.json"
    summarize(ITEMS[:2], client=FakeClient(echo_good), cache_path=cache)
    client = FakeClient(echo_good)
    run = summarize(ITEMS[:2], client=client, cache_path=cache)
    assert client.calls == 0 and run.cache_hits == 2


@pytest.mark.parametrize("reply", ["not json", json.dumps({"stories": []}), RuntimeError("boom"), "{\"stories\": [1, 2]}"])
def test_bad_ai_output_falls_back(reply):
    run = summarize(ITEMS[:2], client=FakeClient(reply), cache_path=None)
    assert all(r["status"] == "fallback" for r in run.results.values())


def test_ungrounded_story_falls_back_alone():
    def reply(payload):
        data = json.loads(echo_good(payload))
        data["stories"][0]["summary_en"] = "Prices rose by 40 percent, officials in Karachi said."
        return json.dumps(data)

    run = summarize(ITEMS[:3], client=FakeClient(reply), cache_path=None)
    assert run.results["s0"]["status"] == "fallback"
    assert "grounding" in run.results["s0"]["reason"]
    assert run.results["s1"]["status"] == run.results["s2"]["status"] == "ai"


def test_rejected_story_is_retried_with_the_reasons():
    seen = []

    def reply(payload):
        seen.append(payload)
        data = json.loads(echo_good(payload))
        if "note" not in payload:  # first attempt: make s0 ungrounded
            data["stories"][0]["summary_en"] = "Prices rose by 40 percent, officials in Karachi said."
        return json.dumps(data)

    client = FakeClient(reply)
    run = summarize(ITEMS[:3], client=client, cache_path=None)
    assert client.calls == 2 and run.retried == 1
    assert run.results["s0"]["status"] == "ai" and run.results["s0"]["reason"] == "summarised on retry"
    retry_payload = seen[1]
    assert [s["id"] for s in retry_payload["stories"]] == ["s0"]
    assert any("40" in p for p in retry_payload["stories"][0]["rejected_because"])


def test_retry_respects_the_call_budget():
    def reply(payload):
        data = json.loads(echo_good(payload))
        data["stories"][0]["summary_en"] = "Prices rose by 40 percent."
        return json.dumps(data)

    client = FakeClient(reply)
    run = summarize(ITEMS[:3], client=client, cache_path=None, max_calls=1)
    assert client.calls == 1 and run.results["s0"]["status"] == "fallback"


PROFILE = {"city": "lahore", "topics": ["prices", "cricket"], "lang": "en"}


def assert_complete_paper(ed):
    assert len(ed["stories"]) == 10
    for s in ed["stories"]:
        assert s["headline"]["en"] and s["sources"]
        assert all(src["link"].startswith("http") for src in s["sources"])
        assert s["coverage"]["en"].startswith("Reported by")


def test_paper_generates_without_ai(monkeypatch, collection):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    ed = build_edition(PROFILE, collection=collection, cache_path=None)
    assert_complete_paper(ed)
    assert ed["ai"]["enabled"] is False
    assert all(s["summary_status"] == "fallback" and s["summary"] is None for s in ed["stories"])
    # no story is left without text: each quotes an outlet's own feed description, credited and linked
    for s in ed["stories"]:
        own = s["brief"]["en"] or s["brief"]["ur"]
        assert own and own["text"] and own["outlet"] and own["link"].startswith("http")
        corpus = " ".join(src_desc for src_desc in (a.summary for a in collection.articles if a.link == own["link"]))
        assert own["text"].rstrip("…") in corpus or own["text"].rstrip("…")[:60] in corpus


def test_paper_generates_when_ai_errors(collection):
    ed = build_edition(PROFILE, collection=collection, client=FakeClient(RuntimeError("API down")), cache_path=None)
    assert_complete_paper(ed)
    assert ed["ai"]["fallback"] == 10


def test_paper_with_working_ai(collection):
    ed = build_edition(PROFILE, collection=collection, client=FakeClient(echo_good), cache_path=None)
    assert_complete_paper(ed)
    assert ed["ai"]["summarised"] == 10 and ed["ai"]["calls"] == 2
    assert ed["stories"][0]["for_you"], "the top story for a Lahore reader who follows prices should carry a tag"
