"""
v2 hybrid rule-based scoring: category-capped, Mozilla-inspired, less punitive.
Uses only existing passive security features (no new rescans).
Produces: rule_score_v2, rule_grade_v2, rule_label_v2, rule_reasons_v2, optional debug breakdown.
"""
from __future__ import annotations

from typing import Any, Dict, List

# Category caps (max penalty per category)
CAP_TRANSPORT = 25
CAP_CONTENT = 25
CAP_COOKIES = 20
CAP_BROWSER = 15
CAP_CROSS_ORIGIN = 15

# Bonus threshold: only add bonuses if score after penalties >= 85
BONUS_THRESHOLD = 85
SCORE_MIN = 0
SCORE_MAX = 110


def _get(features: Dict[str, Any], key: str, default: Any = 0) -> Any:
    v = features.get(key)
    if v is None and key == "csp_has_default_src":
        v = features.get("csp_has_default_self")
    return v if v is not None else default


def _int(features: Dict[str, Any], key: str, default: int = 0) -> int:
    v = _get(features, key, default)
    if v is None:
        return default
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return default


def _float(features: Dict[str, Any], key: str, default: float = 0.0) -> float:
    v = _get(features, key, default)
    if v is None:
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def compute_rule_score_v2(
    features: Dict[str, Any],
    evidence: Dict[str, Any] | None = None,
    *,
    include_debug: bool = False,
) -> Dict[str, Any]:
    """
    Compute rule_score_v2 (0-110), rule_grade_v2, rule_label_v2, rule_reasons_v2.
    Category-capped penalties; bonuses only when score after penalties >= 85.
    """
    evidence = evidence or {}
    reasons_by_category: Dict[str, List[str]] = {
        "transport_security": [],
        "content_security": [],
        "cookies_session_safety": [],
        "browser_policy_headers": [],
        "cross_origin_isolation": [],
    }
    transport_penalty = 0.0
    content_penalty = 0.0
    cookie_penalty = 0.0
    browser_penalty = 0.0
    cross_origin_penalty = 0.0
    total_bonus = 0.0

    # ----- 1. Transport Security (cap 25) -----
    has_https = _int(features, "has_https")
    redirect_http_to_https = _int(features, "redirect_http_to_https")
    weak_tls = _int(features, "weak_tls")
    cert_days = _float(features, "certificate_days_left")
    has_hsts = _int(features, "has_hsts")
    hsts_long = _int(features, "hsts_long")
    hsts_include_subdomains = _int(features, "hsts_include_subdomains")
    hsts_preload = _int(features, "hsts_preload")

    if has_https == 0:
        transport_penalty += 25
        reasons_by_category["transport_security"].append("no HTTPS")
    else:
        if redirect_http_to_https == 0:
            transport_penalty += 5
            reasons_by_category["transport_security"].append("HTTP not redirecting to HTTPS")
        if weak_tls == 1:
            transport_penalty += 8
            reasons_by_category["transport_security"].append("weak TLS")
        if cert_days <= 0:
            transport_penalty += 8
            reasons_by_category["transport_security"].append("certificate expired or invalid")
        elif cert_days <= 30:
            transport_penalty += 2
            reasons_by_category["transport_security"].append("certificate expires in ≤30 days")
        if has_hsts == 0:
            transport_penalty += 8
            reasons_by_category["transport_security"].append("HTTPS but no HSTS")
        else:
            if hsts_long == 0:
                transport_penalty += 3
                reasons_by_category["transport_security"].append("HSTS max-age < 180 days")
            if hsts_include_subdomains == 0:
                transport_penalty += 2
                reasons_by_category["transport_security"].append("HSTS missing includeSubDomains")
    if hsts_preload == 1:
        total_bonus += 3
    transport_penalty = min(transport_penalty, CAP_TRANSPORT)

    # ----- 2. Content Security (cap 25) -----
    has_csp = _int(features, "has_csp")
    csp_score = _float(features, "csp_score")
    csp_unsafe_eval = _int(features, "csp_unsafe_eval")
    csp_unsafe_inline = _int(features, "csp_unsafe_inline")
    csp_has_wildcard = _int(features, "csp_has_wildcard")
    csp_has_default_src = _int(features, "csp_has_default_src")
    csp_has_object_none = _int(features, "csp_has_object_none")

    if has_csp == 0:
        content_penalty += 18
        reasons_by_category["content_security"].append("no CSP")
    else:
        if csp_unsafe_inline == 1:
            content_penalty += 10
            reasons_by_category["content_security"].append("CSP allows unsafe-inline in scripts")
        if csp_unsafe_eval == 1:
            content_penalty += 8
            reasons_by_category["content_security"].append("CSP allows unsafe-eval")
        if csp_has_wildcard == 1:
            content_penalty += 5
            reasons_by_category["content_security"].append("CSP uses wildcard (*)")
        if csp_score < 0.7:
            content_penalty += 5
            reasons_by_category["content_security"].append("CSP overall score is low")
        if csp_has_object_none == 0:
            content_penalty += 3
            reasons_by_category["content_security"].append("CSP missing object-src 'none'")
        if csp_has_default_src == 0:
            content_penalty += 3
            reasons_by_category["content_security"].append("CSP missing default-src")
        # Bonuses (counted in total_bonus, applied only if penalty_score >= 85)
        if csp_unsafe_inline == 0 and csp_unsafe_eval == 0:
            total_bonus += 5
        if (
            csp_unsafe_inline == 0
            and csp_unsafe_eval == 0
            and csp_has_wildcard == 0
            and csp_score >= 0.85
        ):
            total_bonus += 3
    content_penalty = min(content_penalty, CAP_CONTENT)

    # ----- 3. Cookies / Session Safety (cap 20) -----
    total_cookie_count = _int(features, "total_cookie_count")
    secure_cookie_ratio = _float(features, "secure_cookie_ratio")
    httponly_cookie_ratio = _float(features, "httponly_cookie_ratio")
    samesite_cookie_ratio = _float(features, "samesite_cookie_ratio")

    if total_cookie_count > 0:
        # Secure
        secure_pen = 10 if secure_cookie_ratio < 0.5 else (5 if secure_cookie_ratio < 1.0 else 0)
        if secure_pen > 0 and has_hsts == 1:
            secure_pen = max(0, secure_pen - 2)
        cookie_penalty += secure_pen
        if secure_pen > 0:
            reasons_by_category["cookies_session_safety"].append(
                "cookies not all Secure" if secure_cookie_ratio < 0.5 else "some cookies without Secure"
            )
        # HttpOnly (stricter on likely session/auth cookies; softer otherwise)
        if httponly_cookie_ratio < 1.0:
            # Treat cases with very low HttpOnly coverage as stronger signal.
            if httponly_cookie_ratio < 0.5:
                cookie_penalty += 8
                reasons_by_category["cookies_session_safety"].append("cookies not all HttpOnly")
            else:
                cookie_penalty += 4
                reasons_by_category["cookies_session_safety"].append("some cookies without HttpOnly")
        # SameSite
        if samesite_cookie_ratio < 0.5:
            cookie_penalty += 6
            reasons_by_category["cookies_session_safety"].append("cookies not all SameSite")
        elif samesite_cookie_ratio < 1.0:
            cookie_penalty += 3
            reasons_by_category["cookies_session_safety"].append("some cookies without SameSite")
        if (
            secure_cookie_ratio == 1.0
            and httponly_cookie_ratio == 1.0
            and samesite_cookie_ratio == 1.0
        ):
            total_bonus += 2
    cookie_penalty = min(cookie_penalty, CAP_COOKIES)

    # ----- 4. Browser / Policy Headers (cap 15) -----
    has_x_frame = _int(features, "has_x_frame")
    has_x_content_type = _int(features, "has_x_content_type")
    has_referrer_policy = _int(features, "has_referrer_policy")
    referrer_policy_strict = _int(features, "referrer_policy_strict")
    has_permissions_policy = _int(features, "has_permissions_policy")
    server_header_present = _int(features, "server_header_present")
    x_powered_by_present = _int(features, "x_powered_by_present")

    if has_x_frame == 0:
        browser_penalty += 5
        reasons_by_category["browser_policy_headers"].append("missing X-Frame-Options")
    else:
        total_bonus += 2
    if has_x_content_type == 0:
        browser_penalty += 4
        reasons_by_category["browser_policy_headers"].append("missing X-Content-Type-Options: nosniff")
    if has_referrer_policy == 0:
        browser_penalty += 2
        reasons_by_category["browser_policy_headers"].append("missing Referrer-Policy")
    elif referrer_policy_strict == 0:
        browser_penalty += 1
        reasons_by_category["browser_policy_headers"].append("Referrer-Policy not strict")
    else:
        total_bonus += 2
    if has_permissions_policy == 0:
        browser_penalty += 1
        reasons_by_category["browser_policy_headers"].append("missing Permissions-Policy")
    if server_header_present == 1:
        browser_penalty += 1
        reasons_by_category["browser_policy_headers"].append("Server header present")
    if x_powered_by_present == 1:
        browser_penalty += 1
        reasons_by_category["browser_policy_headers"].append("X-Powered-By header present")
    browser_penalty = min(browser_penalty, CAP_BROWSER)

    # ----- 5. Cross-Origin / Isolation (cap 15) -----
    cors_wildcard = _int(features, "cors_wildcard")
    cors_wildcard_with_credentials = _int(features, "cors_wildcard_with_credentials")
    has_coop = _int(features, "has_coop")
    has_coep = _int(features, "has_coep")
    has_corp = _int(features, "has_corp")

    if cors_wildcard_with_credentials == 1:
        cross_origin_penalty += 15
        reasons_by_category["cross_origin_isolation"].append("CORS wildcard with credentials (critical)")
    elif cors_wildcard == 1:
        cross_origin_penalty += 4
        reasons_by_category["cross_origin_isolation"].append("CORS wildcard (*)")
    if has_coop == 0:
        cross_origin_penalty += 1
        reasons_by_category["cross_origin_isolation"].append("missing Cross-Origin-Opener-Policy")
    if has_coep == 0:
        cross_origin_penalty += 1
        reasons_by_category["cross_origin_isolation"].append("missing Cross-Origin-Embedder-Policy")
    if has_corp == 1:
        total_bonus += 2
    if has_coop == 1 and has_coep == 1:
        total_bonus += 3
    cross_origin_penalty = min(cross_origin_penalty, CAP_CROSS_ORIGIN)

    # ----- Aggregate and apply bonus rule -----
    total_penalty = (
        transport_penalty
        + content_penalty
        + cookie_penalty
        + browser_penalty
        + cross_origin_penalty
    )
    penalty_score = 100.0 - total_penalty
    if penalty_score >= BONUS_THRESHOLD:
        final_score = penalty_score + total_bonus
    else:
        final_score = penalty_score
    final_score = max(SCORE_MIN, min(SCORE_MAX, round(final_score, 1)))

    # ----- Grade mapping -----
    if final_score >= 100:
        grade = "A+"
    elif final_score >= 90:
        grade = "A"
    elif final_score >= 85:
        grade = "A-"
    elif final_score >= 80:
        grade = "B+"
    elif final_score >= 70:
        grade = "B"
    elif final_score >= 65:
        grade = "B-"
    elif final_score >= 60:
        grade = "C+"
    elif final_score >= 50:
        grade = "C"
    elif final_score >= 45:
        grade = "C-"
    elif final_score >= 40:
        grade = "D+"
    elif final_score >= 30:
        grade = "D"
    elif final_score >= 25:
        grade = "D-"
    else:
        grade = "F"

    rule_label_v2 = 1 if final_score < 60 else 0

    # Flatten reasons by category for rule_reasons_v2 (e.g. "transport: no HTTPS; content: no CSP")
    rule_reasons_v2: List[str] = []
    for cat, reasons in reasons_by_category.items():
        for r in reasons:
            rule_reasons_v2.append(f"{cat}: {r}")

    out: Dict[str, Any] = {
        "rule_score_v2": round(final_score, 1),
        "rule_grade_v2": grade,
        "rule_label_v2": rule_label_v2,
        "rule_reasons_v2": rule_reasons_v2,
        "reasons_by_category": reasons_by_category,
    }
    if include_debug:
        out["score_debug"] = {
            "transport_penalty": round(transport_penalty, 1),
            "content_penalty": round(content_penalty, 1),
            "cookie_penalty": round(cookie_penalty, 1),
            "browser_penalty": round(browser_penalty, 1),
            "cross_origin_penalty": round(cross_origin_penalty, 1),
            "total_penalty": round(total_penalty, 1),
            "total_bonus": round(total_bonus, 1),
            "penalty_score": round(penalty_score, 1),
            "final_score": round(final_score, 1),
        }
    return out
