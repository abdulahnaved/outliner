#!/usr/bin/env python3
"""
Add rule_score_v2, rule_grade_v2, rule_label_v2, rule_reasons_v2 to the canonical
processed JSONL (in-place or to a given output path). Uses existing features only.
"""
from __future__ import annotations

import argparse
import json
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


def _features_dict(row: dict) -> dict:
    features = row.get("features") or {}
    if hasattr(features, "model_dump"):
        features = features.model_dump()
    elif hasattr(features, "dict"):
        features = features.dict()
    return features


def main() -> int:
    ap = argparse.ArgumentParser(description="Enrich canonical JSONL with scoring v2 fields")
    ap.add_argument("--input", type=Path, default=DEFAULT_JSONL, help="Input canonical JSONL")
    ap.add_argument("--out", type=Path, default=None, help="Output path (default: overwrite input)")
    args = ap.parse_args()

    path = args.input.resolve()
    if not path.exists():
        alt = BACKEND_DIR / "data" / "processed" / path.name
        if alt.exists():
            path = alt
        else:
            print(f"Not found: {args.input}", file=sys.stderr)
            return 1

    sys.path.insert(0, str(BACKEND_DIR))
    from services.scoring_v2 import compute_rule_score_v2

    rows = _load_jsonl(path)
    if not rows:
        print("No rows.", file=sys.stderr)
        return 1

    for r in rows:
        features = _features_dict(r)
        v2 = compute_rule_score_v2(features, r.get("evidence"), include_debug=False)
        r["rule_score_v2"] = v2["rule_score_v2"]
        r["rule_grade_v2"] = v2["rule_grade_v2"]
        r["rule_label_v2"] = v2["rule_label_v2"]
        r["rule_reasons_v2"] = v2.get("rule_reasons_v2") or []

    out_path = args.out.resolve() if args.out else path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"Wrote {len(rows)} rows to {out_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
