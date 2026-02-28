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
  redirect_http_to_https: int = 0
  has_hsts: int = 0
  tls_version: Optional[float] = None
  tls_version_score: Optional[float] = None
  weak_tls: int = 0
  certificate_days_left: Optional[int] = None
  # Client-side
  has_csp: int = 0
  has_x_frame: int = 0
  has_x_content_type: int = 0
  # Session (Set-Cookie)
  cookie_secure: int = 0
  cookie_httponly: int = 0
  cookie_samesite: int = 0
  # CORS
  cors_wildcard: int = 0
  # Behavior (repeated for convenience)
  redirect_count: int = 0
  final_status_code: Optional[int] = None
  response_time: float = 0.0


class ScanEvidence(BaseModel):
  hsts_value: Optional[str] = None
  csp_value: Optional[str] = None
  x_frame_value: Optional[str] = None
  x_content_type_value: Optional[str] = None
  acao_value: Optional[str] = None
  set_cookie_values: List[str] = Field(default_factory=list)
  tls_version_raw: Optional[str] = None
  cipher: Optional[str] = None


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


