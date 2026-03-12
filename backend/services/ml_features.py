"""
Shared regression feature extraction for training export and runtime inference.

Single source of truth: same regression-safe feature set and missing-value/derived
logic as export_regression_dataset.py. Used by ml_inference.py at runtime and
by the export script (which can import from here to avoid drift).
"""
from __future__ import annotations

import math
from typing import Any

# Regression-safe feature keys only (no scoring proxies or labels).
# Must match export_regression_dataset.REGRESSION_SAFE_FEATURES.
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

DERIVED_KEYS = ("tls_version_missing", "cert_days_missing", "cert_expired", "response_time_log")


def _get_canonical_value(features: dict[str, Any], key: str) -> Any:
    v = features.get(key)
    if v is not None:
        return v
    if key == "csp_has_default_src":
        return features.get("csp_has_default_self")
    return None


def _coerce_float(x: Any) -> float:
    if x is None or x == "":
        return 0.0
    try:
        return float(x)
    except (ValueError, TypeError):
        return 0.0


def build_feature_row(scan_result: dict[str, Any]) -> dict[str, float]:
    """
    Build one flat feature row from a scan result (same logic as export regression).
    scan_result must have "features" (dict). Optionally top-level "is_blocked".
    Returns dict with regression-safe keys + derived (tls_version_missing, etc.).
    """
    features = scan_result.get("features") or {}
    if hasattr(features, "model_dump"):
        features = features.model_dump()
    elif hasattr(features, "dict"):
        features = features.dict()

    flat: dict[str, float] = {}
    flat["is_blocked"] = int(scan_result.get("is_blocked", 0) or 0)

    for key in REGRESSION_SAFE_FEATURES:
        v = _get_canonical_value(features, key)
        if v is None:
            v = features.get(key)
        if v is None or (isinstance(v, float) and math.isnan(v)):
            v = 0
        flat[key] = _coerce_float(v)

    # Derived / missing-value handling (must match training)
    tls = flat.get("tls_version")
    if tls is None or (isinstance(tls, float) and math.isnan(tls)):
        flat["tls_version"] = 0.0
        flat["tls_version_missing"] = 1.0
    else:
        flat["tls_version_missing"] = 0.0

    cert_days = flat.get("certificate_days_left")
    if cert_days is None or (isinstance(cert_days, float) and math.isnan(cert_days)):
        flat["certificate_days_left"] = 0.0
        flat["cert_days_missing"] = 1.0
    else:
        flat["cert_days_missing"] = 0.0

    try:
        flat["cert_expired"] = 1.0 if float(flat["certificate_days_left"]) <= 0 else 0.0
    except (TypeError, ValueError):
        flat["cert_expired"] = 0.0

    rt = flat.get("response_time")
    try:
        rt_f = float(rt) if rt is not None else 0.0
        flat["response_time_log"] = math.log1p(max(0.0, rt_f))
    except (TypeError, ValueError):
        flat["response_time_log"] = 0.0

    return flat


def feature_row_to_vector(flat: dict[str, float], feature_columns: list[str]) -> list[float]:
    """Return values in the exact order expected by the model."""
    return [_coerce_float(flat.get(c)) for c in feature_columns]
