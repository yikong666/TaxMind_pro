from __future__ import annotations

import os
from typing import cast
from uuid import uuid4

import pytest
from minio import Minio
from sqlalchemy.ext.asyncio import AsyncSession

from taxmind.bootstrap.settings import Settings
from taxmind.infrastructure.mysql.session import create_engine
from taxmind.infrastructure.object_storage.minio import MinioObjectStore
from taxmind.modules.documents.application.import_service import (
    ManualImportCommand,
    ManualImportService,
)
from taxmind.modules.documents.application.service import (
    DocumentMetadataInput,
    DocumentsService,
    DocumentsUnitOfWorkFactory,
)
from taxmind.modules.documents.infrastructure.repository import SqlAlchemyDocumentsRepository
from taxmind.modules.identity.infrastructure.models import OrganizationModel, UserModel
from taxmind.modules.sources.application.service import (
    RegisterSourceSiteCommand,
    SourcesService,
    SourcesUnitOfWorkFactory,
)
from taxmind.modules.sources.infrastructure.repository import SqlAlchemySourcesRepository
from taxmind.shared.domain.ids import new_id
from taxmind.shared.domain.principal import Principal


class _SharedSourcesUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.repository: SqlAlchemySourcesRepository | None = None

    async def __aenter__(self) -> _SharedSourcesUnitOfWork:
        self.repository = SqlAlchemySourcesRepository(self._session)
        return self

    async def commit(self) -> None:
        await self._session.flush()

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


class _SharedSourcesUnitOfWorkFactory:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def __call__(self) -> _SharedSourcesUnitOfWork:
        return _SharedSourcesUnitOfWork(self._session)


class _SharedDocumentsUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.repository: SqlAlchemyDocumentsRepository | None = None

    async def __aenter__(self) -> _SharedDocumentsUnitOfWork:
        self.repository = SqlAlchemyDocumentsRepository(self._session)
        return self

    async def commit(self) -> None:
        await self._session.flush()

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


class _SharedDocumentsUnitOfWorkFactory:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def __call__(self) -> _SharedDocumentsUnitOfWork:
        return _SharedDocumentsUnitOfWork(self._session)


@pytest.mark.skipif(
    os.getenv("TAXMIND_RUN_INTEGRATION") != "1",
    reason="requires the local MySQL and MinIO Compose services",
)
async def test_manual_import_writes_private_original_and_unpublished_draft() -> None:
    settings = Settings(app_env="test")
    engine = create_engine(settings)
    session = AsyncSession(engine, expire_on_commit=False)
    transaction = await session.begin()
    unique = uuid4().hex
    object_key: str | None = None
    minio_client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key.get_secret_value(),
        secret_key=settings.minio_secret_key.get_secret_value(),
        secure=settings.minio_secure,
    )
    try:
        org_id = new_id()
        user_id = new_id()
        session.add_all(
            [
                OrganizationModel(
                    id=org_id,
                    code=f"stage5-{unique}",
                    name="阶段五虚构验收机构",
                    status="active",
                    settings_json={},
                    version_no=1,
                ),
                UserModel(
                    id=user_id,
                    email=f"stage5-{unique}@example.invalid",
                    display_name="阶段五虚构知识管理员",
                    password_hash="not-used-in-integration-test",  # noqa: S106
                    status="active",
                    last_login_at=None,
                ),
            ]
        )
        await session.flush()
        principal = Principal(
            user_id=user_id,
            org_id=org_id,
            session_id=new_id(),
            roles=frozenset({"knowledge_admin"}),
            permissions=frozenset({"knowledge:read", "knowledge:write"}),
        )
        sources = SourcesService(
            uow_factory=cast(
                SourcesUnitOfWorkFactory,
                _SharedSourcesUnitOfWorkFactory(session),
            )
        )
        source = await sources.register_source(
            RegisterSourceSiteCommand(
                name="阶段五虚构官方来源",
                base_url="https://example.invalid",
                source_level="A",
                authority_name="阶段五虚构机关",
                region_code="000000",
                collection_method="file_import",
                whitelist_rules={},
                crawl_interval_minutes=None,
                request_id=new_id(),
            ),
            principal,
        )
        documents = DocumentsService(
            uow_factory=cast(
                DocumentsUnitOfWorkFactory,
                _SharedDocumentsUnitOfWorkFactory(session),
            )
        )
        importer = ManualImportService(
            sources=sources,
            documents=documents,
            object_store=MinioObjectStore(minio_client),
            raw_bucket=settings.minio_raw_bucket,
            max_bytes=settings.ingestion_max_bytes,
        )
        result = await importer.import_file(
            ManualImportCommand(
                source_site_id=source.id,
                filename="stage5-virtual-policy.txt",
                mime_type="text/plain",
                content=(
                    "关于阶段五虚构验收的公告\n\n"
                    "第一条 本资料仅用于自动化验收。\n"
                    "第二条 本资料不会自动发布。\n"
                ).encode(),
                metadata=DocumentMetadataInput(
                    title="阶段五虚构导入资料",
                    doc_no=f"STAGE5-{unique[:8]}",
                    doc_type="announcement",
                    source_level="A",
                    issuing_authority="阶段五虚构机关",
                    region_code="000000",
                    publish_date=None,
                    effective_start=None,
                    effective_end=None,
                    policy_status="active",
                    canonical_url=f"https://example.invalid/stage5/{unique}",
                ),
                request_id=new_id(),
            ),
            principal,
        )
        object_key = result.job.input_object_key

        assert result.job.status == "succeeded"
        assert result.idempotent is False
        assert result.chunk_count == 2
        assert result.document_id is not None
        assert result.document_version_id is not None
        assert object_key is not None
        stored = minio_client.stat_object(settings.minio_raw_bucket, object_key)
        assert isinstance(stored.size, int)
        assert stored.size > 0
        restored_job = await sources.get_job(result.job.id, principal)
        assert restored_job.status == "succeeded"
        assert restored_job.changed_count == 1
    finally:
        if object_key is not None:
            minio_client.remove_object(settings.minio_raw_bucket, object_key)
        if transaction.is_active:
            await transaction.rollback()
        await session.close()
        await engine.dispose()
