from __future__ import annotations

import ipaddress


def is_blocked_host(hostname: str) -> bool:
  """
  Minimal SSRF guard.

  - Block localhost and *.local
  - Block private / loopback IPv4 ranges and 0.0.0.0
  """
  host = (hostname or "").strip().lower()
  if not host:
    return True

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


