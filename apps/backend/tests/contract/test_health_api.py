from __future__ import annotations

from dataclasses import dataclass

from fastapi import Query
from fastapi.testclient import TestClient

from taxmind.bootstrap.container import AppContainer, ProbeResult
from taxmind.bootstrap.settings import Settings
from taxmind.entrypoints.api.main import create_app
from taxmind.shared.domain.errors import DomainError


@dataclass
class HealthyProbe:
    name: str = "mysql"
    required: bool = True

    async def startup(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None

    async def check(self) -> ProbeResult:
        return ProbeResult(status="healthy", detail="test double")


def test_liveness_returns_envelope_and_request_id(test_settings: Settings) -> None:
    app = create_app(test_settings)

    with TestClient(app) as client:
        response = client.get("/health/live", headers={"X-Request-Id": "client-request-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-Id"] == "client-request-123"
    assert response.json()["data"]["status"] == "live"
    assert response.json()["meta"]["request_id"] == "client-request-123"


def test_readiness_is_not_ready_before_infrastructure_phase(test_settings: Settings) -> None:
    app = create_app(test_settings)

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["data"]["status"] == "not_ready"
    assert response.json()["data"]["dependencies"]["mysql"]["status"] == "not_configured"


def test_readiness_is_ready_with_healthy_required_probe(test_settings: Settings) -> None:
    container = AppContainer(settings=test_settings, probes={"mysql": HealthyProbe()})
    app = create_app(test_settings, container=container)

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ready"


def test_version_does_not_expose_internal_addresses(test_settings: Settings) -> None:
    app = create_app(test_settings)

    with TestClient(app) as client:
        response = client.get("/health/version")

    assert response.status_code == 200
    assert response.json()["data"] == {
        "app_version": "0.1.0",
        "build_sha": "test-build",
        "contract_version": "v1",
    }
    assert "mysql_host" not in response.text


def test_domain_error_uses_safe_error_envelope(test_settings: Settings) -> None:
    app = create_app(test_settings)

    @app.get("/test/domain-error")
    async def domain_error() -> None:
        raise DomainError(code="RESOURCE_NOT_FOUND", message="资源不存在")

    with TestClient(app) as client:
        response = client.get("/test/domain-error")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert "traceback" not in response.text.lower()


def test_validation_error_does_not_echo_input(test_settings: Settings) -> None:
    app = create_app(test_settings)

    @app.get("/test/validation")
    async def validation(limit: int = Query(gt=0)) -> dict[str, int]:
        return {"limit": limit}

    with TestClient(app) as client:
        response = client.get("/test/validation", params={"limit": "sensitive-invalid-input"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"
    assert "sensitive-invalid-input" not in response.text


def test_unexpected_error_is_hidden(test_settings: Settings) -> None:
    app = create_app(test_settings)

    @app.get("/test/unexpected")
    async def unexpected() -> None:
        raise RuntimeError("database-password=should-not-leak")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/test/unexpected")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "should-not-leak" not in response.text


def test_openapi_contains_health_contract_without_starting_dependencies(
    test_settings: Settings,
) -> None:
    schema = create_app(test_settings).openapi()

    assert "/health/live" in schema["paths"]
    assert "/health/ready" in schema["paths"]
    assert "/health/version" in schema["paths"]
