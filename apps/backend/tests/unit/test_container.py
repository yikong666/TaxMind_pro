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


async def test_default_container_reports_mysql_not_configured(test_settings: Settings) -> None:
    container = build_container(test_settings)

    results = await container.check_readiness()

    assert results["mysql"].status == "not_configured"
    assert wire_services(container) == {}


async def test_probe_failure_is_safely_mapped(test_settings: Settings) -> None:
    container = AppContainer(settings=test_settings, probes={"optional": BrokenProbe()})

    results = await container.check_readiness()

    assert results["optional"].status == "unhealthy"
    assert results["optional"].detail == "probe failed safely"