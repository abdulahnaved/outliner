"""
Phase 2 passive scanner: 15 features from headers, TLS, cookies, CORS, behavior.
"""
from __future__ import annotations

import os
import re
import ssl
import socket
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx

from schemas import ScanEvidence, ScanFeatures, ScanResult


USER_AGENT = "Outliner/0.1 (research)"
TIMEOUT_SECONDS = 15.0
WEAK_CIPHER_PATTERNS = re.compile(
    r"RC4|3DES|DES|NULL|EXPORT|MD5", re.IGNORECASE
)
TLS_VERSION_MAP = {
    "TLSv1": 1.0,
    "TLSv1.1": 1.1,
    "TLSv1.2": 1.2,
    "TLSv1.3": 1.3,
}
TLS_VERSION_SCORE_MAP = {
    1.0: 0.0,
    1.1: 0.2,
    1.2: 0.7,
    1.3: 1.0,
}


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
    try:
        return parsedate_to_datetime(not_after)
    except Exception:
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

    # 3) redirect_http_to_https
    redirect_http_to_https = 0
    try:
        async with httpx.AsyncClient(
            verify=not skip_verify,
            timeout=TIMEOUT_SECONDS,
            follow_redirects=False,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            r = await client.get(http_url)
            if 300 <= r.status_code < 400:
                loc = _get_header(r.headers, "location") or ""
                if loc.strip().lower().startswith("https://"):
                    redirect_http_to_https = 1
    except Exception:
        pass

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

    # 6) Cookie features
    cookie_secure = 0
    cookie_httponly = 0
    cookie_samesite = 0
    for raw in set_cookie_values:
        raw_lower = raw.lower()
        if "secure" in raw_lower:
            cookie_secure = 1
        if "httponly" in raw_lower:
            cookie_httponly = 1
        if "samesite=" in raw_lower:
            cookie_samesite = 1

    # 7) TLS features (only when has_https)
    tls_version: Optional[float] = None
    tls_version_score: Optional[float] = None
    weak_tls = 0
    certificate_days_left: Optional[int] = None
    tls_version_raw: Optional[str] = None
    cipher: Optional[str] = None

    if has_https == 1 and final_url:
        h, p = _host_port_from_url(final_url)
        if "https" in final_url:
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
        has_csp=has_csp,
        has_x_frame=has_x_frame,
        has_x_content_type=has_x_content_type,
        cookie_secure=cookie_secure,
        cookie_httponly=cookie_httponly,
        cookie_samesite=cookie_samesite,
        cors_wildcard=cors_wildcard,
        redirect_count=redirect_count,
        final_status_code=final_status_code,
        response_time=response_time,
    )

    evidence = ScanEvidence(
        hsts_value=hsts_val,
        csp_value=csp_val,
        x_frame_value=xfo_val,
        x_content_type_value=xct_val,
        acao_value=acao_val,
        set_cookie_values=set_cookie_values,
        tls_version_raw=tls_version_raw,
        cipher=cipher,
    )

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
    )
