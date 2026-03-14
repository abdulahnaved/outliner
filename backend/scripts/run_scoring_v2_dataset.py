#!/usr/bin/env python3
"""
Run scoring_v2 on the canonical dataset and report:
- score distribution (v2), grade distribution (v2)
- old vs new grade comparison
- example sites: old score vs new score
- whether v2 distribution is more balanced than v3.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_JSONL = BACKEND_DIR / "data" / "processed" / "scans.v3_combined.cleaned.jsonl"


def _load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Run scoring_v2 on canonical dataset and report stats")
    ap.add_argument("--input", type=Path, default=None, help=f"JSONL path (default: {DEFAULT_JSONL.name})")
    ap.add_argument("--examples", type=int, default=8, help="Number of example sites to print (old vs new score)")
    args = ap.parse_args()

    path = Path(args.input).resolve() if args.input else DEFAULT_JSONL
    if not path.exists() and args.input:
        path = BACKEND_DIR / "data" / "processed" / Path(args.input).name
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        return 1

    sys.path.insert(0, str(BACKEND_DIR))
    from services.scoring_v2 import compute_rule_score_v2

    rows = _load_jsonl(path)
    if not rows:
        print("No rows in dataset.", file=sys.stderr)
        return 1

    # Compute v2 for each row
    results = []
    for r in rows:
        features = r.get("features") or {}
        if hasattr(features, "model_dump"):
            features = features.model_dump()
        elif hasattr(features, "dict"):
            features = features.dict()
        v2 = compute_rule_score_v2(features, r.get("evidence"), include_debug=False)
        results.append({
            "row": r,
            "old_score": r.get("rule_score"),
            "old_grade": r.get("rule_grade") or "?",
            "old_label": r.get("rule_label"),
            "v2_score": v2["rule_score_v2"],
            "v2_grade": v2["rule_grade_v2"],
            "v2_label": v2["rule_label_v2"],
        })

    total = len(results)
    v2_scores = [x["v2_score"] for x in results]
    v2_grades = [x["v2_grade"] for x in results]
    v2_labels_0 = sum(1 for x in results if x["v2_label"] == 0)
    v2_labels_1 = sum(1 for x in results if x["v2_label"] == 1)
    old_scores = [float(x["old_score"]) for x in results if x["old_score"] is not None]
    old_grades = [x["old_grade"] for x in results if x["old_grade"]]
    old_label_0 = sum(1 for x in results if x["old_label"] == 0)
    old_label_1 = sum(1 for x in results if x["old_label"] == 1)

    def pct(n: int, t: int) -> str:
        return f"{100.0 * n / t:.1f}%" if t else "0%"

    grade_order = ("A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F")

    print("=== Scoring v2 on canonical dataset ===\n")
    print(f"Input: {path.name}")
    print(f"Total rows: {total}\n")

    print("--- Score distribution (v2) ---")
    if v2_scores:
        print(f"rule_score_v2: min={min(v2_scores):.1f}, median={statistics.median(v2_scores):.1f}, max={max(v2_scores):.1f}")
        print(f"mean={statistics.mean(v2_scores):.1f}, stdev={statistics.stdev(v2_scores):.2f}" if len(v2_scores) > 1 else "")
    print()

    print("--- Grade distribution (v2) ---")
    v2_grade_counts: dict[str, int] = {}
    for g in v2_grades:
        v2_grade_counts[g] = v2_grade_counts.get(g, 0) + 1
    for g in grade_order:
        if g in v2_grade_counts:
            print(f"  {g}: {v2_grade_counts[g]} ({pct(v2_grade_counts[g], total)})")
    print(f"rule_label_v2: 0 (good)={v2_labels_0} ({pct(v2_labels_0, total)}), 1 (risky)={v2_labels_1} ({pct(v2_labels_1, total)})")
    print()

    print("--- Old (v3) vs new (v2) grade comparison ---")
    old_grade_counts: dict[str, int] = {}
    for g in old_grades:
        old_grade_counts[g] = old_grade_counts.get(g, 0) + 1
    print("v3 grades:", dict(sorted(old_grade_counts.items(), key=lambda x: (grade_order.index(x[0]) if x[0] in grade_order else 99, x[0]))))
    print("v2 grades:", dict(sorted(v2_grade_counts.items(), key=lambda x: (grade_order.index(x[0]) if x[0] in grade_order else 99, x[0]))))
    print(f"v3 rule_label: 0={old_label_0} ({pct(old_label_0, total)}), 1={old_label_1} ({pct(old_label_1, total)})")
    print(f"v2 rule_label: 0={v2_labels_0} ({pct(v2_labels_0, total)}), 1={v2_labels_1} ({pct(v2_labels_1, total)})")
    print()

    print("--- Example sites (old vs new score) ---")
    # Pick a mix: some improved, some same, some worse; and spread of scores
    examples = []
    for x in results:
        host = (x["row"].get("normalized_host") or x["row"].get("requested_url") or "?")[:60]
        old = x["old_score"] if x["old_score"] is not None else 0
        examples.append((x["v2_score"] - old, x["v2_score"], old, x["v2_grade"], x["old_grade"], host))
    examples.sort(key=lambda t: (-abs(t[0]), -t[1]))  # biggest deltas first, then high v2
    n = min(args.examples, len(examples))
    for i in range(n):
        delta, v2, old, g2, g_old, host = examples[i]
        sign = "+" if delta >= 0 else ""
        print(f"  {host}: v3={old:.1f} ({g_old}) -> v2={v2:.1f} ({g2}) ({sign}{delta:.1f})")
    print()

    print("--- Balance check ---")
    if old_scores:
        old_median = statistics.median(old_scores)
        v2_median = statistics.median(v2_scores)
        old_f = sum(1 for s in old_scores if s < 60)
        v2_f = sum(1 for s in v2_scores if s < 60)
        print(f"v3 median score: {old_median:.1f}; v2 median score: {v2_median:.1f}")
        print(f"v3 count(score<60): {old_f} ({pct(old_f, total)}); v2 count(score<60): {v2_f} ({pct(v2_f, total)})")
        more_balanced = "yes" if (v2_median > old_median and v2_f < old_f) or (50 <= v2_median <= 70 and 0.2 <= v2_f / total <= 0.5) else "partially"
        print(f"V2 is less punitive (higher median, fewer F/risky): {more_balanced}.")
    else:
        print("No v3 scores in dataset to compare.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
