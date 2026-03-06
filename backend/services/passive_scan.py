"""
Passive scanner v3: posture features + rule-based scoring (OWASP-inspired).
"""
from __future__ import annotations

import os
import re
import ssl
import socket
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx

from schemas import ScanEvidence, ScanFeatures, ScanResult

from .scoring_v3 import compute_rule_score


USER_AGENT = "Outliner/0.1 (research)"
TIMEOUT_SECONDS = 15.0
HTTP_PROBE_TIMEOUT = 8.0
REDIRECT_STATUSES = {301, 302, 303, 307, 308}
WEAK_CIPHER_PATTERNS = re.compile(r"RC4|3DES|DES|NULL|EXPORT|MD5", re.IGNORECASE)
TLS_VERSION_MAP = {
    "TLSv1": 1.0,
    "TLSv1.1": 1.1,
    "TLSv1.2": 1.2,
    "TLSv1.3": 1.3,
}
TLS_VERSION_SCORE_MAP = {1.0: 0.0, 1.1: 0.2, 1.2: 0.7, 1.3: 1.0}
HSTS_LONG_SECONDS = 15552000  # 180 days
REFERRER_POLICY_STRICT = {"no-referrer", "strict-origin", "strict-origin-when-cross-origin"}
CSP_DIRECTIVES_FOR_WILDCARD = (
    "default-src", "script-src", "style-src", "img-src",
    "connect-src", "frame-src", "child-src", "object-src",
)


def _csp_quality(csp_val: Optional[str]) -> Tuple[int, int, int, int]:
    """Return (unsafe_inline, unsafe_eval, default_self, object_none)."""
    if not csp_val or not csp_val.strip():
        return 0, 0, 0, 0
    s = csp_val.strip().lower().replace(" ", "")
    unsafe_inline = 1 if "'unsafe-inline'" in s else 0
    unsafe_eval = 1 if "'unsafe-eval'" in s else 0
    default_self = 0
    object_none = 0
    raw = csp_val.strip()
    if "default-src" in raw.lower():
        m = re.search(r"default-src\s+([^;]+)", raw, re.IGNORECASE)
        if m and "'self'" in m.group(1):
            default_self = 1
    if "object-src" in raw.lower():
        m = re.search(r"object-src\s+([^;]+)", raw, re.IGNORECASE)
        if m and "'none'" in m.group(1):
            object_none = 1
    return unsafe_inline, unsafe_eval, default_self, object_none


def _hsts_strength(hsts_val: Optional[str]) -> Tuple[Optional[float], Optional[int], int, int, int]:
    """Return (max_age_days, max_age_seconds, hsts_long, include_subdomains, preload)."""
    if not hsts_val or not hsts_val.strip():
        return None, None, 0, 0, 0
    s = hsts_val.strip().lower()
    max_age_secs: Optional[int] = None
    max_age_days: Optional[float] = None
    m = re.search(r"max-age\s*=\s*(\d+)", s)
    if m:
        try:
            max_age_secs = int(m.group(1))
            max_age_days = round(max_age_secs / 86400.0, 2)
        except (ValueError, TypeError):
            pass
    hsts_long = 1 if (max_age_secs is not None and max_age_secs >= HSTS_LONG_SECONDS) else 0
    include_subdomains = 1 if "includesubdomains" in s.replace("-", "").replace(" ", "") else 0
    preload = 1 if "preload" in s else 0
    return max_age_days, max_age_secs, hsts_long, include_subdomains, preload


def _csp_v3(csp_val: Optional[str]) -> Tuple[int, int, int, int, float]:
    """Return (csp_has_default_src, csp_unsafe_inline, csp_unsafe_eval, csp_has_wildcard, csp_score)."""
    if not csp_val or not csp_val.strip():
        return 0, 0, 0, 0, 0.0
    raw = csp_val.strip()
    s = raw.lower().replace(" ", "")
    has_default_src = 1 if "default-src" in raw.lower() else 0
    unsafe_inline = 1 if "'unsafe-inline'" in s else 0
    unsafe_eval = 1 if "'unsafe-eval'" in s else 0
    has_wildcard = 0
    for directive in CSP_DIRECTIVES_FOR_WILDCARD:
        m = re.search(rf"{re.escape(directive)}\s+([^;]+)", raw, re.IGNORECASE)
        if m and "*" in m.group(1):
            has_wildcard = 1
            break
    if has_default_src == 0:
        csp_score = 0.3 if raw else 0.0
    elif unsafe_eval == 1 or has_wildcard == 1:
        csp_score = 0.3
    elif unsafe_inline == 1:
        csp_score = 0.7
    else:
        csp_score = 1.0
    return has_default_src, unsafe_inline, unsafe_eval, has_wildcard, csp_score


