"""Mechanical, published ranking. No AI judges importance.

score = number of distinct outlets reporting the story
        + 2 if the story names the reader's city
        + 1 for each of the reader's topics it matches (at most 2)
Ties go to the story with the most recent report, then to the story id (stable).

Topic balance: a story's section is its first topic in catalog order (the label the paper shows). No section
may fill more than 3 of 10 places (30% of the paper, rounded up). A story over that limit waits below the
paper and comes back, in score order, only if there are not enough other stories to fill it. Stories with
no topic are not limited.
"""
from __future__ import annotations

import math

from .group import Story
from .tags import TOPICS, for_you

FORMULA = {
    "en": "Score = outlets reporting the story, plus 2 if it names your city, plus 1 per matching topic (at most 2). Ties go to the newest report. No section fills more than 3 of 10 places.",
    "ur": "اسکور = خبر رپورٹ کرنے والے اداروں کی تعداد، آپ کے شہر کا ذکر ہو تو ۲ مزید، اور ہر ملتے موضوع کا ۱ (زیادہ سے زیادہ ۲)۔ برابری پر تازہ ترین رپورٹ پہلے۔ کوئی ایک شعبہ ۱۰ میں سے ۳ سے زیادہ جگہیں نہیں لیتا۔",
    "ro": "Score = khabar report karne wale idaron ki tadaad, aap ke shehar ka zikr ho to 2 mazeed, aur har milte mauzoo ka 1 (zyada se zyada 2). Barabari par sab se taaza report pehle. Koi ek shoba 10 mein se 3 se zyada jagah nahin leta.",
}
CITY_BONUS = 2
TOPIC_BONUS = 1
TOPIC_BONUS_MAX = 2
SECTION_SHARE = 0.3  # at most 30% of the paper, rounded up, from one section


def score(story: Story, profile: dict) -> tuple[float, dict, list[dict]]:
    tags = for_you(story, profile)
    city = CITY_BONUS if any(t["type"] == "city" for t in tags) else 0
    topics = min(TOPIC_BONUS_MAX, TOPIC_BONUS * sum(1 for t in tags if t["type"] == "topic"))
    parts = {"outlets": story.outlet_count, "city": city, "topics": topics}
    return float(sum(parts.values())), parts, tags


def section_of(story: Story) -> str | None:
    """The story's main section: its first topic in catalog order, as the paper labels it."""
    return next((k for k in TOPICS if k in (story.topics or {})), None)


def section_cap(limit: int) -> int:
    return max(1, math.ceil(limit * SECTION_SHARE))


def rank(stories: list[Story], profile: dict, limit: int = 10) -> list[dict]:
    scored = []
    for s in stories:
        total, parts, tags = score(s, profile)
        scored.append({"story": s, "score": total, "parts": parts, "for_you": tags})
    scored.sort(key=lambda x: (-x["score"], -x["story"].latest.timestamp(), x["story"].id))

    cap = section_cap(limit)
    picked, waiting, per_section = [], [], {}
    for item in scored:
        sec = section_of(item["story"])
        if sec is not None and per_section.get(sec, 0) >= cap:
            waiting.append(item)
            continue
        per_section[sec] = per_section.get(sec, 0) + 1
        picked.append(item)
        if len(picked) == limit:
            break
    if len(picked) < limit:  # not enough variety today: fill from the waiting stories, still in score order
        picked += waiting[: limit - len(picked)]
        picked.sort(key=lambda x: (-x["score"], -x["story"].latest.timestamp(), x["story"].id))

    for i, item in enumerate(picked, start=1):
        item["rank"] = i
        item["section"] = section_of(item["story"])
    return picked
