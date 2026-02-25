from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Tuple
from urllib.parse import urlparse


@dataclass
class NormalizedTarget:
  normalized_host: str
  requested_url: str


_HOST_PATTERN = re.compile(r"^[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def _validate_hostname(hostname: str) -> bool:
  if not hostname:
    return False
  if len(hostname) > 253:
    return False
  return bool(_HOST_PATTERN.fullmatch(hostname))


def normalize_target(raw: str) -> NormalizedTarget:
  """
  Normalize an input domain/URL into:
  - normalized_host: hostname without leading www.
  - requested_url: scheme://hostname/
  """
  value = (raw or "").strip()
  if not value:
    raise ValueError("empty target")

  # If no scheme, assume https.
  if not value.lower().startswith(("http://", "https://")):
    value = f"https://{value}"

  parsed = urlparse(value)
  scheme = parsed.scheme.lower()
  if scheme not in ("http", "https"):
    raise ValueError("unsupported scheme")

  hostname = parsed.hostname or ""
  hostname = hostname.lower()

  if hostname.startswith("www."):
    hostname = hostname[4:]

  if not _validate_hostname(hostname):
    raise ValueError("invalid hostname")

  requested_url = f"{scheme}://{hostname}/"

  return NormalizedTarget(normalized_host=hostname, requested_url=requested_url)


