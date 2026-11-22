"""Takeaways and quiz on the last page: checked against each story's sources, always a quiz, never a guess."""
import json

from server.subah import closing
from server.subah.edition import build_edition

SRC = {"s1": [{"id": "a1", "outlet": "Dawn", "lang": "en", "title": "Govt keeps petrol price unchanged, raises diesel by Rs3 per litre",
               "description": "Diesel goes up by Rs3 per litre in Lahore and Karachi."}],
       "s2": [{"id": "b1", "outlet": "Geo", "lang": "en", "title": "Lahore AQI crosses 500 as smog worsens", "description": ""}]}


def q(**kw):
    base = {"story": "s1", "question_en": "How much did diesel go up per litre?", "question_ur": "ڈیزل فی لیٹر کتنا مہنگا ہوا؟",
            "question_ro": "Diesel fi litre kitna mehnga hua?", "options_en": ["Rs3", "Rs7", "Rs12"],
            "options_ur": ["۳ روپے", "۷ روپے", "۱۲ روپے"], "options_ro": ["Rs3", "Rs7", "Rs12"], "answer": 0}
    base.update(kw)
    return base


def test_a_supported_question_passes():
    out = closing.check_question(q(), SRC)
    assert out and out["options"]["en"][out["answer"]] == "Rs3"  # options may be turned; the answer follows
    assert out["options"]["ro"][out["answer"]] == "Rs3" and out["options"]["ur"][out["answer"]] == "۳ روپے"


def test_questions_are_rejected_when_wrong_or_ambiguous():
    assert closing.check_question(q(options_en=["Rs5", "Rs7", "Rs12"]), SRC) is None          # answer not in sources
    assert closing.check_question(q(options_en=["Rs3", "Rs3", "Rs12"]), SRC) is None          # two options the same
    assert closing.check_question(q(answer=3), SRC) is None                                     # no such option
    assert closing.check_question(q(options_en=["Rs3", "Karachi", "Rs12"]), SRC) is None       # a wrong option is also in the sources
    assert closing.check_question(q(story="zz"), SRC) is None                                   # unknown story


def test_roman_urdu_that_is_english_is_dropped_alone():
    out = closing.check_question(q(question_ro="How much did diesel go up per litre in the city?"), SRC)
    assert out and out["question"]["ro"] is None and out["question"]["en"]


def test_takeaways_are_checked():
    good = {"story": "s2", "en": "Lahore AQI crossed 500.", "ur": "لاہور کا اے کیو آئی 500 سے اوپر گیا۔", "ro": "Lahore ka AQI 500 se oopar gaya."}
    assert closing.check_takeaway(good, SRC)["ro"] == "Lahore ka AQI 500 se oopar gaya."
    assert closing.check_takeaway(dict(good, en="Lahore AQI crossed 700."), SRC) is None


def test_rules_quiz_answers_are_the_papers_own_counts(collection):
    ed = build_edition({}, collection=collection, cache_path=None)
    quiz = ed["closing"]["quiz"]
    assert len(quiz) == 3 and all(x["source"] == "rules" for x in quiz)
    by_id = {s["id"]: s for s in ed["stories"]}
    for x in quiz:
        assert int(x["options"]["en"][x["answer"]]) == by_id[x["story"]]["outlet_count"]
        assert len(set(x["options"]["en"])) == 3
    positions = {closing.outlet_question({"id": f"s{i:x}abc", "outlet_count": 9, "headline": {"en": "H"}})["answer"]
                 for i in range(40)}
    assert positions == {0, 1, 2}  # the right answer is not always in the same place


class FakeClient:
    def __init__(self, reply):
        self.reply, self.calls = reply, 0

    def complete(self, payload):
        self.calls += 1
        return self.reply(json.loads(payload)) if callable(self.reply) else self.reply


def echo_summaries(payload):
    return json.dumps({"stories": [{"id": s["id"], "headline_en": s["sources"][0]["title"], "summary_en": s["sources"][0]["title"],
                                    "headline_ur": s["sources"][0]["title"], "summary_ur": s["sources"][0]["title"],
                                    "headline_ro": "", "summary_ro": "", "used_sources": [s["sources"][0]["id"]]}
                                   for s in payload["stories"]]})


def test_ai_closing_page_mixes_checked_ai_questions_and_rules(collection):
    def closing_reply(payload):
        st = payload["stories"]
        bad = {"story": st[1]["id"], "question_en": "Which minister resigned?", "question_ur": "کون سا وزیر مستعفی ہوا؟",
               "question_ro": "Kaun sa wazir mustafi hua?", "options_en": ["Ahmed Raza", "Bilal Khan", "Omar Ali"],
               "options_ur": ["احمد", "بلال", "عمر"], "options_ro": ["Ahmed Raza", "Bilal Khan", "Omar Ali"], "answer": 0}
        good = {"story": st[0]["id"], "question_en": "Which story is this?", "question_ur": "یہ کون سی خبر ہے؟",
                "question_ro": "Yeh kaunsi khabar hai?", "options_en": [st[0]["headline"], "zz", "yy"],
                "options_ur": ["الف", "ب", "ج"], "options_ro": ["a", "b", "c"], "answer": 0}
        take = {"story": st[0]["id"], "en": st[0]["summary"], "ur": st[0]["summary"], "ro": ""}
        return json.dumps({"takeaways": [take], "quiz": [good, bad]})

    closing_client = FakeClient(closing_reply)
    ed = build_edition({}, collection=collection, cache_path=None, client=FakeClient(echo_summaries), closing_client=closing_client)
    end = ed["closing"]
    assert closing_client.calls == 1 and ed["ai"]["closing_calls"] == 1
    assert end["source"] == "ai" and len(end["takeaways"]) == 1
    assert [x["source"] for x in end["quiz"]] == ["ai", "rules", "rules"]  # the made-up minister was dropped


def test_closing_ai_failure_still_gives_a_quiz(collection):
    ed = build_edition({}, collection=collection, cache_path=None, client=FakeClient(echo_summaries),
                       closing_client=FakeClient("not json"))
    assert len(ed["closing"]["quiz"]) == 3 and ed["closing"]["takeaways"] == []
    assert "failed" in ed["ai"]["closing_note"]
