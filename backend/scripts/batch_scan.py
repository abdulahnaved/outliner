#!/usr/bin/env python3
"""
Phase 3 batch scan: run POST /api/scan for each target.
Appends to scans.jsonl and scans.csv; records failures in failures.jsonl.
Passive-only; do not crawl. Default 1s delay between requests; use --delay 0 for fastest.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

# Default paths relative to backend/
BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_TARGETS = BACKEND_DIR / "data" / "targets.txt"
DEFAULT_JSONL = BACKEND_DIR / "data" / "scans.jsonl"
DEFAULT_CSV = BACKEND_DIR / "data" / "scans.csv"
DEFAULT_FAILURES = BACKEND_DIR / "data" / "failures.jsonl"


def load_targets(path: Path) -> list[str]:
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            out.append(line)
    return out


def load_existing_normalized_hosts(jsonl_path: Path) -> set[str]:
    hosts = set()
    if not jsonl_path.exists():
        return hosts
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                h = obj.get("normalized_host")
                if h:
                    hosts.add(h)
            except json.JSONDecodeError:
                continue
    return hosts


def normalize_target_for_resume(target: str) -> str | None:
    """Minimal host normalization to match backend; returns normalized_host or None."""
    from urllib.parse import urlparse
    s = (target or "").strip()
    if not s:
        return None
    if not s.lower().startswith(("http://", "https://")):
        s = "https://" + s
    try:
        p = urlparse(s)
        host = (p.hostname or "").lower()
        if not host:
            return None
        if host.startswith("www."):
            host = host[4:]
        return host if host else None
    except Exception:
        return None


def scan_one(
    client: httpx.Client,
    api_url: str,
    target: str,
) -> tuple[dict | None, str | None, int | None]:
    """POST /api/scan. Returns (response_json, error_message, status_code)."""
    url = f"{api_url.rstrip('/')}/api/scan"
    try:
        r = client.post(url, json={"target": target}, timeout=30.0)
        if r.status_code == 200:
            return r.json(), None, r.status_code
        return None, r.text or f"HTTP {r.status_code}", r.status_code
    except httpx.TimeoutException as e:
        return None, str(e), None
    except httpx.HTTPError as e:
        return None, str(e), None


# Canonical JSONL field order (single writer, one schema)
CANONICAL_KEYS = [
    "scan_timestamp", "input_target", "normalized_host", "requested_url",
    "final_url", "final_status_code", "timing_ms", "redirect_count",
    "response_time", "is_blocked", "features", "evidence",
]


def api_response_to_canonical(api_result: dict, scan_timestamp: str) -> dict:
    """Transform API ScanResult into canonical JSONL record. One writer, one schema."""
    code = api_result.get("final_status_code")
    is_blocked = 1 if code in (401, 403, 429) else 0
    features = api_result.get("features")
    evidence = api_result.get("evidence")
    if features is None:
        features = {}
    if evidence is None:
        evidence = {}
    # Normalize to dicts for JSON (in case of Pydantic models from JSON)
    if hasattr(features, "model_dump"):
        features = features.model_dump()
    elif hasattr(features, "dict"):
        features = features.dict()
    if hasattr(evidence, "model_dump"):
        evidence = evidence.model_dump()
    elif hasattr(evidence, "dict"):
        evidence = evidence.dict()
    record = {
        "scan_timestamp": scan_timestamp,
        "input_target": api_result.get("input_target", ""),
        "normalized_host": api_result.get("normalized_host", ""),
        "requested_url": api_result.get("requested_url", ""),
        "final_url": api_result.get("final_url") or "",
        "final_status_code": code,
        "timing_ms": api_result.get("timing_ms"),
        "redirect_count": int(api_result.get("redirect_count", 0)),
        "response_time": float(api_result.get("response_time", 0.0)),
        "is_blocked": is_blocked,
        "features": features,
        "evidence": evidence,
    }
    return {k: record[k] for k in CANONICAL_KEYS if k in record}


CSV_FIELDS = [
    "input_target", "normalized_host", "requested_url", "final_url",
    "final_status_code", "timing_ms", "redirect_count", "response_time",
    "is_blocked", "scan_timestamp",
    "feat_has_https", "feat_has_hsts", "feat_tls_version", "feat_certificate_days_left",
    "feat_redirect_count", "feat_response_time",
    "feat_has_csp", "feat_has_x_frame", "feat_has_x_content_type",
    "feat_csp_has_unsafe_inline", "feat_csp_has_unsafe_eval", "feat_csp_has_default_self", "feat_csp_has_object_none",
    "feat_hsts_max_age_days", "feat_hsts_include_subdomains", "feat_hsts_preload",
    "feat_has_referrer_policy", "feat_has_permissions_policy",
    "feat_server_header_present", "feat_x_powered_by_present",
    "feat_cookie_secure", "feat_cookie_httponly", "feat_cookie_samesite",
    "feat_total_cookie_count", "feat_secure_cookie_ratio", "feat_httponly_cookie_ratio", "feat_samesite_cookie_ratio",
    "feat_cors_wildcard",
    "feat_status_is_2xx", "feat_status_is_3xx", "feat_status_is_4xx", "feat_status_is_5xx",
]


def result_to_csv_row(obj: dict) -> dict:
    """Flatten canonical record (or API-like object) to one CSV row."""
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
    }
    feats = obj.get("features") or {}
    for k, v in feats.items():
        row[f"feat_{k}"] = v
    return row


def ensure_csv_header(csv_path: Path) -> None:
    """Write CSV header if file is new."""
    if csv_path.exists():
        return
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()


def append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(obj) + "\n")


def append_failure(path: Path, target: str, error: str, status_code: int | None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    obj = {
        "target": target,
        "error": error,
        "status_code": status_code,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(path, "a") as f:
        f.write(json.dumps(obj) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Batch scan targets via POST /api/scan")
    ap.add_argument("--api-url", default="http://localhost:8000", help="Base URL of API")
    ap.add_argument("--targets", type=Path, default=DEFAULT_TARGETS, help="Targets file (one per line)")
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_JSONL, help="Output JSONL path")
    ap.add_argument("--out-csv", type=Path, default=DEFAULT_CSV, help="Output CSV path")
    ap.add_argument("--failures", type=Path, default=DEFAULT_FAILURES, help="Failures JSONL path")
    ap.add_argument("--delay", type=float, default=1.0, help="Seconds between requests (default 1.0)")
    ap.add_argument("--limit", type=int, default=None, help="Scan only first N targets")
    ap.add_argument("--resume", action="store_true", help="Skip targets already in out-jsonl by normalized_host")
    ap.add_argument("--allow-repeat", action="store_true", help="With --resume, do not skip already-scanned hosts")
    ap.add_argument("--output-prefix", type=str, default=None, help="Write to scans.<prefix>.jsonl and scans.<prefix>.csv")
    args = ap.parse_args()

    if args.output_prefix:
        prefix = args.output_prefix.strip()
        data_dir = args.out_jsonl.parent
        args.out_jsonl = data_dir / f"scans.{prefix}.jsonl"
        args.out_csv = data_dir / f"scans.{prefix}.csv"
        args.failures = data_dir / f"failures.{prefix}.jsonl"

    if not args.targets.exists():
        print(f"Targets file not found: {args.targets}", file=sys.stderr)
        return 1

    targets = load_targets(args.targets)
    if args.limit is not None:
        targets = targets[: args.limit]

    skip_seen = args.resume and not args.allow_repeat
    if skip_seen and args.out_jsonl.exists():
        seen = load_existing_normalized_hosts(args.out_jsonl)
    else:
        seen = set()

    client = httpx.Client()
    done = 0
    failed = 0

    for i, target in enumerate(targets):
        if args.resume:
            host_key = normalize_target_for_resume(target)
            if host_key and host_key in seen:
                print(f"[skip] {target} (already have {host_key})")
                continue
        try:
            result, err, status_code = scan_one(client, args.api_url, target)
            if result is None and (status_code in (502, 504) or status_code is None):
                time.sleep(args.delay)
                result, err, status_code = scan_one(client, args.api_url, target)
            if result is not None:
                host = result.get("normalized_host")
                if skip_seen and host and host in seen:
                    print(f"[skip] {target} (duplicate {host})")
                    continue
                ts = datetime.now(timezone.utc).isoformat()
                canonical = api_response_to_canonical(result, ts)
                append_jsonl(args.out_jsonl, canonical)
                row = result_to_csv_row(canonical)
                ensure_csv_header(args.out_csv)
                with open(args.out_csv, "a", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
                    w.writerow(row)
                if host:
                    seen.add(host)
                done += 1
                print(f"[ok] {target} -> {host} ({result.get('final_status_code')})")
            else:
                append_failure(args.failures, target, err or "unknown", status_code)
                failed += 1
                print(f"[fail] {target} -> {err}", file=sys.stderr)
        except Exception as e:
            append_failure(args.failures, target, str(e), None)
            failed += 1
            print(f"[fail] {target} -> {e}", file=sys.stderr)

        if i < len(targets) - 1 and args.delay > 0:
            time.sleep(args.delay)

    client.close()
    print(f"Done: {done} ok, {failed} failed")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
