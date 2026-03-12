#!/usr/bin/env python3
"""
Smoke test for ML inference: load a scan-like input, call predict_rule_score, verify numeric score.
Run from backend: python scripts/test_ml_inference.py
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.ml_inference import predict_rule_score


def make_scan_like() -> dict:
    """Minimal scan result shape (nested features) compatible with pipeline output."""
    return {
        "input_target": "example.com",
        "normalized_host": "example.com",
        "requested_url": "https://example.com/",
        "final_url": "https://example.com/",
        "final_status_code": 200,
        "features": {
            "has_https": 1,
            "redirect_http_to_https": 1,
            "has_hsts": 1,
            "tls_version": 1.3,
            "weak_tls": 0,
            "certificate_days_left": 90,
            "redirect_count": 0,
            "response_time": 0.5,
            "has_csp": 1,
            "csp_has_default_src": 1,
            "csp_unsafe_inline": 0,
            "csp_unsafe_eval": 0,
            "csp_has_wildcard": 0,
            "csp_has_object_none": 1,
            "hsts_max_age": 31536000,
            "hsts_long": 1,
            "hsts_include_subdomains": 1,
            "hsts_preload": 1,
            "has_referrer_policy": 1,
            "referrer_policy_strict": 1,
            "has_permissions_policy": 0,
            "has_coop": 0,
            "has_coep": 0,
            "has_corp": 0,
            "server_header_present": 0,
            "x_powered_by_present": 0,
            "cookie_secure": 1,
            "cookie_httponly": 1,
            "cookie_samesite": 1,
            "total_cookie_count": 0,
            "secure_cookie_ratio": 0.0,
            "httponly_cookie_ratio": 0.0,
            "samesite_cookie_ratio": 0.0,
            "cors_wildcard": 0,
            "cors_allows_credentials": 0,
            "cors_wildcard_with_credentials": 0,
            "status_is_2xx": 1,
            "status_is_3xx": 0,
            "status_is_4xx": 0,
            "status_is_5xx": 0,
        },
    }


def main() -> int:
    scan = make_scan_like()
    out = predict_rule_score(scan)
    if not out.get("ml_model_name"):
        print("Missing ml_model_name", file=sys.stderr)
        return 1
    if out.get("prediction_available"):
        score = out.get("predicted_rule_score")
        if score is None:
            print("prediction_available=True but predicted_rule_score is None", file=sys.stderr)
            return 1
        if not isinstance(score, (int, float)):
            print("predicted_rule_score is not numeric", file=sys.stderr)
            return 1
        print(f"OK: predicted_rule_score={score}")
        return 0
    print("Prediction unavailable:", out.get("prediction_error", "unknown"), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
