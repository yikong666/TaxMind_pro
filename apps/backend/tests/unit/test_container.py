from __future__ import annotations

from dataclasses import dataclass

from taxmind.bootstrap.container import AppContainer, ProbeResult, build_container, wire_services
from taxmind.bootstrap.settings import Settings


@dataclass
class BrokenProbe:
    name: str = "optional"
    required: bool = False

    async def startup(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None

    async def check(self) -> ProbeResult:
        raise RuntimeError("private infrastructure detail")


async def test_default_container_wires_identity_service_without_connecting_mysql(
    test_settings: Settings,
) -> None:
    container = build_container(test_settings)

    results = await container.check_readiness()

    assert results["mysql"].status == "not_configured"
    assert "identity" in wire_services(container)
    assert "conversations" in wire_services(container)
    assert "documents" in wire_services(container)
    assert "sources" in wire_services(container)
    assert "manual_import" in wire_services(container)
    await container.shutdown()


async def test_probe_failure_is_safely_mapped(test_settings: Settings) -> None:
    container = AppContainer(settings=test_settings, probes={"optional": BrokenProbe()})

    results = await container.check_readiness()

    assert results["optional"].status == "unhealthy"
    assert results["optional"].detail == "probe failed safely"
