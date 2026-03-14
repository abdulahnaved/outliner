"""API tests: health and /api/scan validation (no live HTTP)."""
import pytest
from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_scan_requires_json(client: TestClient) -> None:
    r = client.post("/api/scan")
    assert r.status_code == 422


def test_scan_requires_target(client: TestClient) -> None:
    r = client.post("/api/scan", json={})
    assert r.status_code == 422


def test_scan_invalid_target(client: TestClient) -> None:
    r = client.post("/api/scan", json={"target": ""})
    assert r.status_code in (400, 422)


def test_scan_rejects_blocked_host(client: TestClient) -> None:
    """SSRF: localhost / private IP should be rejected unless explicitly allowed."""
    r = client.post("/api/scan", json={"target": "http://localhost/"})
    assert r.status_code == 400
    assert "not allowed" in r.json().get("detail", "").lower() or "invalid" in r.json().get("detail", "").lower()


def test_scan_rejects_invalid_target_format(client: TestClient) -> None:
    r = client.post("/api/scan", json={"target": "not a valid host"})
    # Either 400 (invalid target) or 422 (validation)
    assert r.status_code in (400, 422)
