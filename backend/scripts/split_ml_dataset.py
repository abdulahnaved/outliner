#!/usr/bin/env python3
"""
Create stratified train/validation/test splits from an ML CSV.

Reads an ML dataset CSV (e.g. dataset_full.csv or dataset_reachable.csv),
splits by rule_label to preserve class balance, and writes train/val/test CSVs.

Outputs (when input is dataset_full.csv):
  data/ml/train_full.csv
  data/ml/val_full.csv
  data/ml/test_full.csv

When input is dataset_reachable.csv, outputs train_reachable.csv, val_reachable.csv, test_reachable.csv.
Splits are deterministic (fixed random_state) for reproducibility.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
ML_DIR = DATA_DIR / "ml"

# Default split ratios: train 70%, val 15%, test 15%.
DEFAULT_TRAIN_RATIO = 0.70
DEFAULT_VAL_RATIO = 0.15
RANDOM_STATE = 42


def load_csv(path: Path) -> tuple[list[dict], list[str]]:
    """Load CSV; return list of row dicts and fieldnames."""
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
    ap = argparse.ArgumentParser(description="Stratified train/val/test split of ML CSV")
    ap.add_argument("--input", type=Path, default=ML_DIR / "dataset_full.csv", help="Input ML CSV")
    ap.add_argument("--out-dir", type=Path, default=ML_DIR, help="Output directory")
    ap.add_argument("--train-ratio", type=float, default=DEFAULT_TRAIN_RATIO, help="Train fraction (0-1)")
    ap.add_argument("--val-ratio", type=float, default=DEFAULT_VAL_RATIO, help="Validation fraction (0-1)")
    ap.add_argument("--seed", type=int, default=RANDOM_STATE, help="Random seed for reproducibility")
    args = ap.parse_args()

    input_path = args.input.resolve()
    if not input_path.exists():
        alt = ML_DIR / input_path.name
        if alt.exists():
            input_path = alt
        else:
            print(f"Input not found: {args.input}", file=sys.stderr)
            return 1

    rows, fieldnames = load_csv(input_path)
    if not rows:
        print("No rows in input.", file=sys.stderr)
        return 1

    # Infer stem for output names: dataset_full -> full, dataset_reachable -> reachable
    stem = input_path.stem
    if stem.startswith("dataset_"):
        suffix = stem.replace("dataset_", "", 1)
    else:
        suffix = "split"

    # Stratified split requires sklearn.
    try:
        from sklearn.model_selection import train_test_split
    except ImportError:
        print("sklearn is required. Install with: pip install scikit-learn", file=sys.stderr)
        return 1

    labels = [r.get("rule_label") for r in rows]
    # Coerce to int for stratify (e.g. "0"/"1" from CSV).
    try:
        y = [int(x) if x is not None and str(x).strip() != "" else 0 for x in labels]
    except (ValueError, TypeError):
        y = [0] * len(rows)

    # First split: train vs (val+test).
    train_ratio = max(0.0, min(1.0, args.train_ratio))
    val_ratio = max(0.0, min(1.0, args.val_ratio))
    test_ratio = 1.0 - train_ratio - val_ratio
    if test_ratio < 0:
        test_ratio = 0.0
    val_plus_test_ratio = val_ratio + test_ratio
    if val_plus_test_ratio <= 0:
        val_plus_test_ratio = 1.0 - train_ratio

    train_rows, rest_rows, train_y, rest_y = train_test_split(
        rows, y, train_size=train_ratio, stratify=y, random_state=args.seed
    )
    if not rest_rows:
        val_rows, test_rows = [], []
    else:
        # Second split: val vs test (stratify within rest).
        val_frac = val_ratio / val_plus_test_ratio if val_plus_test_ratio > 0 else 0.5
        val_rows, test_rows, _, _ = train_test_split(
            rest_rows, rest_y, train_size=val_frac, stratify=rest_y, random_state=args.seed
        )
    args.out_dir.mkdir(parents=True, exist_ok=True)

    train_path = args.out_dir / f"train_{suffix}.csv"
    val_path = args.out_dir / f"val_{suffix}.csv"
    test_path = args.out_dir / f"test_{suffix}.csv"

    write_csv(train_path, train_rows, fieldnames)
    write_csv(val_path, val_rows, fieldnames)
    write_csv(test_path, test_rows, fieldnames)

    print(f"Train: {train_path} ({len(train_rows)} rows)", file=sys.stderr)
    print(f"Val:   {val_path} ({len(val_rows)} rows)", file=sys.stderr)
    print(f"Test:  {test_path} ({len(test_rows)} rows)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
