from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Protocol

from taxmind.bootstrap.settings import Settings


@dataclass(frozen=True, slots=True)
class ProbeResult:
    status: str
    detail: str

    @property
    def healthy(self) -> bool:
        return self.status == "healthy"


class ReadinessProbe(Protocol):
    name: str
    required: bool

    async def startup(self) -> None: ...

    async def shutdown(self) -> None: ...

    async def check(self) -> ProbeResult: ...


@dataclass(slots=True)
class NotConfiguredProbe:
    name: str
    required: bool = True

    async def startup(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None

    async def check(self) -> ProbeResult:
        return ProbeResult(status="not_configured", detail="adapter is planned for phase 3")


@dataclass(slots=True)
class AppContainer:
    settings: Settings
    probes: dict[str, ReadinessProbe] = field(default_factory=dict)

    async def startup(self) -> None:
        for probe in self.probes.values():
            await probe.startup()

    async def shutdown(self) -> None:
        for probe in reversed(tuple(self.probes.values())):
            await probe.shutdown()

    async def check_readiness(self) -> dict[str, ProbeResult]:
        results: dict[str, ProbeResult] = {}
        for name, probe in self.probes.items():
            try:
                results[name] = await probe.check()
            except Exception:
                results[name] = ProbeResult(status="unhealthy", detail="probe failed safely")
        return results


ServiceRegistry = Mapping[str, object]


def build_container(
    settings: Settings,
    *,
    probes: Sequence[ReadinessProbe] | None = None,
) -> AppContainer:
    selected = tuple(probes) if probes is not None else (NotConfiguredProbe(name="mysql"),)
    return AppContainer(settings=settings, probes={probe.name: probe for probe in selected})


def wire_services(container: AppContainer) -> ServiceRegistry:
    del container
    return MappingProxyType({})