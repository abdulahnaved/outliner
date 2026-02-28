#!/usr/bin/env python3
"""
Dev-only sanity check for lab targets. Run with lab containers up.
Uses verify=False for self-signed certs; do not use in production.
"""
from __future__ import annotations

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


def main() -> None:
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


if __name__ == "__main__":
    main()
