#!/usr/bin/env python3
"""
Regression check: scanning youtube.com should produce
  http_probe_status in {301, 302}, http_probe_location startswith "https://", redirect_http_to_https=1.
Run from backend/ with: python3 scripts/check_redirect_probe.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# backend/scripts -> backend
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.passive_scan import perform_passive_scan


async def main() -> int:
    target = "youtube.com"
    result = await perform_passive_scan(target)
    ev = result.evidence
    if ev is not None and hasattr(ev, "model_dump"):
        ev = ev.model_dump()
    ev = ev or {}
    status = ev.get("http_probe_status")
    location = (ev.get("http_probe_location") or "") or ""
    err = ev.get("http_probe_error")
    redirect_ok = getattr(result.features, "redirect_http_to_https", 0) == 1

    ok = (
        status in (301, 302)
        and location.strip().lower().startswith("https://")
        and redirect_ok
    )
    print(f"Target: {target}")
    print(f"  http_probe_status: {status}")
    print(f"  http_probe_location: {location[:80]}..." if len(location) > 80 else f"  http_probe_location: {location}")
    print(f"  http_probe_error: {err}")
    print(f"  redirect_http_to_https: {redirect_ok}")
    if ok:
        print("PASS: redirect probe regression check")
        return 0
    print("FAIL: expected status in {301,302}, location startswith https://, redirect_http_to_https=1", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
