#!/usr/bin/env python3
"""
Print distribution summary for scans JSONL (default: scans.cleaned.jsonl if exists, else scans.jsonl).
Dependency-light: stdlib + statistics.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CLEANED = BACKEND_DIR / "data" / "scans.cleaned.jsonl"
DEFAULT_JSONL = BACKEND_DIR / "data" / "scans.jsonl"


def pct(n: int, total: int) -> str:
    if total == 0:
        return "0.0%"
    return f"{100.0 * n / total:.1f}%"


def _resolve(path: Path) -> Path:
    p = path.resolve()
    if not p.exists() and p.name:
        alt = BACKEND_DIR / "data" / p.name
        if alt.exists():
            return alt
    return p


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


def main() -> int:
    ap = argparse.ArgumentParser(description="Summarize scan dataset distribution (supports multiple files = combined)")
    ap.add_argument("--input", type=Path, nargs="*", default=None, help="One or more JSONL paths; multiple = merge for combined stats")
    args = ap.parse_args()

    paths: list[Path] = []
    if args.input is None or len(args.input) == 0:
        path = DEFAULT_CLEANED if DEFAULT_CLEANED.exists() else DEFAULT_JSONL
        paths = [path]
    else:
        for p in args.input:
            p = _resolve(p)
            if not p.exists():
                print(f"File not found: {p}", file=sys.stderr)
                return 1
            paths.append(p)

    rows: list[dict] = []
    for path in paths:
        rows.extend(_load_jsonl(path))

    total = len(rows)
    hosts = {r.get("normalized_host") or "" for r in rows if r.get("normalized_host")}
    unique_hosts = len(hosts) - (1 if "" in hosts else 0)

    blocked = sum(1 for r in rows if r.get("is_blocked") == 1)
    feats = [r.get("features") or {} for r in rows]
    has_https = sum(1 for f in feats if f.get("has_https") == 1)
    has_hsts = sum(1 for f in feats if f.get("has_hsts") == 1)
    has_csp = sum(1 for f in feats if f.get("has_csp") == 1)
    has_x_frame = sum(1 for f in feats if f.get("has_x_frame") == 1)
    has_x_content = sum(1 for f in feats if f.get("has_x_content_type") == 1)
    cookie_secure = sum(1 for f in feats if f.get("cookie_secure") == 1)
    cookie_httponly = sum(1 for f in feats if f.get("cookie_httponly") == 1)
    cookie_samesite = sum(1 for f in feats if f.get("cookie_samesite") == 1)
    cors_wildcard = sum(1 for f in feats if f.get("cors_wildcard") == 1)
    status_2xx = sum(1 for f in feats if f.get("status_is_2xx") == 1)
    status_4xx = sum(1 for f in feats if f.get("status_is_4xx") == 1)
    status_5xx = sum(1 for f in feats if f.get("status_is_5xx") == 1)
    server_present = sum(1 for f in feats if f.get("server_header_present") == 1)
    referrer_policy = sum(1 for f in feats if f.get("has_referrer_policy") == 1)

    tls_versions: dict[str | float | None, int] = {}
    for f in feats:
        v = f.get("tls_version")
        key = v if v is not None else "null"
        tls_versions[key] = tls_versions.get(key, 0) + 1

    cert_days = [f.get("certificate_days_left") for f in feats if f.get("certificate_days_left") is not None]
    cert_days = [int(x) for x in cert_days if x is not None]
    resp_times = [r.get("response_time") for r in rows if r.get("response_time") is not None]
    resp_times = [float(x) for x in resp_times if x is not None]

    print("=== Dataset summary ===")
    print(f"Input: {paths[0].name}" if len(paths) == 1 else f"Input (combined): {', '.join(p.name for p in paths)}")
    print(f"Total rows: {total}")
    print(f"Unique normalized_host: {unique_hosts}")
    print()
    print("--- Blocking / HTTPS ---")
    print(f"% is_blocked: {pct(blocked, total)}")
    print(f"% has_https: {pct(has_https, total)}")
    print()
    print("--- Headers ---")
    print(f"% has_hsts: {pct(has_hsts, total)}")
    print(f"% has_csp: {pct(has_csp, total)}")
    print(f"% has_x_frame: {pct(has_x_frame, total)}")
    print(f"% has_x_content_type: {pct(has_x_content, total)}")
    print(f"% has_referrer_policy: {pct(referrer_policy, total)}")
    print(f"% server_header_present: {pct(server_present, total)}")
    print()
    print("--- Cookies ---")
    print(f"% cookie_secure: {pct(cookie_secure, total)}")
    print(f"% cookie_httponly: {pct(cookie_httponly, total)}")
    print(f"% cookie_samesite: {pct(cookie_samesite, total)}")
    print()
    print("--- CORS / TLS ---")
    print(f"% cors_wildcard: {pct(cors_wildcard, total)}")
    print("tls_version distribution:", dict(sorted(tls_versions.items(), key=lambda x: (x[0] == "null", str(x[0])))))
    print()
    print("--- Status buckets ---")
    print(f"% status_is_2xx: {pct(status_2xx, total)}")
    print(f"% status_is_4xx: {pct(status_4xx, total)}")
    print(f"% status_is_5xx: {pct(status_5xx, total)}")
    print()
    print("--- Certificate & timing ---")
    if cert_days:
        print(f"certificate_days_left: min={min(cert_days)}, median={statistics.median(cert_days):.0f}, max={max(cert_days)}")
    else:
        print("certificate_days_left: (no data)")
    if resp_times:
        print(f"response_time: min={min(resp_times):.4f}, median={statistics.median(resp_times):.4f}, max={max(resp_times):.4f}")
    else:
        print("response_time: (no data)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
