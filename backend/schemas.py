from typing import Any, Dict, List, Literal, Optional

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
  # Transport (v2 + v3)
  has_https: int = 0
  redirect_http_to_https: int = 0
  has_hsts: int = 0
  tls_version: Optional[float] = None
  tls_version_score: Optional[float] = None
  weak_tls: int = 0
  certificate_days_left: Optional[int] = None
  redirect_count: int = 0
  final_status_code: Optional[int] = None
  response_time: float = 0.0
  # Client-side headers
  has_csp: int = 0
  has_x_frame: int = 0
  has_x_content_type: int = 0
  # CSP quality v2
  csp_has_unsafe_inline: int = 0
  csp_has_unsafe_eval: int = 0
  csp_has_default_self: int = 0
  csp_has_object_none: int = 0
  # CSP quality v3
  csp_has_default_src: int = 0
  csp_unsafe_inline: int = 0
  csp_unsafe_eval: int = 0
  csp_has_wildcard: int = 0
  csp_score: float = 0.0
  # HSTS strength
  hsts_max_age_days: Optional[float] = None
  hsts_max_age: Optional[int] = None  # seconds (v3)
  hsts_long: int = 0  # max-age >= 180 days
  hsts_include_subdomains: int = 0
  hsts_preload: int = 0
  # Policy headers
  has_referrer_policy: int = 0
  referrer_policy_strict: int = 0
  has_permissions_policy: int = 0
  has_coop: int = 0
  has_coep: int = 0
  has_corp: int = 0
  # Server exposure
  server_header_present: int = 0
  x_powered_by_present: int = 0
  # Session (Set-Cookie)
  cookie_secure: int = 0
  cookie_httponly: int = 0
  cookie_samesite: int = 0
  total_cookie_count: int = 0
  secure_cookie_ratio: float = 0.0
  httponly_cookie_ratio: float = 0.0
  samesite_cookie_ratio: float = 0.0
  # CORS
  cors_wildcard: int = 0
  cors_allows_credentials: int = 0
  cors_wildcard_with_credentials: int = 0
  # Status buckets
  status_is_2xx: int = 0
  status_is_3xx: int = 0
  status_is_4xx: int = 0
  status_is_5xx: int = 0


class ScanEvidence(BaseModel):
  hsts_value: Optional[str] = None
  hsts_raw: Optional[str] = None
  hsts_max_age: Optional[int] = None
  csp_value: Optional[str] = None
  csp_raw: Optional[str] = None
  x_frame_value: Optional[str] = None
  x_content_type_value: Optional[str] = None
  acao_value: Optional[str] = None
  acac_value: Optional[str] = None
  set_cookie_values: List[str] = Field(default_factory=list)
  tls_version_raw: Optional[str] = None
  cipher: Optional[str] = None
  http_probe_status: Optional[int] = None
  http_probe_location: Optional[str] = None
  http_probe_error: Optional[str] = None
  referrer_policy_raw: Optional[str] = None
  coop_value: Optional[str] = None
  coep_value: Optional[str] = None
  corp_value: Optional[str] = None
  permissions_policy_raw: Optional[str] = None
  powered_by_value: Optional[str] = None


# Allowed scan status values for graceful degradation.
# (Partial removed: failed targets are always represented as scan_status="failed".)
ScanStatus = Literal["success", "failed"]


class ScoreContext(BaseModel):
  distribution_scores: List[float] = Field(default_factory=list)
  dataset_median: Optional[float] = None
  dataset_average: Optional[float] = None
  percentile: Optional[float] = None


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
  # Rule-based score; null when scan failed or scoring not available
  rule_score: Optional[float] = None
  rule_grade: Optional[str] = None
  rule_label: Optional[int] = None
  rule_reasons: List[str] = Field(default_factory=list)
  # ML prediction (additive; scan succeeds even when prediction unavailable)
  prediction_available: bool = False
  predicted_rule_score: Optional[float] = None
  ml_model_name: Optional[str] = None
  ml_model_variant: Optional[str] = None
  prediction_error: Optional[str] = None
  # Scan status and error info (for failed/unreachable targets)
  scan_status: ScanStatus = "success"
  scan_error_type: Optional[str] = None  # timeout, dns_error, tls_error, connection_error, http_error, blocked, unknown
  scan_error_message: Optional[str] = None
  is_blocked: Optional[int] = None  # preserved when known (e.g. from partial/failed context)
  score_context: Optional[ScoreContext] = None


