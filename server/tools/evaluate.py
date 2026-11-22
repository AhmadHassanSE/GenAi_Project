"""The proposal's evaluation, as sheets people fill in and scores computed from them.

Nothing here invents a label: the tool picks what to judge, a person judges it in a spreadsheet, and the tool
counts. CSV files are written as UTF-8 with a byte-order mark so Excel shows Urdu correctly.

1. Grouping (proposal: 200 hand-labelled article pairs, precision > 90%, recall > 85% for same-event detection)

   python -m server.tools.evaluate pairs-sample --out eval/pairs.csv [--snapshot DIR] [--n 200]
       Groups a saved snapshot of the real feeds and picks pairs to judge: a third from inside predicted groups,
       the rest from different groups, mostly the most similar ones (where mistakes happen). The sheet does not
       show what Subah decided; that goes to eval/pairs.key.json so the person labelling is not swayed.
       Fill the "label" column with "same" (same event) or "different".
   python -m server.tools.evaluate pairs-score --pairs eval/pairs.csv
       Precision, recall and F1 for "same event", and the pairs Subah got wrong.

2. Summaries (proposal: audit 100 summaries, under 2% unsupported claims; native-speaker rating above 4 of 5)

   python -m server.tools.evaluate audit-add --sheet eval/audit.csv [--edition FILE]
       Appends every AI summary in an edition (default: the latest paper) that is not on the sheet yet, with its
       sources. Run it after each day's paper until the sheet has 100 rows.
       Fill in: unsupported_claims (how many claims in the English summary the sources do not support, 0 if none),
       and urdu_rating / roman_rating (1 to 5, by a native speaker; leave blank if not rated).
   python -m server.tools.evaluate audit-score --sheet eval/audit.csv
       Share of summaries with an unsupported claim, unsupported claims per summary, and average ratings.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAIR_FIELDS = ["pair", "a_outlet", "a_lang", "a_headline", "a_description", "b_outlet", "b_lang", "b_headline",
               "b_description", "label", "notes"]
AUDIT_FIELDS = ["story", "edition", "headline_en", "summary_en", "summary_ur", "summary_ro", "sources",
                "unsupported_claims", "urdu_rating", "roman_rating", "notes"]


def _write(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def _read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# --------------------------------------------------------------------------- grouping pairs
def choose_pairs(groups: list[int], sim, n: int, seed: int = 7) -> list[tuple[int, int]]:
    """A third of the pairs from inside predicted groups; the rest from different groups, three quarters of
    them the most similar such pairs and a quarter at random. Each pair appears once."""
    rng = random.Random(seed)
    count = len(groups)
    inside = [(i, j) for i in range(count) for j in range(i + 1, count) if groups[i] == groups[j]]
    across = [(i, j) for i in range(count) for j in range(i + 1, count) if groups[i] != groups[j]]
    rng.shuffle(inside)
    want_inside = min(len(inside), n // 3)
    chosen = inside[:want_inside]
    rest = n - len(chosen)
    across.sort(key=lambda p: -float(sim[p[0], p[1]]))
    near = across[: (rest * 3) // 4]
    others = across[len(near):]
    rng.shuffle(others)
    chosen += near + others[: rest - len(near)]
    rng.shuffle(chosen)
    return chosen


def pairs_sample(args) -> None:
    from server.subah import feeds
    from server.subah.edition import SNAPSHOTS_DIR, latest_snapshot
    from server.subah.embed import get_embedder
    from server.subah.group import group_articles, similarity

    snap = Path(args.snapshot) if args.snapshot else latest_snapshot()
    if not snap:
        sys.exit(f"No saved snapshot in {SNAPSHOTS_DIR}. Generate a live paper first.")
    col = feeds.collect_snapshot(snap, feeds.load_outlets(), max_age_hours=36)
    arts = col.articles
    embedder = get_embedder()
    stories = group_articles(arts, embedder)
    where = {a.id: k for k, s in enumerate(stories) for a in s.articles}
    groups = [where[a.id] for a in arts]
    sim = similarity(arts, embedder)
    pairs = choose_pairs(groups, sim, args.n)

    rows, key = [], {}
    for k, (i, j) in enumerate(pairs, 1):
        a, b = arts[i], arts[j]
        pid = f"p{k:03d}"
        rows.append({"pair": pid, "a_outlet": a.outlet_name, "a_lang": a.lang, "a_headline": a.title,
                     "a_description": a.summary, "b_outlet": b.outlet_name, "b_lang": b.lang, "b_headline": b.title,
                     "b_description": b.summary, "label": "", "notes": ""})
        key[pid] = {"predicted_same": groups[i] == groups[j], "similarity": round(float(sim[i, j]), 4),
                    "a": a.id, "b": b.id}
    out = Path(args.out)
    _write(out, PAIR_FIELDS, rows)
    out.with_suffix(".key.json").write_text(json.dumps({"snapshot": str(snap), "pairs": key}, indent=1), encoding="utf-8")
    same = sum(v["predicted_same"] for v in key.values())
    print(f"Wrote {len(rows)} pairs to {out} ({same} from inside groups) and the answers to {out.with_suffix('.key.json')}.")
    print('Fill the "label" column with "same" or "different", then run pairs-score.')


def score_pairs(labels: dict[str, bool], predicted: dict[str, bool]) -> dict:
    tp = sum(1 for p, same in labels.items() if same and predicted[p])
    fp = sum(1 for p, same in labels.items() if not same and predicted[p])
    fn = sum(1 for p, same in labels.items() if same and not predicted[p])
    tn = len(labels) - tp - fp - fn
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * precision * recall / (precision + recall) if precision and recall else None
    return {"labelled": len(labels), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": precision, "recall": recall, "f1": f1}


def pairs_score(args) -> None:
    sheet = Path(args.pairs)
    key = json.loads(sheet.with_suffix(".key.json").read_text(encoding="utf-8"))["pairs"]
    labels, bad = {}, []
    for row in _read(sheet):
        v = (row.get("label") or "").strip().lower()
        if v in ("same", "s", "yes", "y", "1"):
            labels[row["pair"]] = True
        elif v in ("different", "diff", "d", "no", "n", "0"):
            labels[row["pair"]] = False
        elif v:
            bad.append(row["pair"])
    if not labels:
        sys.exit("No labelled pairs yet.")
    s = score_pairs(labels, {p: key[p]["predicted_same"] for p in labels})
    pct = lambda x: "n/a" if x is None else f"{x * 100:.1f}%"
    print(f"Labelled pairs: {s['labelled']} (same event: {s['tp'] + s['fn']}, different: {s['fp'] + s['tn']})")
    print(f"Precision {pct(s['precision'])} (target above 90%)   Recall {pct(s['recall'])} (target above 85%)   F1 {pct(s['f1'])}")
    print(f"Merged wrongly: {s['fp']}   Split wrongly: {s['fn']}")
    for p, same in sorted(labels.items()):
        if same != key[p]["predicted_same"]:
            print(f"  {p}: labelled {'same' if same else 'different'}, Subah said "
                  f"{'same' if key[p]['predicted_same'] else 'different'} (similarity {key[p]['similarity']})")
    if bad:
        print(f"Unreadable labels (use same or different): {', '.join(bad)}")


# --------------------------------------------------------------------------- summary audit
def audit_rows(edition: dict) -> list[dict]:
    rows = []
    for st in edition.get("stories", []):
        sm = st.get("summary")
        if not sm:
            continue
        sources = "\n".join(f"[{s['outlet']}] {s['title']}" + (f" — {s['description']}" if s.get("description") else "")
                            for s in st["sources"])
        rows.append({"story": st["id"], "edition": edition.get("edition_id", ""), "headline_en": sm["en"]["headline"],
                     "summary_en": sm["en"]["text"], "summary_ur": sm.get("ur", {}).get("text", ""),
                     "summary_ro": sm.get("ro", {}).get("text", ""), "sources": sources,
                     "unsupported_claims": "", "urdu_rating": "", "roman_rating": "", "notes": ""})
    return rows


def audit_add(args) -> None:
    from server.subah.edition import load_latest

    edition = json.loads(Path(args.edition).read_text(encoding="utf-8")) if args.edition else load_latest()
    if not edition:
        sys.exit("No paper yet. Generate one first.")
    sheet = Path(args.sheet)
    have = _read(sheet) if sheet.exists() else []
    seen = {r["story"] for r in have}
    new = [r for r in audit_rows(edition) if r["story"] not in seen]
    _write(sheet, AUDIT_FIELDS, have + new)
    print(f"Added {len(new)} summaries; the sheet has {len(have) + len(new)} of the 100 the proposal asks for.")
    if not new and not audit_rows(edition):
        print("This paper has no AI summaries (no GROQ_API_KEY, or every summary fell back).")


def score_audit(rows: list[dict]) -> dict:
    def ratings(col: str) -> list[int]:
        return [int(v) for v in ((r.get(col) or "").strip() for r in rows) if v in {"1", "2", "3", "4", "5"}]

    claims = [int(r["unsupported_claims"]) for r in rows if (r.get("unsupported_claims") or "").strip().isdigit()]
    ur, ro = ratings("urdu_rating"), ratings("roman_rating")
    return {
        "audited": len(claims),
        "with_unsupported": sum(1 for c in claims if c > 0),
        "share_with_unsupported": (sum(1 for c in claims if c > 0) / len(claims)) if claims else None,
        "unsupported_per_summary": (sum(claims) / len(claims)) if claims else None,
        "urdu_rated": len(ur), "urdu_average": (sum(ur) / len(ur)) if ur else None,
        "roman_rated": len(ro), "roman_average": (sum(ro) / len(ro)) if ro else None,
    }


def audit_score(args) -> None:
    s = score_audit(_read(Path(args.sheet)))
    if not s["audited"] and not s["urdu_rated"] and not s["roman_rated"]:
        sys.exit("Nothing filled in yet.")
    pct = lambda x: "n/a" if x is None else f"{x * 100:.1f}%"
    num = lambda x: "n/a" if x is None else f"{x:.2f}"
    print(f"Audited summaries: {s['audited']} (the proposal asks for 100)")
    print(f"With an unsupported claim: {s['with_unsupported']} ({pct(s['share_with_unsupported'])}; target under 2%)")
    print(f"Unsupported claims per summary: {num(s['unsupported_per_summary'])}")
    print(f"Urdu rating: {num(s['urdu_average'])} from {s['urdu_rated']} ratings; "
          f"Roman Urdu: {num(s['roman_average'])} from {s['roman_rated']} (target above 4)")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pairs-sample"); p.add_argument("--out", default="eval/pairs.csv"); p.add_argument("--snapshot"); p.add_argument("--n", type=int, default=200)
    p = sub.add_parser("pairs-score"); p.add_argument("--pairs", default="eval/pairs.csv")
    p = sub.add_parser("audit-add"); p.add_argument("--sheet", default="eval/audit.csv"); p.add_argument("--edition")
    p = sub.add_parser("audit-score"); p.add_argument("--sheet", default="eval/audit.csv")
    args = ap.parse_args(argv)
    {"pairs-sample": pairs_sample, "pairs-score": pairs_score, "audit-add": audit_add, "audit-score": audit_score}[args.cmd](args)


if __name__ == "__main__":
    main()
