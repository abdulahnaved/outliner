from __future__ import annotations

import os
import ipaddress


def is_blocked_host(hostname: str) -> bool:
  """
  Minimal SSRF guard.

  - Block localhost and *.local
  - Block private / loopback IPv4 ranges and 0.0.0.0

  Dev-only: set OUTLINER_ALLOW_LOCALHOST=true to allow localhost/private IPs
  (e.g. for scanning lab targets). Secure by default.
  """
  host = (hostname or "").strip().lower()
  if not host:
    return True

  # Dev-only bypass: allow localhost and private IPs for lab testing
  allow_local = os.getenv("OUTLINER_ALLOW_LOCALHOST", "").strip().lower() in ("true", "1", "yes")
  if allow_local:
    if host == "localhost" or host.endswith(".local"):
      return False
    try:
      ip = ipaddress.ip_address(host)
      if ip.is_loopback or ip.is_private or ip == ipaddress.ip_address("0.0.0.0"):
        return False
    except ValueError:
      pass

  # Obvious local names
  if host == "localhost" or host.endswith(".local"):
    return True

  # Check if it's an IP literal
  try:
    ip = ipaddress.ip_address(host)
  except ValueError:
    # Not an IP, treat as regular hostname
    return False

  # Block loopback (e.g. 127.0.0.1)
  if ip.is_loopback:
    return True

  # Block private ranges (10/8, 172.16/12, 192.168/16)
  if ip.is_private:
    return True

  # Block unspecified address
  if ip == ipaddress.ip_address("0.0.0.0"):
    return True

  return False
