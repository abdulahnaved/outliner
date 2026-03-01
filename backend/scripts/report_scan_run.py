#!/usr/bin/env python3
"""
Report for a single scan run: success distribution + failure analysis.
Does not combine with any other dataset. Use --scans and --failures for one run.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"


def pct(n: int, total: int) -> str:
    if total == 0:
        return "0.0%"
    return f"{100.0 * n / total:.1f}%"


def _resolve(path: Path) -> Path:
    p = path.resolve()
    if not p.exists() and p.name:
        alt = DATA_DIR / p.name
        if alt.exists():
            return alt
    return p


def load_scans(path: Path) -> list[dict]:
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


def load_failures(path: Path) -> list[dict]:
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


def summarize_success(rows: list[dict], lines: list[str]) -> None:
    if not rows:
        lines.append("(no successful scans)")
        return
    total = len(rows)
    feats = [r.get("features") or {} for r in rows]
    hosts = {r.get("normalized_host") or "" for r in rows if r.get("normalized_host")}
    unique_hosts = len(hosts) - (1 if "" in hosts else 0)
    blocked = sum(1 for r in rows if r.get("is_blocked") == 1)
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
    cert_days = [int(x) for x in [f.get("certificate_days_left") for f in feats] if x is not None]
    resp_times = [float(x) for x in [r.get("response_time") for r in rows] if x is not None]

    lines.append(f"Total successful scans: {total}")
    lines.append(f"Unique normalized_host: {unique_hosts}")
    lines.append("")
    lines.append("--- Blocking / HTTPS ---")
    lines.append(f"% is_blocked: {pct(blocked, total)}")
    lines.append(f"% has_https: {pct(has_https, total)}")
    lines.append("")
    lines.append("--- Headers ---")
    lines.append(f"% has_hsts: {pct(has_hsts, total)}")
    lines.append(f"% has_csp: {pct(has_csp, total)}")
    lines.append(f"% has_x_frame: {pct(has_x_frame, total)}")
    lines.append(f"% has_x_content_type: {pct(has_x_content, total)}")
    lines.append(f"% has_referrer_policy: {pct(referrer_policy, total)}")
    lines.append(f"% server_header_present: {pct(server_present, total)}")
    lines.append("")
    lines.append("--- Cookies ---")
    lines.append(f"% cookie_secure: {pct(cookie_secure, total)}")
    lines.append(f"% cookie_httponly: {pct(cookie_httponly, total)}")
    lines.append(f"% cookie_samesite: {pct(cookie_samesite, total)}")
    lines.append("")
    lines.append("--- CORS / TLS ---")
    lines.append(f"% cors_wildcard: {pct(cors_wildcard, total)}")
    lines.append("tls_version distribution: " + str(dict(sorted(tls_versions.items(), key=lambda x: (x[0] == "null", str(x[0]))))))
    lines.append("")
    lines.append("--- Status buckets ---")
    lines.append(f"% status_is_2xx: {pct(status_2xx, total)}")
    lines.append(f"% status_is_4xx: {pct(status_4xx, total)}")
    lines.append(f"% status_is_5xx: {pct(status_5xx, total)}")
    lines.append("")
    lines.append("--- Certificate & timing ---")
    if cert_days:
        lines.append(f"certificate_days_left: min={min(cert_days)}, median={statistics.median(cert_days):.0f}, max={max(cert_days)}")
    else:
        lines.append("certificate_days_left: (no data)")
    if resp_times:
        lines.append(f"response_time: min={min(resp_times):.4f}, median={statistics.median(resp_times):.4f}, max={max(resp_times):.4f}")
    else:
        lines.append("response_time: (no data)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Report for one scan run (success + failures)")
    ap.add_argument("--scans", type=Path, required=True, help="Scans JSONL (e.g. data/scans.v2_extra.cleaned.jsonl)")
    ap.add_argument("--failures", type=Path, default=None, help="Failures JSONL for this run (e.g. data/failures.v2_extra.jsonl)")
    ap.add_argument("--out", type=Path, default=None, help="Write report to file (default: print only)")
    ap.add_argument("--name", type=str, default="Scan run", help="Report title (e.g. v2_extra)")
    args = ap.parse_args()

    scans_path = _resolve(args.scans)
    if not scans_path.exists():
        print(f"Scans file not found: {scans_path}", file=sys.stderr)
        return 1

    scans = load_scans(scans_path)
    failures = []
    if args.failures:
        fail_path = _resolve(args.failures)
        if fail_path.exists():
            failures = load_failures(fail_path)

    total_attempted = len(scans) + len(failures)
    success_rate = pct(len(scans), total_attempted) if total_attempted else "0.0%"

    lines = []
    lines.append("=" * 60)
    lines.append(f"  {args.name}")
    lines.append("=" * 60)
    lines.append("")
    lines.append("--- Run overview ---")
    lines.append(f"Scans file: {scans_path.name}")
    lines.append(f"Failures file: {args.failures.name if args.failures else 'none'}")
    lines.append(f"Total attempted: {total_attempted}")
    lines.append(f"Succeeded: {len(scans)}")
    lines.append(f"Failed: {len(failures)}")
    lines.append(f"Success rate: {success_rate}")
    lines.append("")

    lines.append("--- Successful scans (feature distribution) ---")
    lines.append("")
    summarize_success(scans, lines)

    if failures:
        lines.append("")
        lines.append("=" * 60)
        lines.append("  Failures")
        lines.append("=" * 60)
        lines.append("")
        by_status: dict[str, int] = defaultdict(int)
        by_error: dict[str, int] = defaultdict(int)
        for r in failures:
            sc = r.get("status_code")
            if sc is not None:
                by_status[str(sc)] += 1
            else:
                by_status["(no status)"] += 1
            err = (r.get("error") or "").strip()
            if len(err) > 60:
                err = err[:57] + "..."
            by_error[err or "(empty)"] += 1
        lines.append(f"Total failures: {len(failures)}")
        lines.append("")
        lines.append("By status code:")
        for k, v in sorted(by_status.items(), key=lambda x: -x[1]):
            lines.append(f"  {k}: {v}")
        lines.append("")
        lines.append("By error (top 15):")
        for err, count in sorted(by_error.items(), key=lambda x: -x[1])[:15]:
            lines.append(f"  {count}: {err}")
        lines.append("")
        lines.append("Failed targets (all):")
        for r in failures:
            lines.append(f"  {r.get('target', '?')}")

    report = "\n".join(lines)
    if args.out:
        out_path = args.out.resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            f.write(report)
        print(f"Report written to {out_path}", file=sys.stderr)
    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
