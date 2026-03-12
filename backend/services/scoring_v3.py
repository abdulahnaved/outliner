"""
v3 rule-based scoring and labeling for Outliner scan results.
OWASP-inspired tiers; deterministic; no external API.
"""
from __future__ import annotations

from typing import Any, Dict, List


def compute_rule_score(features: Dict[str, Any], evidence: Dict[str, Any] | None) -> Dict[str, Any]:
    """
    Compute rule_score (0-100), rule_grade (A/B/C/D/F), rule_label (0/1), rule_reasons (top 5).
    Start at 100, subtract penalties, clamp to [0, 100].
    """
    evidence = evidence or {}
    reasons: List[str] = []
    score = 100.0

    def _penalize(amount: float, reason: str) -> None:
        nonlocal score
        if amount > 0:
            score -= amount
            reasons.append(reason)

    # Transport
    has_https = features.get("has_https", 0)
    if has_https == 0:
        _penalize(40, "no HTTPS")
    else:
        if features.get("redirect_http_to_https", 0) == 0:
            _penalize(10, "HTTP not redirecting to HTTPS")
        if features.get("weak_tls", 0) == 1:
            _penalize(15, "weak TLS")
        cert_days = features.get("certificate_days_left")
        if cert_days is not None:
            if cert_days <= 0:
                _penalize(15, "certificate expired or invalid")
            elif cert_days <= 30:
                _penalize(5, "certificate expires in ≤30 days")

    # HSTS
    has_hsts = features.get("has_hsts", 0)
    if has_https == 1 and has_hsts == 0:
        _penalize(10, "HTTPS but no HSTS")
    if has_hsts == 1:
        if features.get("hsts_long", 0) == 0:
            _penalize(3, "HSTS max-age < 180 days")
        if features.get("hsts_include_subdomains", 0) == 0:
            _penalize(2, "HSTS missing includeSubDomains")

    # CSP
    has_csp = features.get("has_csp", 0)
    if has_csp == 0:
        _penalize(20, "no CSP")
    else:
        csp_score = features.get("csp_score")
        weaknesses: List[str] = []
        total_penalty = 0.0
        if csp_score is not None and csp_score < 0.7:
            total_penalty += 6
            weaknesses.append("overall CSP score is low")
        if features.get("csp_unsafe_eval", 0) == 1:
            total_penalty += 6
            weaknesses.append("CSP allows unsafe-eval")
        if features.get("csp_unsafe_inline", 0) == 1:
            total_penalty += 6
            weaknesses.append("CSP allows unsafe-inline in scripts")
        if features.get("csp_has_wildcard", 0) == 1:
            total_penalty += 6
            weaknesses.append("CSP uses wildcard (*)")
        if total_penalty > 0 and weaknesses:
            _penalize(total_penalty, f"CSP weaknesses: {', '.join(weaknesses)}")

    # Clickjacking / MIME
    if features.get("has_x_frame", 0) == 0:
        _penalize(8, "missing X-Frame-Options")
    if features.get("has_x_content_type", 0) == 0:
        _penalize(6, "missing X-Content-Type-Options: nosniff")

    # Cookies (only if cookies exist)
    set_cookies = evidence.get("set_cookie_values") or []
    if set_cookies:
        if features.get("cookie_secure", 0) == 0:
            _penalize(10, "cookies without Secure")
        if features.get("cookie_httponly", 0) == 0:
            _penalize(8, "cookies without HttpOnly")
        if features.get("cookie_samesite", 0) == 0:
            _penalize(6, "cookies without SameSite")

    # CORS
    if features.get("cors_wildcard", 0) == 1:
        _penalize(8, "CORS wildcard (*)")
    if features.get("cors_wildcard_with_credentials", 0) == 1:
        _penalize(25, "CORS wildcard with credentials (critical)")

    # Referrer-Policy
    if features.get("has_referrer_policy", 0) == 0:
        _penalize(3, "missing Referrer-Policy")
    elif features.get("referrer_policy_strict", 0) == 0:
        _penalize(1, "Referrer-Policy not strict")

    # Info disclosure
    if features.get("server_header_present", 0) == 1:
        _penalize(2, "Server header present")
    if features.get("x_powered_by_present", 0) == 1:
        _penalize(2, "X-Powered-By header present")

    # Modern isolation
    if features.get("has_permissions_policy", 0) == 0:
        _penalize(1, "missing Permissions-Policy")
    if features.get("has_coop", 0) == 0:
        _penalize(1, "missing Cross-Origin-Opener-Policy")
    if features.get("has_coep", 0) == 0:
        _penalize(1, "missing Cross-Origin-Embedder-Policy")
    if features.get("has_corp", 0) == 0:
        _penalize(1, "missing Cross-Origin-Resource-Policy")

    score = max(0.0, min(100.0, score))

    # Grade
    if score >= 90:
        grade = "A"
    elif score >= 80:
        grade = "B"
    elif score >= 70:
        grade = "C"
    elif score >= 60:
        grade = "D"
    else:
        grade = "F"

    # Label: 1 = bad/risky if score < 70
    rule_label = 1 if score < 70 else 0

    # Top 5 reasons (already in order of application; take first 5)
    rule_reasons = reasons[:5]

    return {
        "rule_score": round(score, 1),
        "rule_grade": grade,
        "rule_label": rule_label,
        "rule_reasons": rule_reasons,
    }