def _should_skip_verify(host: str) -> bool:
    """Skip TLS verify only when OUTLINER_ALLOW_LOCALHOST and host is localhost/127.0.0.1."""
    allow = os.getenv("OUTLINER_ALLOW_LOCALHOST", "").strip().lower() in ("true", "1", "yes")
    if not allow:
        return False
    h = (host or "").strip().lower()
    if h == "localhost":
        return True
    if h == "127.0.0.1":
        return True
    return False


def _build_urls(host: str, port: Optional[int], use_https: bool) -> str:
    scheme = "https" if use_https else "http"
    if port is None or port == (443 if use_https else 80):
        return f"{scheme}://{host}/"
    return f"{scheme}://{host}:{port}/"


def _http_probe_url(requested_url: str) -> str:
    """
    URL to use for the dedicated HTTP redirect probe.
    - If user requested http://host:port (e.g. http://localhost:8085), probe that exact host:port.
    - Otherwise probe http://host/ (port 80). Never probe http://host:443.
    """
    p = urlparse(requested_url)
    host = (p.hostname or "").lower()
    scheme = (p.scheme or "").lower()
    port = p.port
    if scheme == "http" and port is not None and port != 80:
        return f"http://{host}:{port}/"
    return f"http://{host}/"


def _host_port_from_url(url: str) -> Tuple[str, int]:
    p = urlparse(url)
    host = (p.hostname or "").lower()
    port = p.port
    if p.scheme == "https":
        port = port or 443
    else:
        port = port or 80
    return host, port


def _get_header(headers: httpx.Headers, name: str) -> Optional[str]:
    return headers.get(name)


def _get_header_list(headers: httpx.Headers, name: str) -> List[str]:
    out: List[str] = []
    for k, v in headers.multi_items():
        if k.lower() == name.lower():
            out.append(v)
    return out


def _parse_cert_not_after(not_after: str) -> Optional[datetime]:
    """Parse notAfter like 'Jun 10 12:00:00 2026 GMT' to UTC datetime."""
    if not not_after or not isinstance(not_after, str):
        return None
    try:
        # ssl.getpeercert() returns this format on most platforms
        dt = datetime.strptime(not_after.strip(), "%b %d %H:%M:%S %Y %Z")
        # Treat as UTC (GMT)
        return dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        try:
            # Fallback: strip timezone suffix (e.g. " GMT") for platforms that differ
            s = re.sub(r"\s+[A-Z]+$", "", not_after.strip())
            dt = datetime.strptime(s, "%b %d %H:%M:%S %Y")
            return dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return None


def _tls_probe(host: str, port: int, skip_verify: bool) -> Dict[str, Any]:
    """Connect to host:port with TLS; return version, cipher, cert days left."""
    result: Dict[str, Any] = {
        "tls_version_raw": None,
        "tls_version": None,
        "cipher": None,
        "certificate_days_left": None,
    }
    ctx = ssl.create_default_context()
    if skip_verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    try:
        with socket.create_connection((host, port), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                result["tls_version_raw"] = ssock.version()
                result["tls_version"] = TLS_VERSION_MAP.get(ssock.version())
                c = ssock.cipher()
                result["cipher"] = c[0] if c else None
                cert = ssock.getpeercert()
                if cert and "notAfter" in cert:
                    dt = _parse_cert_not_after(cert["notAfter"])
                    if dt:
                        delta = dt.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)
                        result["certificate_days_left"] = max(0, delta.days)
    except Exception:
        pass
    return result


