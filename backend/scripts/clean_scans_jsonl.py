#!/usr/bin/env python3
"""
One-time utility: read scans.jsonl, normalize to canonical schema, deduplicate,
write scans.cleaned.jsonl and optionally scans.cleaned.csv. Does not delete originals.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_JSONL = BACKEND_DIR / "data" / "scans.jsonl"
DEFAULT_CLEANED_JSONL = BACKEND_DIR / "data" / "scans.cleaned.jsonl"
DEFAULT_CLEANED_CSV = BACKEND_DIR / "data" / "scans.cleaned.csv"

CANONICAL_KEYS = [
    "scan_timestamp", "input_target", "normalized_host", "requested_url",
    "final_url", "final_status_code", "timing_ms", "redirect_count",
    "response_time", "is_blocked", "features", "evidence",
    "rule_score", "rule_grade", "rule_label", "rule_reasons",
]

CSV_FIELDS = [
    "input_target", "normalized_host", "requested_url", "final_url",
    "final_status_code", "timing_ms", "redirect_count", "response_time",
    "is_blocked", "scan_timestamp",
    "rule_score", "rule_grade", "rule_label",
    "feat_has_https", "feat_redirect_http_to_https", "feat_has_hsts", "feat_tls_version", "feat_tls_version_score", "feat_weak_tls",
    "feat_certificate_days_left", "feat_redirect_count", "feat_final_status_code", "feat_response_time",
    "feat_has_csp", "feat_has_x_frame", "feat_has_x_content_type",
    "feat_csp_has_default_src", "feat_csp_unsafe_inline", "feat_csp_unsafe_eval", "feat_csp_has_wildcard", "feat_csp_score",
    "feat_hsts_max_age", "feat_hsts_long", "feat_hsts_include_subdomains", "feat_hsts_preload",
    "feat_has_referrer_policy", "feat_referrer_policy_strict", "feat_has_permissions_policy",
    "feat_has_coop", "feat_has_coep", "feat_has_corp",
    "feat_server_header_present", "feat_x_powered_by_present",
    "feat_cookie_secure", "feat_cookie_httponly", "feat_cookie_samesite",
    "feat_total_cookie_count", "feat_secure_cookie_ratio", "feat_httponly_cookie_ratio", "feat_samesite_cookie_ratio",
    "feat_cors_wildcard", "feat_cors_allows_credentials", "feat_cors_wildcard_with_credentials",
    "feat_status_is_2xx", "feat_status_is_3xx", "feat_status_is_4xx", "feat_status_is_5xx",
]


def normalize_record(raw: dict) -> dict | None:
    """Normalize a raw JSONL object to canonical schema. Returns None if too broken."""
    code = raw.get("final_status_code")
    is_blocked = 1 if code in (401, 403, 429) else 0
    features = raw.get("features")
    evidence = raw.get("evidence")
    if features is None:
        features = {}
    if evidence is None:
        evidence = {}
    if isinstance(features, dict):
        pass
    elif hasattr(features, "model_dump"):
        features = features.model_dump()
    elif hasattr(features, "dict"):
        features = features.dict()
    else:
        features = {}
    if isinstance(evidence, dict):
        pass
    elif hasattr(evidence, "model_dump"):
        evidence = evidence.model_dump()
    elif hasattr(evidence, "dict"):
        evidence = evidence.dict()
    else:
        evidence = {}

    rule_reasons = raw.get("rule_reasons")
    if not isinstance(rule_reasons, list):
        rule_reasons = []
    record = {
        "scan_timestamp": raw.get("scan_timestamp") or "",
        "input_target": raw.get("input_target", ""),
        "normalized_host": raw.get("normalized_host", ""),
        "requested_url": raw.get("requested_url", ""),
        "final_url": raw.get("final_url") or "",
        "final_status_code": code,
        "timing_ms": raw.get("timing_ms"),
        "redirect_count": int(raw.get("redirect_count", 0)),
        "response_time": float(raw.get("response_time", 0.0)),
        "is_blocked": raw.get("is_blocked", is_blocked),
        "features": features,
        "evidence": evidence,
        "rule_score": float(raw.get("rule_score", 0.0)),
        "rule_grade": raw.get("rule_grade", "F"),
        "rule_label": int(raw.get("rule_label", 1)),
        "rule_reasons": rule_reasons,
    }
    return {k: record[k] for k in CANONICAL_KEYS}


def dedupe_key(r: dict) -> tuple:
    return (
        r.get("normalized_host") or "",
        r.get("requested_url") or "",
        r.get("final_url") or "",
        r.get("final_status_code"),
        r.get("redirect_count", 0),
        r.get("timing_ms"),
    )


def record_to_csv_row(obj: dict) -> dict:
    row = {
        "input_target": obj.get("input_target", ""),
        "normalized_host": obj.get("normalized_host", ""),
        "requested_url": obj.get("requested_url", ""),
        "final_url": obj.get("final_url") or "",
        "final_status_code": obj.get("final_status_code"),
        "timing_ms": obj.get("timing_ms"),
        "redirect_count": obj.get("redirect_count", 0),
        "response_time": obj.get("response_time", 0),
        "is_blocked": obj.get("is_blocked", 0),
        "scan_timestamp": obj.get("scan_timestamp", ""),
        "rule_score": obj.get("rule_score", 0.0),
        "rule_grade": obj.get("rule_grade", "F"),
        "rule_label": obj.get("rule_label", 1),
    }
    for k, v in (obj.get("features") or {}).items():
        row[f"feat_{k}"] = v
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description="Normalize and deduplicate scans.jsonl")
    ap.add_argument("--input", type=Path, default=DEFAULT_JSONL, help="Input JSONL (from backend/: use data/scans.PREFIX.jsonl)")
    ap.add_argument("--out-jsonl", type=Path, default=None, help="Output cleaned JSONL (default: derived from input, e.g. scans.PREFIX.cleaned.jsonl)")
    ap.add_argument("--out-csv", type=Path, default=None, help="Output CSV (default: same stem as out-jsonl with .csv)")
    ap.add_argument("--no-csv", action="store_true", help="Do not write CSV")
    args = ap.parse_args()

    args.input = args.input.resolve()
    if not args.input.exists():
        alt = BACKEND_DIR / "data" / args.input.name
        if alt.exists():
            args.input = alt.resolve()
        else:
            print(f"Input not found: {args.input}", file=sys.stderr)
            print("From backend/ use: data/scans.PREFIX.jsonl (e.g. data/scans.v1_fixed_redirect.jsonl)", file=sys.stderr)
            return 1

    if args.out_jsonl is None:
        stem = args.input.stem
        if stem.startswith("scans.") and stem != "scans":
            args.out_jsonl = args.input.parent / f"{stem}.cleaned.jsonl"
        else:
            args.out_jsonl = args.input.parent / "scans.cleaned.jsonl"
    else:
        args.out_jsonl = args.out_jsonl.resolve()

    records: list[dict] = []
    skipped = 0
    with open(args.input) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"Warning: skip line {i}: invalid JSON - {e}", file=sys.stderr)
                skipped += 1
                continue
            rec = normalize_record(raw)
            if rec is None:
                print(f"Warning: skip line {i}: could not normalize", file=sys.stderr)
                skipped += 1
                continue
            records.append(rec)

    # Deduplicate: keep earliest scan_timestamp per (normalized_host, requested_url, final_url, final_status_code, redirect_count, timing_ms)
    seen: dict[tuple, dict] = {}
    for r in records:
        key = dedupe_key(r)
        ts = r.get("scan_timestamp") or ""
        if key not in seen or (ts and seen[key].get("scan_timestamp", "z") > ts):
            seen[key] = r
    unique = list(seen.values())
    unique.sort(key=lambda r: (r.get("scan_timestamp") or ""))

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out_jsonl, "w") as f:
        for r in unique:
            f.write(json.dumps(r) + "\n")

    print(f"Read {len(records)} records, skipped {skipped} invalid, deduplicated to {len(unique)}", file=sys.stderr)

    if not args.no_csv:
        out_csv = args.out_csv or args.out_jsonl.with_suffix(".csv")
        with open(out_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
            w.writeheader()
            for r in unique:
                w.writerow(record_to_csv_row(r))
        print(f"Wrote {out_csv}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
