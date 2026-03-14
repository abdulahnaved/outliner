"""Unit tests for scoring_v2: rule_score_v2, grade, reasons."""
import pytest
from services.scoring_v2 import compute_rule_score_v2


def test_perfect_score_gets_a_plus() -> None:
    features = {
        "has_https": 1,
        "redirect_http_to_https": 1,
        "weak_tls": 0,
        "certificate_days_left": 400,
        "has_hsts": 1,
        "hsts_long": 1,
        "hsts_include_subdomains": 1,
        "has_csp": 1,
        "csp_score": 0.9,
        "csp_unsafe_inline": 0,
        "csp_unsafe_eval": 0,
        "secure_cookie_ratio": 1.0,
        "httponly_cookie_ratio": 1.0,
        "samesite_cookie_ratio": 1.0,
        "total_cookie_count": 2,
        "has_x_frame": 1,
        "has_x_content_type": 1,
        "has_referrer_policy": 1,
        "referrer_policy_strict": 1,
        "has_permissions_policy": 1,
        "cors_wildcard_with_credentials": 0,
    }
    out = compute_rule_score_v2(features)
    assert out["rule_score_v2"] >= 100
    assert out["rule_grade_v2"] == "A+"


def test_no_https_max_transport_penalty() -> None:
    features = {
        "has_https": 0,
        "redirect_http_to_https": 0,
        "has_hsts": 0,
        "has_csp": 0,
        "total_cookie_count": 0,
        "has_x_frame": 0,
        "has_x_content_type": 0,
        "has_referrer_policy": 0,
        "has_permissions_policy": 0,
        "cors_wildcard_with_credentials": 0,
    }
    out = compute_rule_score_v2(features)
    assert out["rule_score_v2"] <= 75
    assert "no HTTPS" in str(out["rule_reasons_v2"]).lower() or "transport" in str(out["reasons_by_category"])


def test_grade_mapping() -> None:
    """Score boundaries map to expected grades."""
    # Low score -> F
    out = compute_rule_score_v2({"has_https": 0, "has_csp": 0, "has_hsts": 0, "total_cookie_count": 0,
                                  "has_x_frame": 0, "has_x_content_type": 0, "has_referrer_policy": 0,
                                  "has_permissions_policy": 0, "cors_wildcard_with_credentials": 0})
    assert out["rule_grade_v2"] in ("D+", "D", "D-", "F")

    # Mid score with some good signals
    features = {"has_https": 1, "redirect_http_to_https": 1, "has_hsts": 0, "weak_tls": 0,
                "certificate_days_left": 90, "has_csp": 1, "csp_score": 0.5, "csp_unsafe_inline": 0, "csp_unsafe_eval": 0,
                "total_cookie_count": 0, "has_x_frame": 0, "has_x_content_type": 0,
                "has_referrer_policy": 0, "has_permissions_policy": 0, "cors_wildcard_with_credentials": 0}
    out = compute_rule_score_v2(features)
    assert 0 <= out["rule_score_v2"] <= 110
    assert out["rule_grade_v2"] in ("A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "F")


def test_output_has_required_keys() -> None:
    out = compute_rule_score_v2({"has_https": 1, "has_csp": 0, "has_hsts": 0, "total_cookie_count": 0,
                                  "has_x_frame": 0, "has_x_content_type": 0, "has_referrer_policy": 0,
                                  "has_permissions_policy": 0, "cors_wildcard_with_credentials": 0})
    assert "rule_score_v2" in out
    assert "rule_grade_v2" in out
    assert "rule_label_v2" in out
    assert "rule_reasons_v2" in out
    assert isinstance(out["rule_score_v2"], (int, float))
    assert isinstance(out["rule_reasons_v2"], list)
