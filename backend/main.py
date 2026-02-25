from __future__ import annotations

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from schemas import FetchRequest, FetchResponse
from utils.normalize import normalize_target
from utils.ssrf import is_blocked_host
from services.fetch import perform_fetch


app = FastAPI(title="Outliner Backend", version="0.1.0")

app.add_middleware(
  CORSMiddleware,
  allow_origins=["http://localhost:3000"],
  allow_credentials=False,
  allow_methods=["*"],
  allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
  return {"ok": True}


@app.post("/api/fetch", response_model=FetchResponse)
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


