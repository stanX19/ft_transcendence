"""Evaluator-visible health endpoint contract."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_is_public_and_returns_simple_success_payload(
    client: TestClient,
) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"status": "ok"}
