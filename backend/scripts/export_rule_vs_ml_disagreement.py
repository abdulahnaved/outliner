#!/usr/bin/env python3
"""
Export disagreement analysis: rule baseline vs ML estimate across dataset rows.

This produces a thesis-friendly CSV with:
- normalized_host
- actual rule_score_v2 (baseline target)
- ML predicted score (from current artifacts)
- Δ (ML - Rule)

It supports later analysis of agreement/divergence patterns.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.ml_inference import _load_artifacts  # type: ignore


def main() -> int:
    ap = argparse.ArgumentParser(description="Export rule vs ML disagreement over a dataset CSV")
    ap.add_argument(
        "--input",
        type=Path,
        default=BACKEND_DIR / "data" / "ml" / "datasets" / "test_regression_full.csv",
        help="Input CSV with normalized_host, rule_score_v2 target, and feature columns",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=BACKEND_DIR / "data" / "ml" / "results" / "rule_vs_ml_disagreement.csv",
        help="Output CSV path",
    )
    args = ap.parse_args()

    input_path = args.input.resolve()
    if not input_path.exists():
        print(f"Input not found: {input_path}", file=sys.stderr)
        return 1

    import numpy as np

    model, feature_columns, _, _, _ = _load_artifacts()

    with open(input_path) as f:
        r = csv.DictReader(f)
        rows = list(r)

    out_rows: list[list] = []
    for row in rows:
        host = row.get("normalized_host", "")
        actual = row.get("rule_score_v2")
        try:
            y_true = float(actual) if actual not in (None, "") else 0.0
        except (ValueError, TypeError):
            y_true = 0.0

        vec: list[float] = []
        for col in feature_columns:
            v = row.get(col)
            if v is None or v == "":
                vec.append(0.0)
                continue
            try:
                vec.append(float(v))
            except (ValueError, TypeError):
                vec.append(0.0)

        X = np.asarray([vec], dtype=float)
        pred = float(model.predict(X)[0])
        delta = pred - y_true
        out_rows.append([host, y_true, pred, delta])

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["normalized_host", "rule_score_v2", "ml_predicted_score", "delta_ml_minus_rule"])
        w.writerows(out_rows)

    print(f"Wrote {args.out} ({len(out_rows)} rows)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

