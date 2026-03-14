#!/usr/bin/env python3
"""
Sanity-check scoring_v2 on known sites and report distribution extremes.
1) Report for recognizable sites: v3 vs v2 score/grade and top v2 reasons.
2) Top 20 and bottom 20 by rule_score_v2 with score, grade, top reasons.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_JSONL = BACKEND_DIR / "data" / "processed" / "scans.v3_combined.cleaned.jsonl"

# Recognizable sites to sanity-check (normalized_host or substring match)
KNOWN_STRONG = [
    "google.com",
    "instagram.com",
    "github.com",
    "wikipedia.org",
    "mozilla.org",
    "cloudflare.com",
]
KNOWN_WEAK = [
    "ucv.cl",
    "baja.hu",
    "jd.com",
    "reuters.com",
]


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


def _features_dict(row: dict) -> dict:
    features = row.get("features") or {}
    if hasattr(features, "model_dump"):
        features = features.model_dump()
    elif hasattr(features, "dict"):
        features = features.dict()
    return features


def main() -> int:
    path = DEFAULT_JSONL
    if not path.exists():
        path = BACKEND_DIR / "data" / path.name
    if not path.exists():
        print(f"Dataset not found: {DEFAULT_JSONL}", file=sys.stderr)
        return 1

    sys.path.insert(0, str(BACKEND_DIR))
    from services.scoring_v2 import compute_rule_score_v2

    rows = _load_jsonl(path)
    if not rows:
        print("No rows.", file=sys.stderr)
        return 1

    # Compute v2 for every row and attach
    by_host: dict[str, dict] = {}
    for r in rows:
        host = (r.get("normalized_host") or "").strip()
        if not host:
            continue
        features = _features_dict(r)
        v2 = compute_rule_score_v2(features, r.get("evidence"), include_debug=False)
        r["_v2_score"] = v2["rule_score_v2"]
        r["_v2_grade"] = v2["rule_grade_v2"]
        r["_v2_reasons"] = v2.get("rule_reasons_v2") or []
        by_host[host] = r

    # 1) Sanity-check known sites
    wanted = KNOWN_STRONG + KNOWN_WEAK
    print("=" * 60)
    print("1. SANITY-CHECK: Known sites (v3 vs v2)")
    print("=" * 60)
    for name in wanted:
        row = by_host.get(name)
        if not row:
            # try substring match
            row = next((by_host[h] for h in by_host if name in h or h.endswith("." + name)), None)
        if not row:
            print(f"\n  {name}: not in dataset")
            continue
        v3_score = row.get("rule_score")
        v3_grade = row.get("rule_grade") or "—"
        v2_score = row["_v2_score"]
        v2_grade = row["_v2_grade"]
        reasons = row["_v2_reasons"][:5]
        print(f"\n  {row.get('normalized_host', name)}")
        print(f"    rule_score_v3:  {v3_score}  |  rule_grade_v3:  {v3_grade}")
        print(f"    rule_score_v2:  {v2_score}  |  rule_grade_v2:  {v2_grade}")
        print(f"    top v2 reasons: {reasons[:3] if reasons else ['(none)']}")
        if len(reasons) > 3:
            for r in reasons[3:5]:
                print(f"                    {r}")

    # 2) Top 20 and bottom 20 by rule_score_v2
    sorted_rows = sorted(by_host.values(), key=lambda r: (r["_v2_score"], r.get("normalized_host") or ""), reverse=True)
    print("\n" + "=" * 60)
    print("2. TOP 20 by rule_score_v2")
    print("=" * 60)
    for r in sorted_rows[:20]:
        host = r.get("normalized_host", "?")
        score = r["_v2_score"]
        grade = r["_v2_grade"]
        reasons = (r.get("_v2_reasons") or [])[:2]
        reasons_str = "; ".join(reasons) if reasons else "(none)"
        print(f"  {score:5.1f}  {grade:2}  {host}")
        print(f"         {reasons_str}")

    print("\n" + "=" * 60)
    print("3. BOTTOM 20 by rule_score_v2")
    print("=" * 60)
    for r in sorted_rows[-20:]:
        host = r.get("normalized_host", "?")
        score = r["_v2_score"]
        grade = r["_v2_grade"]
        reasons = (r.get("_v2_reasons") or [])[:2]
        reasons_str = "; ".join(reasons) if reasons else "(none)"
        print(f"  {score:5.1f}  {grade:2}  {host}")
        print(f"         {reasons_str}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
