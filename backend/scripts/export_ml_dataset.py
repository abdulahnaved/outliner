#!/usr/bin/env python3
"""
Export ML-ready flat CSV from cleaned v3 combined JSONL.

Reads data/scans.v3_combined.cleaned.jsonl, flattens "features" into columns,
keeps normalized_host as metadata and rule_score/rule_label as targets.
Excludes evidence, URLs, timestamps, and legacy duplicate features (prefers v3 naming).
Handles missing values (tls_version, certificate_days_left) with indicators and
adds engineered columns: tls_version_missing, cert_days_missing, cert_expired, response_time_log.

Outputs:
  data/ml/dataset_full.csv       - all rows
  data/ml/dataset_reachable.csv  - is_blocked==0 and status_is_2xx==1 (configurable)
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
ML_DIR = DATA_DIR / "ml"
DEFAULT_INPUT = DATA_DIR / "scans.v3_combined.cleaned.jsonl"

# Legacy feature keys to drop when flattening (v3 equivalents kept).
# We keep: csp_has_default_src, csp_unsafe_inline, csp_unsafe_eval, hsts_max_age (int).
LEGACY_FEATURE_KEYS = frozenset({
    "csp_has_unsafe_inline",
    "csp_has_unsafe_eval",
    "csp_has_default_self",
    "csp_has_object_none",
    "hsts_max_age_days",
})

# Engineered features that can be excluded via --no-engineered.
ENGINEERED_FEATURE_KEYS = frozenset({"csp_score", "tls_version_score"})


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


def flatten_features(
    row: dict,
    include_engineered: bool = True,
) -> dict:
    """
    Build a flat dict for one row: metadata + flattened features + targets + derived columns.
    Excludes evidence, requested_url, final_url, scan_timestamp, and legacy feature keys.
    """
    features = row.get("features") or {}
    # Start with metadata and targets we keep for ML.
    flat = {
        "normalized_host": row.get("normalized_host", ""),
        "rule_score": row.get("rule_score"),
        "rule_label": row.get("rule_label"),
    }
    # For filtering we need is_blocked and status_is_2xx (from row top-level and features).
    flat["_is_blocked"] = row.get("is_blocked", 0)
    flat["_status_is_2xx"] = features.get("status_is_2xx", 0)

    # Flatten feature keys, skipping legacy duplicates and optionally engineered.
    for k, v in features.items():
        if k in LEGACY_FEATURE_KEYS:
            continue
        if not include_engineered and k in ENGINEERED_FEATURE_KEYS:
            continue
        flat[k] = v

    # Missing value handling and derived columns (apply after flattening).
    tls = flat.get("tls_version")
    if tls is None or (isinstance(tls, float) and math.isnan(tls)):
        flat["tls_version"] = 0
        flat["tls_version_missing"] = 1
    else:
        flat["tls_version_missing"] = 0

    cert_days = flat.get("certificate_days_left")
    if cert_days is None or (isinstance(cert_days, float) and math.isnan(cert_days)):
        flat["certificate_days_left"] = 0
        flat["cert_days_missing"] = 1
    else:
        flat["cert_days_missing"] = 0

    try:
        cert_days_val = float(flat["certificate_days_left"])
        flat["cert_expired"] = 1 if cert_days_val <= 0 else 0
    except (TypeError, ValueError):
        flat["cert_expired"] = 0

    rt = flat.get("response_time")
    try:
        rt_f = float(rt) if rt is not None else 0.0
        flat["response_time_log"] = math.log1p(max(0.0, rt_f))
    except (TypeError, ValueError):
        flat["response_time_log"] = 0.0

    return flat


def get_feature_column_order(flat_rows: list[dict]) -> list[str]:
    """
    Determine column order: metadata, then targets, then feature columns (excluding internal _).
    Assumes all rows have the same keys after flattening.
    """
    if not flat_rows:
        return []
    meta = ["normalized_host"]
    targets = ["rule_score", "rule_label"]
    internal = {"_is_blocked", "_status_is_2xx"}
    feature_keys = sorted(
        k for k in flat_rows[0].keys()
        if k not in meta and k not in targets and k not in internal
    )
    return meta + targets + feature_keys


def filter_reachable(flat_rows: list[dict]) -> list[dict]:
    """Return rows where is_blocked==0 and status_is_2xx==1."""
    return [
        r for r in flat_rows
        if r.get("_is_blocked", 1) == 0 and r.get("_status_is_2xx", 0) == 1
    ]


def write_csv(path: Path, flat_rows: list[dict], columns: list[str]) -> None:
    """Write flat rows to CSV; each row is a dict with keys matching columns (internal _ keys stripped for output)."""
    # Export columns: do not write _is_blocked, _status_is_2xx to CSV (they're filter-only).
    export_columns = [c for c in columns if not c.startswith("_")]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=export_columns, extrasaction="ignore")
        w.writeheader()
        for r in flat_rows:
            w.writerow(r)


def main() -> int:
    ap = argparse.ArgumentParser(description="Export ML-ready CSV from v3 combined cleaned JSONL")
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input JSONL path")
    ap.add_argument("--out-dir", type=Path, default=ML_DIR, help="Output directory for CSV files")
    ap.add_argument("--no-engineered", action="store_true", help="Exclude csp_score and tls_version_score from features")
    ap.add_argument("--no-reachable", action="store_true", help="Do not write dataset_reachable.csv")
    ap.add_argument(
        "--reachable-filter",
        type=str,
        default="is_blocked:0,status_is_2xx:1",
        help="Filter for reachable: is_blocked:0,status_is_2xx:1 (default). Unused if --no-reachable.",
    )
    args = ap.parse_args()

    input_path = args.input.resolve()
    if not input_path.exists():
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

    include_engineered = not args.no_engineered
    flat_rows = [flatten_features(r, include_engineered=include_engineered) for r in rows]
    columns = get_feature_column_order(flat_rows)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    # dataset_full.csv: all rows
    full_path = args.out_dir / "dataset_full.csv"
    write_csv(full_path, flat_rows, columns)
    print(f"Wrote {full_path} ({len(flat_rows)} rows)", file=sys.stderr)

    if not args.no_reachable:
        reachable = filter_reachable(flat_rows)
        reachable_path = args.out_dir / "dataset_reachable.csv"
        write_csv(reachable_path, reachable, columns)
        print(f"Wrote {reachable_path} ({len(reachable)} rows)", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
