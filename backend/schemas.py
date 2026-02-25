from typing import Any, Dict, List

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


