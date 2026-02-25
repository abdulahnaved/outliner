from __future__ import annotations

import time
from typing import Any, Dict, List, Union

import httpx


USER_AGENT = "Outliner/0.1 (research)"
TIMEOUT_SECONDS = 15.0


async def perform_fetch(requested_url: str) -> Dict[str, Any]:
  start = time.perf_counter()

  async with httpx.AsyncClient(
    follow_redirects=True,
    timeout=TIMEOUT_SECONDS,
    headers={"User-Agent": USER_AGENT},
  ) as client:
    response = await client.get(requested_url)

  elapsed_ms = int((time.perf_counter() - start) * 1000)

  # Build redirect chain from history plus final response
  chain = []
  for r in list(response.history) + [response]:
    chain.append(
      {
        "url": str(r.url),
        "status_code": r.status_code,
      }
    )

  # Normalize headers, preserving multiple values as lists (e.g. set-cookie)
  headers: Dict[str, Union[str, List[str]]] = {}
  for key, value in response.headers.multi_items():
    k = key.lower()
    existing = headers.get(k)
    if existing is None:
      headers[k] = value
    else:
      if isinstance(existing, list):
        existing.append(value)
      else:
        headers[k] = [existing, value]

  return {
    "final_url": str(response.url),
    "status_code": response.status_code,
    "timing_ms": elapsed_ms,
    "redirect_chain": chain,
    "headers": headers,
  }