async def perform_passive_scan(target: str) -> ScanResult:
    from utils.normalize import normalize_target
    from utils.ssrf import is_blocked_host

    # 1) Normalize
    try:
        normalized = normalize_target(target)
    except ValueError:
        raise ValueError("Invalid target")

    host = normalized.normalized_host
    if is_blocked_host(host):
        raise ValueError("Target not allowed (SSRF)")

    requested_url = normalized.requested_url
    host_for_url, port_for_url = _host_port_from_url(requested_url)
    https_url = _build_urls(host_for_url, port_for_url, True)
    http_url = _build_urls(host_for_url, port_for_url, False)
    http_probe_url = _http_probe_url(requested_url)
    skip_verify = _should_skip_verify(host_for_url)

    # 2) has_https
    has_https = 0
    try:
        async with httpx.AsyncClient(
            verify=not skip_verify,
            timeout=TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            r = await client.get(https_url)
            has_https = 1
    except Exception:
        pass

    # 3) redirect_http_to_https — dedicated HTTP probe (do not reuse final fetch)
    redirect_http_to_https = 0
    http_probe_status: Optional[int] = None
    http_probe_location: Optional[str] = None
    http_probe_error: Optional[str] = None
    try:
        async with httpx.AsyncClient(
            verify=not skip_verify,
            timeout=HTTP_PROBE_TIMEOUT,
            follow_redirects=False,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            r = await client.get(http_probe_url)
            http_probe_status = r.status_code
            loc = _get_header(r.headers, "location")
            http_probe_location = loc.strip() if loc and loc.strip() else None
            if r.status_code in REDIRECT_STATUSES and http_probe_location and http_probe_location.strip().lower().startswith("https://"):
                redirect_http_to_https = 1
    except Exception as e:
        msg = (str(e).strip() or type(e).__name__)
        http_probe_error = msg[:200] if msg else "UnknownError"

    # 4) Final fetch (HTTPS if available else HTTP)
    base_url = https_url if has_https else http_url
    final_url: Optional[str] = None
    final_status_code: Optional[int] = None
    timing_ms: Optional[int] = None
    redirect_count = 0
    response_time = 0.0
    headers: httpx.Headers = httpx.Headers([])
    set_cookie_values: List[str] = []

    start = time.perf_counter()
    async with httpx.AsyncClient(
        verify=not skip_verify,
        timeout=TIMEOUT_SECONDS,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    ) as client:
        response = await client.get(base_url)
    elapsed = time.perf_counter() - start
    timing_ms = int(elapsed * 1000)
    response_time = round(elapsed, 4)
    final_url = str(response.url)
    final_status_code = response.status_code
    redirect_count = len(response.history)
    headers = response.headers
    set_cookie_values = _get_header_list(response.headers, "set-cookie")

    # 5) Header features (case-insensitive)
    hsts_val = _get_header(headers, "strict-transport-security")
    has_hsts = 1 if (hsts_val is not None and hsts_val.strip()) else 0

    csp_val = _get_header(headers, "content-security-policy")
    has_csp = 1 if (csp_val is not None and csp_val.strip()) else 0

    xfo_val = _get_header(headers, "x-frame-options")
    has_x_frame = 1 if (xfo_val is not None and xfo_val.strip()) else 0

    xct_val = _get_header(headers, "x-content-type-options")
    has_x_content_type = 1 if (xct_val is not None and xct_val.strip().lower() == "nosniff") else 0

    acao_val = _get_header(headers, "access-control-allow-origin")
    cors_wildcard = 1 if (acao_val is not None and acao_val.strip() == "*") else 0

    # 6) Cookie features (binary flags + depth)
    cookie_secure = 0
    cookie_httponly = 0
    cookie_samesite = 0
    total_cookie_count = len(set_cookie_values)
    secure_count = 0
    httponly_count = 0
    samesite_count = 0
    for raw in set_cookie_values:
        raw_lower = raw.lower()
        if "secure" in raw_lower:
            cookie_secure = 1
            secure_count += 1
        if "httponly" in raw_lower:
            cookie_httponly = 1
            httponly_count += 1
        if "samesite=" in raw_lower:
            cookie_samesite = 1
            samesite_count += 1
    if total_cookie_count > 0:
        secure_cookie_ratio = round(secure_count / total_cookie_count, 4)
        httponly_cookie_ratio = round(httponly_count / total_cookie_count, 4)
        samesite_cookie_ratio = round(samesite_count / total_cookie_count, 4)
    else:
        secure_cookie_ratio = 0.0
        httponly_cookie_ratio = 0.0
        samesite_cookie_ratio = 0.0

    # 7) Policy headers (presence only)
    has_referrer_policy = 1 if (_get_header(headers, "referrer-policy") or "").strip() else 0
    has_permissions_policy = 1 if (
        (_get_header(headers, "permissions-policy") or "").strip()
        or (_get_header(headers, "feature-policy") or "").strip()
    ) else 0

    # 8) Server exposure (presence only)
    server_header_present = 1 if (_get_header(headers, "server") or "").strip() else 0
    x_powered_by_present = 1 if (_get_header(headers, "x-powered-by") or "").strip() else 0

    # 9) CSP quality + HSTS strength (v2 + v3)
    csp_unsafe_inline, csp_unsafe_eval, csp_default_self, csp_object_none = _csp_quality(csp_val)
    hsts_max_age_days, hsts_max_age_secs, hsts_long, hsts_include_subdomains, hsts_preload = _hsts_strength(hsts_val)
    csp_has_default_src, csp_unsafe_inline_v3, csp_unsafe_eval_v3, csp_has_wildcard, csp_score = _csp_v3(csp_val)

    # 9b) Referrer-Policy strict
    referrer_policy_raw = _get_header(headers, "referrer-policy")
    referrer_policy_strict = 0
    if referrer_policy_raw and referrer_policy_raw.strip():
        rp = referrer_policy_raw.strip().lower().split(";")[0].strip()
        if rp in REFERRER_POLICY_STRICT:
            referrer_policy_strict = 1

    # 9c) Modern isolation headers
    coop_val = _get_header(headers, "cross-origin-opener-policy")
    coep_val = _get_header(headers, "cross-origin-embedder-policy")
    corp_val = _get_header(headers, "cross-origin-resource-policy")
    has_coop = 1 if (coop_val or "").strip() else 0
    has_coep = 1 if (coep_val or "").strip() else 0
    has_corp = 1 if (corp_val or "").strip() else 0

    # 9d) CORS credentials
    acac_val = _get_header(headers, "access-control-allow-credentials")
    cors_allows_credentials = 1 if (acac_val or "").strip().lower() == "true" else 0
    cors_wildcard_with_credentials = 1 if (cors_wildcard == 1 and cors_allows_credentials == 1) else 0

    permissions_policy_raw = _get_header(headers, "permissions-policy") or _get_header(headers, "feature-policy")
    powered_by_val = _get_header(headers, "x-powered-by")

    # 10) Status buckets
    code = final_status_code or 0
    status_is_2xx = 1 if 200 <= code < 300 else 0
    status_is_3xx = 1 if 300 <= code < 400 else 0
    status_is_4xx = 1 if 400 <= code < 500 else 0
    status_is_5xx = 1 if 500 <= code < 600 else 0

    # 11) TLS (v3: restore weak_tls, tls_version_score)
    tls_version = None
    tls_version_score = None
    weak_tls = 0
    certificate_days_left = None
    tls_version_raw = None
    cipher = None
    if has_https == 1 and final_url and "https" in final_url:
        h, p = _host_port_from_url(final_url)
        tls_result = _tls_probe(h, p, skip_verify)
        tls_version_raw = tls_result.get("tls_version_raw")
        tls_version = tls_result.get("tls_version")
        cipher = tls_result.get("cipher")
        certificate_days_left = tls_result.get("certificate_days_left")
        if tls_version is not None:
            tls_version_score = TLS_VERSION_SCORE_MAP.get(tls_version)
        if tls_version is not None and tls_version < 1.2:
            weak_tls = 1
        elif cipher and WEAK_CIPHER_PATTERNS.search(cipher):
            weak_tls = 1

    features = ScanFeatures(
        has_https=has_https,
        redirect_http_to_https=redirect_http_to_https,
        has_hsts=has_hsts,
        tls_version=tls_version,
        tls_version_score=tls_version_score,
        weak_tls=weak_tls,
        certificate_days_left=certificate_days_left,
        redirect_count=redirect_count,
        final_status_code=final_status_code,
        response_time=response_time,
        has_csp=has_csp,
        has_x_frame=has_x_frame,
        has_x_content_type=has_x_content_type,
        csp_has_unsafe_inline=csp_unsafe_inline,
        csp_has_unsafe_eval=csp_unsafe_eval,
        csp_has_default_self=csp_default_self,
        csp_has_object_none=csp_object_none,
        csp_has_default_src=csp_has_default_src,
        csp_unsafe_inline=csp_unsafe_inline_v3,
        csp_unsafe_eval=csp_unsafe_eval_v3,
        csp_has_wildcard=csp_has_wildcard,
        csp_score=csp_score,
        hsts_max_age_days=hsts_max_age_days,
        hsts_max_age=hsts_max_age_secs,
        hsts_long=hsts_long,
        hsts_include_subdomains=hsts_include_subdomains,
        hsts_preload=hsts_preload,
        has_referrer_policy=has_referrer_policy,
        referrer_policy_strict=referrer_policy_strict,
        has_permissions_policy=has_permissions_policy,
        has_coop=has_coop,
        has_coep=has_coep,
        has_corp=has_corp,
        server_header_present=server_header_present,
        x_powered_by_present=x_powered_by_present,
        cookie_secure=cookie_secure,
        cookie_httponly=cookie_httponly,
        cookie_samesite=cookie_samesite,
        total_cookie_count=total_cookie_count,
        secure_cookie_ratio=secure_cookie_ratio,
        httponly_cookie_ratio=httponly_cookie_ratio,
        samesite_cookie_ratio=samesite_cookie_ratio,
        cors_wildcard=cors_wildcard,
        cors_allows_credentials=cors_allows_credentials,
        cors_wildcard_with_credentials=cors_wildcard_with_credentials,
        status_is_2xx=status_is_2xx,
        status_is_3xx=status_is_3xx,
        status_is_4xx=status_is_4xx,
        status_is_5xx=status_is_5xx,
    )

    evidence = ScanEvidence(
        hsts_value=hsts_val,
        hsts_raw=hsts_val.strip() if hsts_val and hsts_val.strip() else None,
        hsts_max_age=hsts_max_age_secs,
        csp_value=csp_val,
        csp_raw=csp_val.strip() if csp_val and csp_val.strip() else None,
        x_frame_value=xfo_val,
        x_content_type_value=xct_val,
        acao_value=acao_val,
        acac_value=acac_val.strip() if acac_val and acac_val.strip() else None,
        set_cookie_values=set_cookie_values,
        tls_version_raw=tls_version_raw,
        cipher=cipher,
        http_probe_status=http_probe_status,
        http_probe_location=http_probe_location,
        http_probe_error=http_probe_error,
        referrer_policy_raw=referrer_policy_raw.strip() if referrer_policy_raw and referrer_policy_raw.strip() else None,
        coop_value=coop_val.strip() if coop_val and coop_val.strip() else None,
        coep_value=coep_val.strip() if coep_val and coep_val.strip() else None,
        corp_value=corp_val.strip() if corp_val and corp_val.strip() else None,
        permissions_policy_raw=permissions_policy_raw.strip() if permissions_policy_raw and permissions_policy_raw.strip() else None,
        powered_by_value=powered_by_val.strip() if powered_by_val and powered_by_val.strip() else None,
    )

    features_dict = features.model_dump()
    evidence_dict = evidence.model_dump()
    rule = compute_rule_score(features_dict, evidence_dict)

    return ScanResult(
        input_target=target,
        normalized_host=normalized.normalized_host,
        requested_url=requested_url,
        final_url=final_url,
        final_status_code=final_status_code,
        timing_ms=timing_ms,
        redirect_count=redirect_count,
        response_time=response_time,
        features=features,
        evidence=evidence,
        rule_score=rule["rule_score"],
        rule_grade=rule["rule_grade"],
        rule_label=rule["rule_label"],
        rule_reasons=rule["rule_reasons"],
    )
