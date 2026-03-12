#!/usr/bin/env python3
"""
Smoke test for failed-scan response: structured ScanResult for failed scans,
null scores when unavailable, no unhandled exception.
Run from backend: python scripts/test_failed_scan_response.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.passive_scan import perform_passive_scan, _make_failed_result


def test_failed_result_shape() -> int:
    """Simulated failed result has correct shape and null scores."""
    r = _make_failed_result(
        "https://example.invalid/",
        "example.invalid",
        "https://example.invalid/",
        "timeout",
        "Request timed out",
    )
    if r.scan_status != "failed":
        print(f"FAIL: _make_failed_result should set scan_status='failed', got {r.scan_status!r}", file=sys.stderr)
        return 1
    if r.rule_score is not None:
        print(f"FAIL: failed result should have rule_score=None, got {r.rule_score}", file=sys.stderr)
        return 1
    if r.rule_grade is not None:
        print(f"FAIL: failed result should have rule_grade=None", file=sys.stderr)
        return 1
    if r.rule_label is not None:
        print(f"FAIL: failed result should have rule_label=None", file=sys.stderr)
        return 1
    if r.prediction_available or r.predicted_rule_score is not None:
        print("FAIL: failed result should have prediction_available=False, predicted_rule_score=None", file=sys.stderr)
        return 1
    if not r.scan_error_type or not r.scan_error_message:
        print("FAIL: failed result should have scan_error_type and scan_error_message", file=sys.stderr)
        return 1
    if r.input_target != "https://example.invalid/":
        print("FAIL: input_target should be preserved", file=sys.stderr)
        return 1
    print("OK: _make_failed_result shape and null scores")
    return 0


async def test_unreachable_does_not_raise() -> int:
    """Unreachable target: no exception; result has scan_status and preserved fields."""
    target = "https://nonexistent-domain-xyz-12345.invalid/"
    try:
        result = await perform_passive_scan(target)
    except Exception as e:
        print(f"FAIL: perform_passive_scan raised: {e}", file=sys.stderr)
        return 1
    if not hasattr(result, "scan_status"):
        print("FAIL: result has no scan_status", file=sys.stderr)
        return 1
    if result.scan_status not in ("success", "failed"):
        print(f"FAIL: scan_status must be success/failed, got {result.scan_status!r}", file=sys.stderr)
        return 1
    if result.input_target != target:
        print(f"FAIL: input_target should be preserved, got {result.input_target!r}", file=sys.stderr)
        return 1
    if result.scan_status == "failed":
        if result.rule_score is not None or result.prediction_available:
            print("FAIL: failed scan should have null score and prediction_available=False", file=sys.stderr)
            return 1
        if not result.scan_error_type or not result.scan_error_message:
            print("FAIL: failed scan should have scan_error_type and scan_error_message", file=sys.stderr)
            return 1
    print("OK: unreachable target returned structured result; scan_status=%s; no exception" % result.scan_status)
    return 0


def main() -> int:
    if test_failed_result_shape() != 0:
        return 1
    return asyncio.run(test_unreachable_does_not_raise())


if __name__ == "__main__":
    sys.exit(main())
