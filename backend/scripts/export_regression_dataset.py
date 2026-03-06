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
import math
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
ML_DIR = DATA_DIR / "ml"
DEFAULT_INPUT = DATA_DIR / "scans.v3_combined.cleaned.jsonl"

# Regression-safe feature keys only (raw security posture; no scoring proxies or labels).
# One canonical name per concept; legacy aliases excluded.
REGRESSION_SAFE_FEATURES = [
    "has_https",
    "redirect_http_to_https",
    "has_hsts",
    "tls_version",
    "weak_tls",
    "certificate_days_left",
    "redirect_count",
    "response_time",
    "has_csp",
    "csp_has_default_src",
    "csp_unsafe_inline",
    "csp_unsafe_eval",
    "csp_has_wildcard",
    "csp_has_object_none",
    "hsts_max_age",
    "hsts_long",
    "hsts_include_subdomains",
    "hsts_preload",
    "has_referrer_policy",
    "referrer_policy_strict",
    "has_permissions_policy",
    "has_coop",
    "has_coep",
    "has_corp",
    "server_header_present",
    "x_powered_by_present",
    "cookie_secure",
    "cookie_httponly",
    "cookie_samesite",
    "total_cookie_count",
    "secure_cookie_ratio",
    "httponly_cookie_ratio",
    "samesite_cookie_ratio",
    "cors_wildcard",
    "cors_allows_credentials",
    "cors_wildcard_with_credentials",
    "status_is_2xx",
    "status_is_3xx",
    "status_is_4xx",
    "status_is_5xx",
]

# Legacy/duplicate keys in source features that we do NOT use (canonical above used instead).
EXCLUDED_FEATURE_ALIASES = frozenset({
    "csp_has_unsafe_inline",
    "csp_has_unsafe_eval",
    "csp_has_default_self",
    "hsts_max_age_days",
    "final_status_code",  # use status_is_2xx/3xx/4xx/5xx only
})

# Excluded entirely (scoring proxies or labels).
EXCLUDED_LEAKAGE = frozenset({
    "rule_score",
    "rule_label",
    "rule_grade",
    "rule_reasons",
    "csp_score",
    "tls_version_score",
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


def get_canonical_value(features: dict, key: str):
    """Return value for canonical key; support legacy alias where source uses old name."""
    v = features.get(key)
    if v is not None:
        return v
    if key == "csp_has_default_src":
        return features.get("csp_has_default_self")
    return None


def flatten_row(row: dict) -> dict:
    """Build one flat row: normalized_host, rule_score (target), is_blocked, then regression-safe features + derived."""
    features = row.get("features") or {}
    flat = {
        "normalized_host": row.get("normalized_host", ""),
        "rule_score": row.get("rule_score"),
        "is_blocked": row.get("is_blocked", 0),
    }
    for key in REGRESSION_SAFE_FEATURES:
        v = get_canonical_value(features, key)
        if v is None:
            v = features.get(key)
        if v is None or (isinstance(v, float) and math.isnan(v)):
            v = 0
        flat[key] = v

    # Derived / missing-value handling
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
        flat["cert_expired"] = 1 if float(flat["certificate_days_left"]) <= 0 else 0
    except (TypeError, ValueError):
        flat["cert_expired"] = 0

    rt = flat.get("response_time")
    try:
        rt_f = float(rt) if rt is not None else 0.0
        flat["response_time_log"] = math.log1p(max(0.0, rt_f))
    except (TypeError, ValueError):
        flat["response_time_log"] = 0.0

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
