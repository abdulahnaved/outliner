#!/usr/bin/env python3
"""
Dev-only sanity check for lab targets. Run with lab containers up.
Uses verify=False for self-signed certs; do not use in production.

Optional: python3 scripts/test_lab.py --scan youtube.com
  Calls POST /api/scan and prints http_probe evidence for real sites.
"""
from __future__ import annotations

import argparse
import warnings

import httpx

# Suppress InsecureRequestWarning when verify=False (optional)
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

LAB_URLS = [
    "https://localhost:8441",  # good
    "https://localhost:8442",  # bad_headers
    "https://localhost:8443",  # bad_cors
    "https://localhost:8444",  # bad_cookies
    "http://localhost:8085",   # http_only
]

HEADERS_TO_SHOW = [
    "strict-transport-security",
    "content-security-policy",
    "x-frame-options",
    "x-content-type-options",
    "access-control-allow-origin",
    "set-cookie",
]


def run_lab_checks(api_url: str) -> None:
    client = httpx.Client(verify=False, timeout=10.0)
    try:
        for url in LAB_URLS:
            print(f"\n--- {url} ---")
            try:
                r = client.get(url)
                print(f"status_code: {r.status_code}")
                for name in HEADERS_TO_SHOW:
                    found = [v for k, v in r.headers.multi_items() if k.lower() == name]
                    if not found:
                        v = r.headers.get(name)
                        if v is not None:
                            found = [v]
                    for v in found:
                        print(f"  {name}: {v}")
            except Exception as e:
                print(f"  error: {e}")
    finally:
        client.close()
    print()


def run_scan_and_print_evidence(target: str, api_url: str) -> None:
    url = f"{api_url.rstrip('/')}/api/scan"
    try:
        r = httpx.post(url, json={"target": target}, timeout=30.0)
        if r.status_code != 200:
            print(f"Scan failed: {r.status_code} {r.text}")
            return
        data = r.json()
        feats = data.get("features") or {}
        ev = data.get("evidence") or {}
        print(f"\n--- Scan: {target} ---")
        print(f"redirect_http_to_https: {feats.get('redirect_http_to_https')}")
        print("HTTP probe evidence:")
        print(f"  http_probe_status: {ev.get('http_probe_status')}")
        print(f"  http_probe_location: {ev.get('http_probe_location')}")
        print(f"  http_probe_error: {ev.get('http_probe_error')}")
    except Exception as e:
        print(f"Error: {e}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Lab sanity check; optional --scan for http_probe evidence")
    ap.add_argument("--scan", type=str, metavar="TARGET", help="Call /api/scan and print http_probe evidence (e.g. youtube.com)")
    ap.add_argument("--api-url", type=str, default="http://localhost:8000", help="Base URL of API (for --scan)")
    args = ap.parse_args()

    if args.scan:
        run_scan_and_print_evidence(args.scan, args.api_url)
        return
    run_lab_checks(args.api_url)


if __name__ == "__main__":
    main()
