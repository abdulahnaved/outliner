from __future__ import annotations

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from schemas import FetchRequest, FetchResponse, HealthResponse, ScanRequest, ScanResult
from utils.normalize import normalize_target
from utils.ssrf import is_blocked_host
from services.fetch import perform_fetch
from services.passive_scan import perform_passive_scan

# Dataset persistence is done only by batch_scan.py; /api/scan returns JSON only.

TAGS = [
  {"name": "system", "description": "Service status and health endpoints."},
  {"name": "scan", "description": "Passive fetch and scan endpoints."},
]

app = FastAPI(
  title="Outliner Scanner API",
  description=(
    "Academic demo backend for Outliner.\n\n"
    "Performs **passive** web security inspection (headers/TLS/cookies/redirects), computes a deterministic rule score, "
    "and optionally adds an ML-estimated score plus a distance-to-training reliability label.\n\n"
    "Interactive docs are available at `/docs`."
  ),
  version="0.1.0",
  docs_url="/docs",
  openapi_url="/openapi.json",
  openapi_tags=TAGS,
)

app.add_middleware(
  CORSMiddleware,
  allow_origins=["http://localhost:3000"],
  allow_credentials=False,
  allow_methods=["*"],
  allow_headers=["*"],
)


@app.get(
  "/health",
  response_model=HealthResponse,
  tags=["system"],
  summary="Health check",
  description="Simple liveness check for the API process. Does not call any external services.",
  response_description="API is running.",
)
async def health() -> HealthResponse:
  return HealthResponse(ok=True)


@app.post(
  "/api/fetch",
  response_model=FetchResponse,
  tags=["scan"],
  summary="Fetch a URL (headers + redirects)",
  description=(
    "Fetch a single target and return raw response headers and the redirect chain.\n\n"
    "Includes minimal normalization and a small SSRF guard. This endpoint is a building block for scanning."
  ),
  response_description="Fetch result including headers and redirect chain.",
  responses={
    400: {"description": "Invalid target or target not allowed."},
    502: {"description": "Upstream fetch failed."},
    504: {"description": "Upstream fetch timed out."},
  },
)
async def api_fetch(payload: FetchRequest) -> FetchResponse:
  # Normalize target
  try:
    normalized = normalize_target(payload.target)
  except ValueError:
    raise HTTPException(status_code=400, detail="Invalid target")

  host = normalized.normalized_host

  # Minimal SSRF guard
  if is_blocked_host(host):
    raise HTTPException(status_code=400, detail="Target not allowed")

  # Perform HTTP fetch
  try:
    fetch_result = await perform_fetch(normalized.requested_url)
  except httpx.TimeoutException:
    raise HTTPException(status_code=504, detail="Fetch timeout")
  except httpx.HTTPError:
    raise HTTPException(status_code=502, detail="Fetch failed")

  response_payload = FetchResponse(
    input_target=payload.target,
    normalized_host=normalized.normalized_host,
    requested_url=normalized.requested_url,
    final_url=fetch_result["final_url"],
    status_code=fetch_result["status_code"],
    timing_ms=fetch_result["timing_ms"],
    redirect_chain=fetch_result["redirect_chain"],
    headers=fetch_result["headers"],
  )

  return response_payload


@app.post(
  "/api/scan",
  response_model=ScanResult,
  tags=["scan"],
  summary="Run a passive security scan",
  description=(
    "Run Outliner’s passive scan pipeline on one target.\n\n"
    "- Validates + normalizes the target\n"
    "- Performs a fetch (following redirects)\n"
    "- Extracts passive security features (TLS, headers, cookies, CORS)\n"
    "- Computes a deterministic rule-based score\n"
    "- Optionally adds an ML-estimated score and reliability label\n\n"
    "For unreachable targets, the API returns **200** with `scan_status=\"failed\"` (scores may be null). "
    "Only invalid/blocked targets return 400."
  ),
  response_description="Scan result: features, evidence snapshot, rule score, and optional ML estimate.",
  responses={
    400: {"description": "Invalid target or target not allowed (SSRF guard)."},
  },
)
async def api_scan(payload: ScanRequest) -> ScanResult:
  # Only invalid target / SSRF raise; unreachable targets return 200 with scan_status="failed"
  try:
    result = await perform_passive_scan(payload.target)
  except ValueError as e:
    msg = str(e)
    if "Invalid target" in msg or "invalid" in msg.lower():
      raise HTTPException(status_code=400, detail="Invalid target")
    if "not allowed" in msg.lower():
      raise HTTPException(status_code=400, detail="Target not allowed")
    raise HTTPException(status_code=400, detail=msg)
  return result
