from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
  ok: bool = Field(..., description="Health check flag. True means the API process is running.")


class FetchRequest(BaseModel):
  target: str = Field(..., description="Target domain or URL to fetch (e.g. example.com or https://example.com).")


class RedirectEntry(BaseModel):
  url: str = Field(..., description="URL in the redirect chain.")
  status_code: int = Field(..., description="HTTP status code returned for this redirect step.")


class FetchResponse(BaseModel):
  input_target: str = Field(..., description="Original user input target.")
  normalized_host: str = Field(..., description="Normalized hostname derived from the input target.")
  requested_url: str = Field(..., description="URL that was requested (after normalization).")
  final_url: str = Field(..., description="Final URL after following redirects.")
  status_code: int = Field(..., description="HTTP status code of the final response.")
  timing_ms: int = Field(..., description="Total fetch time in milliseconds.")
  redirect_chain: List[RedirectEntry] = Field(default_factory=list, description="Redirect chain (may be empty).")
  headers: Dict[str, Any] = Field(default_factory=dict, description="Response headers as a dictionary.")


# --- Phase 2 Scan ---

class ScanRequest(BaseModel):
  target: str = Field(..., description="Target domain or URL to scan (e.g. example.com or https://example.com).")


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
  distribution_scores: List[float] = Field(
    default_factory=list,
    description="Historical rule-score distribution used to compute percentile (rule scale)."
  )
  dataset_median: Optional[float] = Field(default=None, description="Median of the historical rule-score distribution.")
  dataset_average: Optional[float] = Field(default=None, description="Average of the historical rule-score distribution.")
  percentile: Optional[float] = Field(default=None, description="Percentile position of this scan in the historical rule-score distribution.")


class ScanResult(BaseModel):
  input_target: str = Field(..., description="Original user input target.")
  normalized_host: str = Field(..., description="Normalized hostname derived from the input target.")
  requested_url: str = Field(..., description="URL that was requested (after normalization).")
  final_url: Optional[str] = Field(default=None, description="Final URL after redirects (if reached).")
  final_status_code: Optional[int] = Field(default=None, description="Final HTTP status code (if reached).")
  timing_ms: Optional[int] = Field(default=None, description="Total scan time in milliseconds (if measured).")
  redirect_count: int = Field(default=0, description="Number of redirects followed during scanning.")
  response_time: float = Field(default=0.0, description="Response time in seconds for the final fetch (when available).")
  features: ScanFeatures = Field(..., description="Extracted passive security features used for scoring and ML.")
  evidence: Optional[ScanEvidence] = Field(default=None, description="Raw evidence snapshot (headers/TLS/cookies) when available.")
  # Rule-based score (v2 = primary; null when scan failed or scoring not available)
  rule_score: Optional[float] = Field(default=None, description="Deterministic rule-based score (primary baseline).")
  rule_grade: Optional[str] = Field(default=None, description="Grade mapped from the rule_score (e.g. A+, B, C).")
  rule_label: Optional[int] = Field(default=None, description="Rule label (legacy or derived mapping used in earlier versions).")
  rule_reasons: List[str] = Field(default_factory=list, description="Short reasons produced by the rule engine.")
  # V2 explicit fields (same as above when v2 is primary; kept for API clarity)
  rule_score_v2: Optional[float] = None
  rule_grade_v2: Optional[str] = None
  rule_label_v2: Optional[int] = None
  rule_reasons_v2: List[str] = Field(default_factory=list)
  # V3 legacy (optional, for comparison/debugging)
  rule_score_v3: Optional[float] = None
  rule_grade_v3: Optional[str] = None
  rule_label_v3: Optional[int] = None
  rule_reasons_v3: List[str] = Field(default_factory=list)
  # ML prediction (additive; scan succeeds even when prediction unavailable)
  prediction_available: bool = Field(default=False, description="Whether the ML model produced a prediction.")
  predicted_rule_score: Optional[float] = Field(default=None, description="ML-predicted rule-like score (0–110 scale).")
  ml_model_name: Optional[str] = Field(default=None, description="ML model family name (for transparency).")
  ml_model_variant: Optional[str] = Field(default=None, description="ML model variant identifier (for transparency).")
  prediction_error: Optional[str] = Field(default=None, description="Prediction failure reason, if prediction_available=false due to an error.")
  # ML reliability (additive; careful wording; derived from distance-to-training when available)
  prediction_reliability: Optional[Literal["higher", "moderate", "lower"]] = Field(
    default=None,
    description="Reliability tier for the ML estimate based on distance-to-training (higher/moderate/lower)."
  )
  prediction_reliability_reason: Optional[str] = Field(
    default=None,
    description="Human-readable explanation of the ML reliability tier (includes avg neighbor distance when available)."
  )
  # Scan status and error info (for failed/unreachable targets)
  scan_status: ScanStatus = Field(default="success", description='Scan status: "success" or "failed".')
  scan_error_type: Optional[str] = Field(
    default=None,
    description="If failed: high-level error type (timeout, dns_error, tls_error, connection_error, http_error, blocked, unknown)."
  )
  scan_error_message: Optional[str] = Field(default=None, description="If failed: a short error message for debugging/demo.")
  is_blocked: Optional[int] = Field(default=None, description="Whether the target was blocked by SSRF guard (when known).")
  score_context: Optional[ScoreContext] = Field(default=None, description="Optional dataset context (distribution + percentile) for the rule score.")


