"""The evaluation tools count correctly and never fill in a label themselves."""
import numpy as np

from server.tools import evaluate


def test_pair_choice_mixes_inside_and_near_misses():
    groups = [0, 0, 0, 1, 1, 2, 3, 4]
    rng = np.random.default_rng(0)
    sim = rng.random((8, 8))
    sim = (sim + sim.T) / 2
    pairs = evaluate.choose_pairs(groups, sim, n=12)
    assert len(pairs) == len(set(pairs)) == 12
    inside = [p for p in pairs if groups[p[0]] == groups[p[1]]]
    assert len(inside) == 4  # a third, and there are exactly 4 inside pairs
    across = sorted((p for p in pairs if groups[p[0]] != groups[p[1]]), key=lambda p: -sim[p])
    all_across = sorted(((i, j) for i in range(8) for j in range(i + 1, 8) if groups[i] != groups[j]), key=lambda p: -sim[p])
    assert across[:6] == all_across[:6]  # the most similar different-group pairs are always judged


def test_precision_and_recall():
    labels = {"p1": True, "p2": True, "p3": False, "p4": False, "p5": True}
    predicted = {"p1": True, "p2": False, "p3": True, "p4": False, "p5": True}
    s = evaluate.score_pairs(labels, predicted)
    assert (s["tp"], s["fp"], s["fn"], s["tn"]) == (2, 1, 1, 1)
    assert s["precision"] == 2 / 3 and s["recall"] == 2 / 3


def test_audit_sheet_rows_and_scores(tmp_path):
    edition = {"edition_id": "e1", "stories": [
        {"id": "s1", "summary": {"en": {"headline": "H", "text": "T"}, "ur": {"headline": "ح", "text": "ت"}},
         "sources": [{"outlet": "Dawn", "title": "A", "description": "B"}]},
        {"id": "s2", "summary": None, "sources": []},
    ]}
    rows = evaluate.audit_rows(edition)
    assert [r["story"] for r in rows] == ["s1"] and rows[0]["unsupported_claims"] == ""  # left for a person
    filled = [dict(rows[0], unsupported_claims="0", urdu_rating="5", roman_rating="12"),
              dict(rows[0], story="s3", unsupported_claims="2", urdu_rating="3", roman_rating="")]
    s = evaluate.score_audit(filled)
    assert s["audited"] == 2 and s["with_unsupported"] == 1 and s["unsupported_per_summary"] == 1.0
    assert s["urdu_average"] == 4.0 and s["roman_rated"] == 0  # "12" is not a rating
