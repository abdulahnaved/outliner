#!/usr/bin/env python3
"""
Split a regression dataset CSV into train/validation/test with optional
score-based stratification (quantile bins) for similar score distribution.

Output naming: dataset_regression_full.csv -> train_regression_full.csv,
val_regression_full.csv, test_regression_full.csv; same for reachable.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
ML_DIR = DATA_DIR / "ml"

DEFAULT_TRAIN_RATIO = 0.70
DEFAULT_VAL_RATIO = 0.15
RANDOM_STATE = 42
N_QUANTILE_BINS = 5


def load_csv(path: Path) -> tuple[list[dict], list[str]]:
    with open(path) as f:
        r = csv.DictReader(f)
        fieldnames = list(r.fieldnames or [])
        rows = list(r)
    return rows, fieldnames


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description="Train/val/test split for regression CSV")
    ap.add_argument("--input", type=Path, default=ML_DIR / "datasets" / "dataset_regression_full.csv", help="Input regression CSV")
    ap.add_argument("--out-dir", type=Path, default=ML_DIR / "datasets", help="Output directory")
    ap.add_argument("--train-ratio", type=float, default=DEFAULT_TRAIN_RATIO, help="Train fraction")
    ap.add_argument("--val-ratio", type=float, default=DEFAULT_VAL_RATIO, help="Validation fraction")
    ap.add_argument("--seed", type=int, default=RANDOM_STATE, help="Random seed")
    ap.add_argument("--no-stratify", action="store_true", help="Use random split only (no quantile stratification)")
    args = ap.parse_args()

    input_path = args.input.resolve()
    if not input_path.exists():
        # Fallback to legacy layout without datasets/ subdir
        alt = ML_DIR / input_path.name
        if alt.exists():
            input_path = alt
        else:
            print(f"Input not found: {args.input}", file=sys.stderr)
            return 1

    rows, fieldnames = load_csv(input_path)
    if not rows:
        print("No rows.", file=sys.stderr)
        return 1

    try:
        import numpy as np
        from sklearn.model_selection import train_test_split
    except ImportError:
        print("scikit-learn required for split.", file=sys.stderr)
        return 1

    # Infer suffix: dataset_regression_full -> full, dataset_regression_reachable -> reachable
    stem = input_path.stem
    if stem.startswith("dataset_regression_"):
        suffix = stem.replace("dataset_regression_", "", 1)
    else:
        suffix = "split"

    def score_bin(r: dict) -> int:
        try:
            s = float(r.get("rule_score", 0) or 0)
            return min(N_QUANTILE_BINS - 1, max(0, int(s / 20)))  # 0-20, 20-40, ..., 80-100
        except (TypeError, ValueError):
            return 0

    if args.no_stratify:
        stratify = None
    else:
        # Quantile-like bins for approximate stratification
        bins = [score_bin(r) for r in rows]
        stratify = np.asarray(bins)

    train_ratio = max(0.0, min(1.0, args.train_ratio))
    val_ratio = max(0.0, min(1.0, args.val_ratio))
    test_ratio = 1.0 - train_ratio - val_ratio
    if test_ratio < 0:
        test_ratio = 0.0
    rest_ratio = val_ratio + test_ratio
    if rest_ratio <= 0:
        rest_ratio = 1.0 - train_ratio

    train_rows, rest_rows = train_test_split(
        rows, train_size=train_ratio, stratify=stratify, random_state=args.seed
    )

    if not rest_rows:
        val_rows, test_rows = [], []
    else:
        val_frac = val_ratio / rest_ratio if rest_ratio > 0 else 0.5
        rest_bins = None if args.no_stratify else np.array([score_bin(r) for r in rest_rows])
        val_rows, test_rows = train_test_split(
            rest_rows, train_size=val_frac, stratify=rest_bins, random_state=args.seed
        )

    args.out_dir.mkdir(parents=True, exist_ok=True)

    train_path = args.out_dir / f"train_regression_{suffix}.csv"
    val_path = args.out_dir / f"val_regression_{suffix}.csv"
    test_path = args.out_dir / f"test_regression_{suffix}.csv"

    write_csv(train_path, train_rows, fieldnames)
    write_csv(val_path, val_rows, fieldnames)
    write_csv(test_path, test_rows, fieldnames)

    print(f"Train: {train_path} ({len(train_rows)})", file=sys.stderr)
    print(f"Val:   {val_path} ({len(val_rows)})", file=sys.stderr)
    print(f"Test:  {test_path} ({len(test_rows)})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
