"""Predictable API error envelope and safe unexpected-error handling."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel


class RequiredValue(BaseModel):
    value: str


def _assert_error_envelope(
    response,
    *,
    status_code: int,
    code: str,
) -> dict:
    assert response.status_code == status_code
    assert response.headers["content-type"].startswith("application/json")

    payload = response.json()
    assert set(payload) == {"error"}
    assert isinstance(payload["error"], dict)
    assert payload["error"]["code"] == code
    assert isinstance(payload["error"]["message"], str)
    assert payload["error"]["message"]
    return payload


@pytest.fixture
def app_with_temporary_routes() -> Iterator[FastAPI]:
    """Expose test-only routes without leaving them on the shared app."""

    from app.main import app

    original_routes = list(app.router.routes)
    try:
        yield app
    finally:
        app.router.routes[:] = original_routes


def test_missing_route_uses_predictable_error_envelope(
    client: TestClient,
) -> None:
    payload = _assert_error_envelope(
        client.get("/api/foundation/does-not-exist"),
        status_code=404,
        code="not_found",
    )

    assert "traceback" not in str(payload).lower()


def test_request_validation_uses_predictable_error_envelope(
    client: TestClient,
    app_with_temporary_routes: FastAPI,
) -> None:
    async def validation_probe(body: RequiredValue) -> dict[str, str]:
        return {"value": body.value}

    app_with_temporary_routes.add_api_route(
        "/api/foundation/validation-probe",
        validation_probe,
        methods=["POST"],
    )

    payload = _assert_error_envelope(
        client.post("/api/foundation/validation-probe", json={}),
        status_code=422,
        code="validation_error",
    )

    assert "traceback" not in str(payload).lower()


def test_unexpected_error_is_json_and_does_not_leak_exception_details(
    client: TestClient,
    app_with_temporary_routes: FastAPI,
) -> None:
    secret = "foundation-test-secret-do-not-leak"

    async def failure_probe() -> None:
        raise RuntimeError(secret)

    app_with_temporary_routes.add_api_route(
        "/api/foundation/failure-probe",
        failure_probe,
        methods=["GET"],
    )

    response = client.get("/api/foundation/failure-probe")
    payload = _assert_error_envelope(
        response,
        status_code=500,
        code="internal_error",
    )

    response_text = response.text.lower()
    assert secret not in response.text
    assert "runtimeerror" not in response_text
    assert "traceback" not in response_text
    assert secret not in str(payload)
