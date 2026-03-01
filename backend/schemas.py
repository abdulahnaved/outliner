from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FetchRequest(BaseModel):
  target: str = Field(..., description="Target domain or URL to fetch")


class RedirectEntry(BaseModel):
  url: str
  status_code: int


class FetchResponse(BaseModel):
  input_target: str
  normalized_host: str
  requested_url: str
  final_url: str
  status_code: int
  timing_ms: int
  redirect_chain: List[RedirectEntry]
  headers: Dict[str, Any]


# --- Phase 2 Scan ---

class ScanRequest(BaseModel):
  target: str = Field(..., description="Target domain or URL to scan")


class ScanFeatures(BaseModel):
  # Transport
  has_https: int = 0
  has_hsts: int = 0
  tls_version: Optional[float] = None
  certificate_days_left: Optional[int] = None
  redirect_count: int = 0
  response_time: float = 0.0
  # Client-side headers
  has_csp: int = 0
  has_x_frame: int = 0
  has_x_content_type: int = 0
  # CSP quality (0/1; all 0 if no CSP)
  csp_has_unsafe_inline: int = 0
  csp_has_unsafe_eval: int = 0
  csp_has_default_self: int = 0
  csp_has_object_none: int = 0
  # HSTS strength
  hsts_max_age_days: Optional[float] = None
  hsts_include_subdomains: int = 0
  hsts_preload: int = 0
  # Policy headers (presence)
  has_referrer_policy: int = 0
  has_permissions_policy: int = 0
  # Server exposure (presence only)
  server_header_present: int = 0
  x_powered_by_present: int = 0
  # Session (Set-Cookie) base flags
  cookie_secure: int = 0
  cookie_httponly: int = 0
  cookie_samesite: int = 0
  # Cookie depth
  total_cookie_count: int = 0
  secure_cookie_ratio: float = 0.0
  httponly_cookie_ratio: float = 0.0
  samesite_cookie_ratio: float = 0.0
  # CORS
  cors_wildcard: int = 0
  # Status buckets (from final_status_code)
  status_is_2xx: int = 0
  status_is_3xx: int = 0
  status_is_4xx: int = 0
  status_is_5xx: int = 0


class ScanEvidence(BaseModel):
  hsts_value: Optional[str] = None
  csp_value: Optional[str] = None
  x_frame_value: Optional[str] = None
  x_content_type_value: Optional[str] = None
  acao_value: Optional[str] = None
  set_cookie_values: List[str] = Field(default_factory=list)
  tls_version_raw: Optional[str] = None
  cipher: Optional[str] = None
  # HTTP probe for redirect_http_to_https
  http_probe_status: Optional[int] = None
  http_probe_location: Optional[str] = None
  http_probe_error: Optional[str] = None


class ScanResult(BaseModel):
  input_target: str
  normalized_host: str
  requested_url: str
  final_url: Optional[str] = None
  final_status_code: Optional[int] = None
  timing_ms: Optional[int] = None
  redirect_count: int = 0
  response_time: float = 0.0
  features: ScanFeatures
  evidence: Optional[ScanEvidence] = None


