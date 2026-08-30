from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from taxmind.modules.audit.infrastructure.models import AuditLogModel
from taxmind.modules.documents.domain import (
    DocumentChunkRecord,
    DocumentDetail,
    DocumentVersionRecord,
    PolicyEvidence,
    SourceDocumentRecord,
)
from taxmind.modules.documents.infrastructure.models import (
    DocumentChunkModel,
    DocumentVersionModel,
    SourceDocumentModel,
)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _document_record(model: SourceDocumentModel) -> SourceDocumentRecord:
    return SourceDocumentRecord(
        id=model.id,
        canonical_key=model.canonical_key,
        title=model.title,
        doc_no=model.doc_no,
        doc_type=model.doc_type,
        source_level=model.source_level,
        issuing_authority=model.issuing_authority,
        region_code=model.region_code,
        publish_date=model.publish_date,
        effective_start=model.effective_start,
        effective_end=model.effective_end,
        policy_status=model.policy_status,
        canonical_url=model.canonical_url,
        current_version_id=model.current_version_id,
        review_status=model.review_status,
        created_by=model.created_by,
        created_at=_as_utc(model.created_at),
        updated_at=_as_utc(model.updated_at),
    )


def _version_record(model: DocumentVersionModel) -> DocumentVersionRecord:
    return DocumentVersionRecord(
        id=model.id,
        document_id=model.document_id,
        version_no=model.version_no,
        captured_at=_as_utc(model.captured_at),
        source_url=model.source_url,
        raw_object_key=model.raw_object_key,
        parsed_object_key=model.parsed_object_key,
        mime_type=model.mime_type,
        content_hash_sha256=model.content_hash_sha256,
        parse_status=model.parse_status,
        ocr_status=model.ocr_status,
        review_status=model.review_status,
        published_at=_as_utc(model.published_at) if model.published_at else None,
        supersedes_version_id=model.supersedes_version_id,
        created_by=model.created_by,
    )


def _chunk_record(model: DocumentChunkModel) -> DocumentChunkRecord:
    return DocumentChunkRecord(
        id=model.id,
        document_id=model.document_id,
        document_version_id=model.document_version_id,
        source_chunk_id=model.source_chunk_id,
        chunk_order=model.chunk_order,
        chunk_type=model.chunk_type,
        heading_path=model.heading_path,
        clause_label=model.clause_label,
        content_text=model.content_text,
        content_hash_sha256=model.content_hash_sha256,
        token_count=model.token_count,
        effective_start=model.effective_start,
        effective_end=model.effective_end,
        region_code=model.region_code,
        policy_status=model.policy_status,
        review_status=model.review_status,
        index_status=model.index_status,
    )


class SqlAlchemyDocumentsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def flush(self) -> None:
        await self._session.flush()

    async def create_document(self, record: SourceDocumentRecord, *, actor_id: str) -> None:
        self._session.add(
            SourceDocumentModel(
                id=record.id,
                canonical_key=record.canonical_key,
                title=record.title,
                doc_no=record.doc_no,
                doc_type=record.doc_type,
                source_level=record.source_level,
                issuing_authority=record.issuing_authority,
                region_code=record.region_code,
                publish_date=record.publish_date,
                effective_start=record.effective_start,
                effective_end=record.effective_end,
                policy_status=record.policy_status,
                canonical_url=record.canonical_url,
                current_version_id=None,
                review_status=record.review_status,
                created_at=record.created_at,
                updated_at=record.updated_at,
                created_by=actor_id,
                updated_by=actor_id,
            )
        )

    async def create_version(self, record: DocumentVersionRecord) -> None:
        self._session.add(
            DocumentVersionModel(
                id=record.id,
                document_id=record.document_id,
                version_no=record.version_no,
                captured_at=record.captured_at,
                source_url=record.source_url,
                raw_object_key=record.raw_object_key,
                parsed_object_key=record.parsed_object_key,
                mime_type=record.mime_type,
                content_hash_sha256=record.content_hash_sha256,
                parse_status=record.parse_status,
                ocr_status=record.ocr_status,
                review_status=record.review_status,
                published_at=record.published_at,
                supersedes_version_id=record.supersedes_version_id,
                created_at=record.captured_at,
                created_by=record.created_by,
            )
        )

    async def create_chunks(
        self, records: list[DocumentChunkRecord], *, created_at: datetime
    ) -> None:
        self._session.add_all(
            [
                DocumentChunkModel(
                    id=record.id,
                    document_id=record.document_id,
                    document_version_id=record.document_version_id,
                    source_chunk_id=record.source_chunk_id,
                    chunk_order=record.chunk_order,
                    chunk_type=record.chunk_type,
                    heading_path=record.heading_path,
                    clause_label=record.clause_label,
                    content_text=record.content_text,
                    content_hash_sha256=record.content_hash_sha256,
                    token_count=record.token_count,
                    effective_start=record.effective_start,
                    effective_end=record.effective_end,
                    region_code=record.region_code,
                    policy_status=record.policy_status,
                    review_status=record.review_status,
                    index_status=record.index_status,
                    created_at=created_at,
                )
                for record in records
            ]
        )

    async def get_document(self, document_id: str) -> SourceDocumentRecord | None:
        model = await self._session.get(SourceDocumentModel, document_id)
        return _document_record(model) if model else None

    async def get_version(
        self, version_id: str, *, lock: bool = False
    ) -> DocumentVersionRecord | None:
        statement = select(DocumentVersionModel).where(DocumentVersionModel.id == version_id)
        if lock:
            statement = statement.with_for_update()
        model = await self._session.scalar(statement)
        return _version_record(model) if model else None

    async def latest_version(self, document_id: str) -> DocumentVersionRecord | None:
        model = await self._session.scalar(
            select(DocumentVersionModel)
            .where(DocumentVersionModel.document_id == document_id)
            .order_by(DocumentVersionModel.version_no.desc())
            .limit(1)
        )
        return _version_record(model) if model else None

    async def list_chunks(self, version_id: str) -> list[DocumentChunkRecord]:
        models = await self._session.scalars(
            select(DocumentChunkModel)
            .where(DocumentChunkModel.document_version_id == version_id)
            .order_by(DocumentChunkModel.chunk_order, DocumentChunkModel.id)
        )
        return [_chunk_record(model) for model in models]

    async def detail(self, document_id: str, version_id: str) -> DocumentDetail | None:
        document = await self.get_document(document_id)
        version = await self.get_version(version_id)
        if document is None or version is None or version.document_id != document.id:
            return None
        return DocumentDetail(
            document=document, version=version, chunks=await self.list_chunks(version.id)
        )

    async def set_pending_review(
        self, version_id: str, *, actor_id: str, updated_at: datetime
    ) -> None:
        await self._session.execute(
            update(DocumentVersionModel)
            .where(DocumentVersionModel.id == version_id)
            .values(review_status="pending_review")
        )
        await self._session.execute(
            update(DocumentChunkModel)
            .where(DocumentChunkModel.document_version_id == version_id)
            .values(review_status="pending_review")
        )
        await self._session.execute(
            update(SourceDocumentModel)
            .where(
                SourceDocumentModel.id
                == select(DocumentVersionModel.document_id)
                .where(DocumentVersionModel.id == version_id)
                .scalar_subquery()
            )
            .values(review_status="pending_review", updated_at=updated_at, updated_by=actor_id)
        )

    async def publish(
        self, version: DocumentVersionRecord, *, actor_id: str, published_at: datetime
    ) -> None:
        await self._session.execute(
            update(DocumentVersionModel)
            .where(DocumentVersionModel.id == version.id)
            .values(review_status="published", published_at=published_at)
        )
        await self._session.execute(
            update(DocumentChunkModel)
            .where(DocumentChunkModel.document_version_id == version.id)
            .values(review_status="published", index_status="pending")
        )
        await self._session.execute(
            update(SourceDocumentModel)
            .where(SourceDocumentModel.id == version.document_id)
            .values(
                current_version_id=version.id,
                review_status="published",
                updated_at=published_at,
                updated_by=actor_id,
            )
        )

    async def search_published(
        self, *, query: str, region_code: str, business_date: date, limit: int
    ) -> list[PolicyEvidence]:
        pattern = f"%{query.casefold()}%"
        statement = (
            select(SourceDocumentModel, DocumentVersionModel, DocumentChunkModel)
            .join(
                DocumentVersionModel,
                SourceDocumentModel.current_version_id == DocumentVersionModel.id,
            )
            .join(
                DocumentChunkModel,
                DocumentChunkModel.document_version_id == DocumentVersionModel.id,
            )
            .where(
                SourceDocumentModel.review_status == "published",
                SourceDocumentModel.policy_status == "active",
                DocumentVersionModel.review_status == "published",
                DocumentChunkModel.review_status == "published",
                DocumentChunkModel.policy_status == "active",
                DocumentChunkModel.region_code.in_([region_code, "000000"]),
                or_(
                    DocumentChunkModel.effective_start.is_(None),
                    DocumentChunkModel.effective_start <= business_date,
                ),
                or_(
                    DocumentChunkModel.effective_end.is_(None),
                    DocumentChunkModel.effective_end >= business_date,
                ),
                or_(
                    SourceDocumentModel.doc_no.ilike(pattern),
                    SourceDocumentModel.title.ilike(pattern),
                    DocumentChunkModel.heading_path.ilike(pattern),
                    DocumentChunkModel.content_text.ilike(pattern),
                ),
            )
            .order_by(
                DocumentChunkModel.region_code.desc(),
                DocumentChunkModel.chunk_order,
                DocumentChunkModel.id,
            )
            .limit(limit)
        )
        rows = (await self._session.execute(statement)).all()
        return [
            PolicyEvidence(
                document=_document_record(document),
                version=_version_record(version),
                chunk=_chunk_record(chunk),
                region_match="local" if chunk.region_code == region_code else "national_only",
            )
            for document, version, chunk in rows
        ]

    async def create_audit_log(
        self,
        *,
        org_id: str,
        actor_user_id: str,
        action_code: str,
        resource_id: str,
        request_id: str,
        occurred_at: datetime,
    ) -> None:
        self._session.add(
            AuditLogModel(
                org_id=org_id,
                actor_user_id=actor_user_id,
                action_code=action_code,
                resource_type="source_document",
                resource_id=resource_id,
                request_id=request_id,
                result="success",
                occurred_at=occurred_at,
            )
        )
