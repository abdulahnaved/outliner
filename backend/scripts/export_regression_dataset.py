#!/usr/bin/env python3
"""
Export regression ML datasets from the canonical cleaned JSONL.

Reads data/scans.v3_combined.cleaned.jsonl and exports leakage-safe flat CSVs
for predicting rule_score from raw passive security features only.

Leakage prevention: excludes rule_score, rule_label, rule_grade, rule_reasons,
metadata, evidence, and derived scoring proxies (csp_score, tls_version_score).
Uses a single canonical name per concept (no legacy duplicates).

Outputs:
  data/ml/dataset_regression_full.csv
  data/ml/dataset_regression_reachable.csv
  data/ml/regression_feature_schema.json
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
from services.ml_features import build_feature_row  # noqa: E402

DATA_DIR = BACKEND_DIR / "data"
ML_DIR = DATA_DIR / "ml"
DEFAULT_INPUT = DATA_DIR / "processed" / "scans.v3_combined.cleaned.jsonl"

# Excluded entirely (scoring proxies or labels); for schema doc only.
EXCLUDED_LEAKAGE = frozenset({
    "rule_score",
    "rule_label",
    "rule_grade",
    "rule_reasons",
    "csp_score",
    "tls_version_score",
})
EXCLUDED_FEATURE_ALIASES = frozenset({
    "csp_has_unsafe_inline",
    "csp_has_unsafe_eval",
    "csp_has_default_self",
    "hsts_max_age_days",
    "final_status_code",
})


def load_jsonl(path: Path) -> list[dict]:
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


def flatten_row(row: dict) -> dict:
    """Build one flat row: normalized_host, rule_score (target), is_blocked, then features from shared ml_features."""
    flat = {
        "normalized_host": row.get("normalized_host", ""),
        "rule_score": row.get("rule_score"),
        "is_blocked": row.get("is_blocked", 0),
    }
    flat.update(build_feature_row(row))
    return flat


def get_export_columns(flat_rows: list[dict]) -> list[str]:
    """Column order: metadata, target, then feature columns (including derived)."""
    if not flat_rows:
        return []
    meta_target = ["normalized_host", "rule_score", "is_blocked"]
    rest = sorted(k for k in flat_rows[0].keys() if k not in meta_target)
    return meta_target + rest


def filter_reachable(flat_rows: list[dict]) -> list[dict]:
    """Rows with is_blocked==0 and status_is_2xx==1."""
    return [
        r for r in flat_rows
        if r.get("is_blocked", 1) == 0 and r.get("status_is_2xx", 0) == 1
    ]


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def build_schema(export_columns: list[str]) -> dict:
    return {
        "target_column": "rule_score",
        "metadata_columns": ["normalized_host", "is_blocked"],
        "included_feature_columns": [c for c in export_columns if c not in ("normalized_host", "rule_score", "is_blocked")],
        "excluded_columns": {
            "labels_and_proxies": list(EXCLUDED_LEAKAGE),
            "legacy_aliases": list(EXCLUDED_FEATURE_ALIASES),
            "metadata_and_evidence": [
                "scan_timestamp", "input_target", "requested_url", "final_url",
                "evidence", "rule_grade", "rule_label", "rule_reasons",
            ],
        },
        "missing_value_handling": {
            "tls_version": "set to 0, add tls_version_missing=1",
            "certificate_days_left": "set to 0, add cert_days_missing=1",
            "cert_expired": "1 if certificate_days_left <= 0 else 0",
            "response_time_log": "log1p(response_time)",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Export regression datasets from v3 combined cleaned JSONL")
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input JSONL")
    ap.add_argument("--out-dir", type=Path, default=ML_DIR, help="Output directory")
    ap.add_argument("--no-reachable", action="store_true", help="Do not write reachable subset")
    args = ap.parse_args()

    input_path = args.input.resolve()
    if not input_path.exists():
        # Fallback to legacy location (before data/processed/ reorg)
        alt = DATA_DIR / input_path.name
        if alt.exists():
            input_path = alt
        else:
            print(f"Input not found: {args.input}", file=sys.stderr)
            return 1

    rows = load_jsonl(input_path)
    if not rows:
        print("No rows loaded.", file=sys.stderr)
        return 1

    flat_rows = [flatten_row(r) for r in rows]
    columns = get_export_columns(flat_rows)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    full_path = args.out_dir / "dataset_regression_full.csv"
    write_csv(full_path, flat_rows, columns)
    print(f"Wrote {full_path} ({len(flat_rows)} rows)", file=sys.stderr)

    if not args.no_reachable:
        reachable = filter_reachable(flat_rows)
        reachable_path = args.out_dir / "dataset_regression_reachable.csv"
        write_csv(reachable_path, reachable, columns)
        print(f"Wrote {reachable_path} ({len(reachable)} rows)", file=sys.stderr)

    schema_path = args.out_dir / "regression_feature_schema.json"
    schema = build_schema(columns)
    with open(schema_path, "w") as f:
        json.dump(schema, f, indent=2)
    print(f"Wrote {schema_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
