from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from taxmind.modules.sources.application.service import (
    RegisterSourceSiteCommand,
    SourcesService,
)
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.principal import Principal


class _StubUnitOfWork:
    def __init__(self, repository: AsyncMock) -> None:
        self.repository = repository
        self.commit = AsyncMock()

    async def __aenter__(self) -> _StubUnitOfWork:
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


def _principal(*permissions: str) -> Principal:
    return Principal(
        user_id="018f4cc1-7852-7d5d-8c1c-dbd404e8b101",
        org_id="018f4cc1-7852-7d5d-8c1c-dbd404e8b102",
        session_id="018f4cc1-7852-7d5d-8c1c-dbd404e8b103",
        roles=frozenset({"knowledge_admin"}),
        permissions=frozenset(permissions),
    )


def _command(**overrides: object) -> RegisterSourceSiteCommand:
    values: dict[str, object] = {
        "name": "虚构国家税务机关公开站点",
        "base_url": "https://EXAMPLE.invalid/policies/",
        "source_level": "A",
        "authority_name": "虚构国家税务机关",
        "region_code": "000000",
        "collection_method": "manual",
        "whitelist_rules": {"allowed_paths": ["/policies"]},
        "crawl_interval_minutes": None,
        "request_id": "request-stage5-source",
    }
    values.update(overrides)
    return RegisterSourceSiteCommand(**values)  # type: ignore[arg-type]


async def test_register_source_creates_audited_draft_with_normalized_url() -> None:
    repository = AsyncMock()
    repository.get_by_scope.return_value = None
    uow = _StubUnitOfWork(repository)
    service = SourcesService(uow_factory=lambda: uow)  # type: ignore[arg-type]

    source = await service.register_source(
        _command(),
        _principal("knowledge:write"),
    )

    assert source.base_url == "https://example.invalid/policies"
    assert source.domain == "example.invalid"
    assert source.status == "draft"
    repository.create_source.assert_awaited_once_with(source)
    repository.create_audit_log.assert_awaited_once()
    uow.commit.assert_awaited_once()


@pytest.mark.parametrize(
    ("overrides", "message_part"),
    [
        ({"base_url": "http://example.invalid"}, "HTTPS"),
        ({"base_url": "https://127.0.0.1"}, "IP"),
        ({"base_url": "https://example.invalid:8443"}, "HTTPS"),
        (
            {
                "collection_method": "whitelist_crawl",
                "crawl_interval_minutes": 30,
            },
            "60",
        ),
        ({"whitelist_rules": {"headers": {"x-auth": "unsafe"}}}, "密钥"),
    ],
)
async def test_register_source_rejects_unsafe_or_noncompliant_configuration(
    overrides: dict[str, object],
    message_part: str,
) -> None:
    repository = AsyncMock()
    repository.get_by_scope.return_value = None
    service = SourcesService(
        uow_factory=lambda: _StubUnitOfWork(repository)  # type: ignore[arg-type]
    )

    with pytest.raises(DomainError) as error:
        await service.register_source(
            _command(**overrides),
            _principal("knowledge:write"),
        )

    assert error.value.code == "VALIDATION_FAILED"
    assert message_part in error.value.message
    repository.create_source.assert_not_awaited()


async def test_register_source_rejects_duplicate_domain_in_same_region() -> None:
    repository = AsyncMock()
    repository.get_by_scope.return_value = object()
    service = SourcesService(
        uow_factory=lambda: _StubUnitOfWork(repository)  # type: ignore[arg-type]
    )

    with pytest.raises(DomainError) as error:
        await service.register_source(
            _command(),
            _principal("knowledge:write"),
        )

    assert error.value.code == "RESOURCE_CONFLICT"
    repository.create_source.assert_not_awaited()


async def test_list_sources_requires_read_permission() -> None:
    service = SourcesService(
        uow_factory=lambda: _StubUnitOfWork(AsyncMock())  # type: ignore[arg-type]
    )

    with pytest.raises(DomainError) as error:
        await service.list_sources(_principal("knowledge:write"))

    assert error.value.code == "AUTH_FORBIDDEN"


async def test_list_sources_returns_repository_records_for_reader() -> None:
    repository = AsyncMock()
    repository.list_sources.return_value = []
    service = SourcesService(
        uow_factory=lambda: _StubUnitOfWork(repository)  # type: ignore[arg-type]
    )

    sources = await service.list_sources(_principal("knowledge:read"))

    assert sources == []
    repository.list_sources.assert_awaited_once_with()
