from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
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
    services: dict[str, object] = field(default_factory=dict)
    shutdown_callbacks: list[Callable[[], Awaitable[None]]] = field(default_factory=list)

    async def startup(self) -> None:
        for probe in self.probes.values():
            await probe.startup()

    async def shutdown(self) -> None:
        for probe in reversed(tuple(self.probes.values())):
            await probe.shutdown()
        for callback in reversed(self.shutdown_callbacks):
            await callback()

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
    from taxmind.infrastructure.mysql.session import create_engine, session_factory
    from taxmind.modules.cases.application.service import CasesService
    from taxmind.modules.cases.infrastructure.uow import SqlAlchemyCasesUnitOfWorkFactory
    from taxmind.modules.conversations.application.service import ConversationsService
    from taxmind.modules.conversations.infrastructure.memory import RedisShortMemoryAdapter
    from taxmind.modules.conversations.infrastructure.uow import (
        SqlAlchemyConversationsUnitOfWorkFactory,
    )
    from taxmind.modules.documents.application.service import DocumentsService
    from taxmind.modules.documents.infrastructure.uow import SqlAlchemyDocumentsUnitOfWorkFactory
    from taxmind.modules.identity.application.service import IdentityService
    from taxmind.modules.identity.infrastructure.security import (
        Argon2PasswordService,
        JwtTokenService,
    )
    from taxmind.modules.identity.infrastructure.uow import SqlAlchemyIdentityUnitOfWorkFactory

    engine = create_engine(settings)
    identity_service = IdentityService(
        settings=settings,
        uow_factory=SqlAlchemyIdentityUnitOfWorkFactory(session_factory(engine)),
        password_service=Argon2PasswordService(),
        token_service=JwtTokenService(settings),
    )
    sessions = session_factory(engine)
    cases_service = CasesService(uow_factory=SqlAlchemyCasesUnitOfWorkFactory(sessions))
    from redis.asyncio import Redis

    redis_client = Redis.from_url(settings.redis_url)
    short_memory = RedisShortMemoryAdapter(
        redis_client,
        ttl_seconds=settings.short_memory_ttl_seconds,
    )
    conversations_service = ConversationsService(
        uow_factory=SqlAlchemyConversationsUnitOfWorkFactory(sessions),
        cases_service=cases_service,
        short_memory=short_memory,
        recent_message_limit=settings.short_memory_recent_message_limit,
    )
    documents_service = DocumentsService(uow_factory=SqlAlchemyDocumentsUnitOfWorkFactory(sessions))
    return AppContainer(
        settings=settings,
        probes={probe.name: probe for probe in selected},
        services={
            "identity": identity_service,
            "cases": cases_service,
            "conversations": conversations_service,
            "documents": documents_service,
        },
        shutdown_callbacks=[short_memory.close, engine.dispose],
    )


def wire_services(container: AppContainer) -> ServiceRegistry:
    return MappingProxyType(container.services)
