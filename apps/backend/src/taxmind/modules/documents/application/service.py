from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from typing import Protocol
from urllib.parse import urlparse

from taxmind.modules.documents.domain import (
    DocumentChunkRecord,
    DocumentDetail,
    DocumentVersionRecord,
    PolicyEvidence,
    SourceDocumentRecord,
)
from taxmind.modules.documents.infrastructure.repository import SqlAlchemyDocumentsRepository
from taxmind.modules.documents.infrastructure.uow import SqlAlchemyDocumentsUnitOfWork
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.ids import new_id
from taxmind.shared.domain.principal import Principal

_DOCUMENT_TYPES = frozenset({"law", "regulation", "announcement", "interpretation", "guide", "faq"})
_SOURCE_LEVELS = frozenset({"A", "B", "C", "D"})
_CHUNK_TYPES = frozenset({"title", "chapter", "article", "paragraph", "table", "attachment"})


class DocumentsUnitOfWorkFactory(Protocol):
    def __call__(self) -> SqlAlchemyDocumentsUnitOfWork: ...


@dataclass(frozen=True, slots=True)
class DocumentMetadataInput:
    title: str
    doc_no: str | None
    doc_type: str
    source_level: str
    issuing_authority: str
    region_code: str
    publish_date: date | None
    effective_start: date | None
    effective_end: date | None
    policy_status: str
    canonical_url: str


@dataclass(frozen=True, slots=True)
class VersionInput:
    source_url: str
    mime_type: str
    content_hash_sha256: str
    raw_object_key: str | None
    parsed_object_key: str | None


@dataclass(frozen=True, slots=True)
class ChunkInput:
    source_chunk_id: str
    chunk_order: int
    chunk_type: str
    heading_path: str
    clause_label: str | None
    content_text: str
    content_hash_sha256: str
    token_count: int
    effective_start: date | None
    effective_end: date | None


class DocumentsService:
    def __init__(self, *, uow_factory: DocumentsUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def create_document(
        self,
        metadata: DocumentMetadataInput,
        version_input: VersionInput,
        *,
        request_id: str,
        principal: Principal,
    ) -> DocumentDetail:
        _require_knowledge_write(principal)
        _validate_metadata(metadata)
        _validate_version_input(version_input)
        now = datetime.now(UTC)
        document = SourceDocumentRecord(
            id=new_id(),
            canonical_key=_canonical_key(metadata),
            title=_normalized_text(metadata.title, "资料标题"),
            doc_no=_optional_text(metadata.doc_no),
            doc_type=metadata.doc_type,
            source_level=metadata.source_level,
            issuing_authority=_normalized_text(metadata.issuing_authority, "发文机关"),
            region_code=metadata.region_code,
            publish_date=metadata.publish_date,
            effective_start=metadata.effective_start,
            effective_end=metadata.effective_end,
            policy_status=metadata.policy_status,
            canonical_url=metadata.canonical_url,
            current_version_id=None,
            review_status="draft",
            created_by=principal.user_id,
            created_at=now,
            updated_at=now,
        )
        version = _version_record(
            version_input,
            document_id=document.id,
            version_no=1,
            supersedes_version_id=None,
            actor_id=principal.user_id,
            now=now,
        )
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            await repository.create_document(document, actor_id=principal.user_id)
            await repository.flush()
            await repository.create_version(version)
            await repository.create_audit_log(
                org_id=principal.org_id,
                actor_user_id=principal.user_id,
                action_code="knowledge.document.created_draft",
                resource_id=document.id,
                request_id=request_id,
                occurred_at=now,
            )
            await uow.commit()
        return DocumentDetail(document=document, version=version, chunks=[])

    async def create_version(
        self,
        document_id: str,
        version_input: VersionInput,
        *,
        request_id: str,
        principal: Principal,
    ) -> DocumentDetail:
        _require_knowledge_write(principal)
        _validate_version_input(version_input)
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            document = await repository.get_document(document_id)
            if document is None:
                raise DomainError(code="RESOURCE_NOT_FOUND", message="资料不存在")
            latest = await repository.latest_version(document.id)
            if latest is None:
                raise DomainError(code="RESOURCE_CONFLICT", message="资料版本状态不完整")
            if latest.review_status in {"draft", "pending_review"}:
                raise DomainError(
                    code="POLICY_STATUS_CONFLICT", message="现有草稿或待审核版本尚未处理"
                )
            version = _version_record(
                version_input,
                document_id=document.id,
                version_no=latest.version_no + 1,
                supersedes_version_id=latest.id,
                actor_id=principal.user_id,
                now=now,
            )
            await repository.create_version(version)
            await repository.create_audit_log(
                org_id=principal.org_id,
                actor_user_id=principal.user_id,
                action_code="knowledge.document_version.created_draft",
                resource_id=document.id,
                request_id=request_id,
                occurred_at=now,
            )
            await uow.commit()
            return DocumentDetail(document=document, version=version, chunks=[])

    async def create_chunks(
        self,
        version_id: str,
        inputs: list[ChunkInput],
        *,
        request_id: str,
        principal: Principal,
    ) -> DocumentDetail:
        _require_knowledge_write(principal)
        _validate_chunk_inputs(inputs)
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            version = await repository.get_version(version_id, lock=True)
            if version is None:
                raise DomainError(code="RESOURCE_NOT_FOUND", message="资料版本不存在")
            if version.review_status != "draft":
                raise DomainError(code="POLICY_STATUS_CONFLICT", message="仅草稿版本可补充条款")
            document = await repository.get_document(version.document_id)
            if document is None:
                raise DomainError(code="RESOURCE_CONFLICT", message="资料主记录不存在")
            chunks = [_chunk_record(item, document=document, version=version) for item in inputs]
            await repository.create_chunks(chunks, created_at=now)
            await repository.create_audit_log(
                org_id=principal.org_id,
                actor_user_id=principal.user_id,
                action_code="knowledge.document_chunks.created_draft",
                resource_id=document.id,
                request_id=request_id,
                occurred_at=now,
            )
            await uow.commit()
            return DocumentDetail(document=document, version=version, chunks=chunks)

    async def submit_review(
        self, version_id: str, *, request_id: str, principal: Principal
    ) -> DocumentDetail:
        _require_knowledge_write(principal)
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            version = await repository.get_version(version_id, lock=True)
            if version is None:
                raise DomainError(code="RESOURCE_NOT_FOUND", message="资料版本不存在")
            if version.review_status != "draft":
                raise DomainError(code="POLICY_STATUS_CONFLICT", message="当前版本不能提交审核")
            document = await repository.get_document(version.document_id)
            chunks = await repository.list_chunks(version.id)
            if document is None or not chunks:
                raise DomainError(
                    code="POLICY_STATUS_CONFLICT", message="资料版本至少需要一条可引用条款"
                )
            await repository.set_pending_review(
                version.id, actor_id=principal.user_id, updated_at=now
            )
            await repository.create_audit_log(
                org_id=principal.org_id,
                actor_user_id=principal.user_id,
                action_code="knowledge.document_version.submitted_review",
                resource_id=document.id,
                request_id=request_id,
                occurred_at=now,
            )
            await uow.commit()
            pending_version = replace(version, review_status="pending_review")
            pending_chunks = [replace(chunk, review_status="pending_review") for chunk in chunks]
            return DocumentDetail(
                document=replace(document, review_status="pending_review", updated_at=now),
                version=pending_version,
                chunks=pending_chunks,
            )

    async def publish(
        self, version_id: str, *, request_id: str, principal: Principal
    ) -> DocumentDetail:
        _require_knowledge_review(principal)
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            version = await repository.get_version(version_id, lock=True)
            if version is None:
                raise DomainError(code="RESOURCE_NOT_FOUND", message="资料版本不存在")
            if version.review_status != "pending_review":
                raise DomainError(code="POLICY_STATUS_CONFLICT", message="仅待审核版本可发布")
            if version.created_by == principal.user_id:
                raise DomainError(code="AUTH_FORBIDDEN", message="资料创建者不得自行发布")
            document = await repository.get_document(version.document_id)
            chunks = await repository.list_chunks(version.id)
            if document is None or not chunks:
                raise DomainError(code="POLICY_STATUS_CONFLICT", message="资料版本缺少可引用条款")
            await repository.publish(version, actor_id=principal.user_id, published_at=now)
            await repository.create_audit_log(
                org_id=principal.org_id,
                actor_user_id=principal.user_id,
                action_code="knowledge.document_version.published",
                resource_id=document.id,
                request_id=request_id,
                occurred_at=now,
            )
            await uow.commit()
            return DocumentDetail(
                document=replace(
                    document,
                    current_version_id=version.id,
                    review_status="published",
                    updated_at=now,
                ),
                version=replace(version, review_status="published", published_at=now),
                chunks=[
                    replace(chunk, review_status="published", index_status="pending")
                    for chunk in chunks
                ],
            )

    async def search_published(
        self,
        *,
        query: str,
        region_code: str,
        business_date: date,
        limit: int,
        principal: Principal,
    ) -> list[PolicyEvidence]:
        _require_knowledge_read(principal)
        normalized_query = _normalized_text(query, "检索词")
        _validate_region_code(region_code)
        async with self._uow_factory() as uow:
            return await _repository(uow).search_published(
                query=normalized_query,
                region_code=region_code,
                business_date=business_date,
                limit=limit,
            )


def _repository(uow: SqlAlchemyDocumentsUnitOfWork) -> SqlAlchemyDocumentsRepository:
    if uow.repository is None:
        raise RuntimeError("unit of work repository is unavailable")
    return uow.repository


def _require_knowledge_read(principal: Principal) -> None:
    if not principal.has_permission("knowledge:read"):
        raise DomainError(code="AUTH_FORBIDDEN", message="当前角色无知识检索权限")


def _require_knowledge_write(principal: Principal) -> None:
    if not principal.has_permission("knowledge:write"):
        raise DomainError(code="AUTH_FORBIDDEN", message="当前角色无知识维护权限")


def _require_knowledge_review(principal: Principal) -> None:
    if not principal.has_permission("knowledge:review"):
        raise DomainError(code="AUTH_FORBIDDEN", message="当前角色无知识发布权限")


def _normalized_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise DomainError(code="VALIDATION_FAILED", message=f"{field_name}不能为空")
    return normalized


def _optional_text(value: str | None) -> str | None:
    return value.strip() or None if value is not None else None


def _validate_region_code(value: str) -> None:
    if len(value) != 6 or not value.isdigit():
        raise DomainError(code="VALIDATION_FAILED", message="地区必须使用六位 GB/T 2260 代码")


def _validate_metadata(metadata: DocumentMetadataInput) -> None:
    _normalized_text(metadata.title, "资料标题")
    _normalized_text(metadata.issuing_authority, "发文机关")
    _validate_region_code(metadata.region_code)
    if metadata.doc_type not in _DOCUMENT_TYPES:
        raise DomainError(code="VALIDATION_FAILED", message="资料类型无效")
    if metadata.source_level not in _SOURCE_LEVELS:
        raise DomainError(code="VALIDATION_FAILED", message="资料来源等级无效")
    if metadata.policy_status != "active":
        raise DomainError(code="VALIDATION_FAILED", message="当前阶段仅可录入有效的官方资料草稿")
    if (
        metadata.effective_end
        and metadata.effective_start
        and metadata.effective_end < metadata.effective_start
    ):
        raise DomainError(code="VALIDATION_FAILED", message="有效期结束日不能早于开始日")
    parsed = urlparse(metadata.canonical_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise DomainError(code="VALIDATION_FAILED", message="资料来源必须为 HTTPS 官方公开地址")


def _validate_version_input(value: VersionInput) -> None:
    parsed = urlparse(value.source_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise DomainError(code="VALIDATION_FAILED", message="版本来源必须为 HTTPS 官方公开地址")
    if not value.mime_type.strip():
        raise DomainError(code="VALIDATION_FAILED", message="资料 MIME 类型不能为空")
    _validate_hash(value.content_hash_sha256, "资料内容哈希")


def _validate_chunk_inputs(inputs: list[ChunkInput]) -> None:
    if not inputs:
        raise DomainError(code="VALIDATION_FAILED", message="至少需要一条条款")
    seen_source_ids: set[str] = set()
    seen_orders: set[int] = set()
    for item in inputs:
        if item.source_chunk_id in seen_source_ids or item.chunk_order in seen_orders:
            raise DomainError(code="VALIDATION_FAILED", message="条款标识和顺序不得重复")
        seen_source_ids.add(item.source_chunk_id)
        seen_orders.add(item.chunk_order)
        if item.chunk_type not in _CHUNK_TYPES:
            raise DomainError(code="VALIDATION_FAILED", message="条款类型无效")
        if item.chunk_order < 0 or item.token_count < 0:
            raise DomainError(code="VALIDATION_FAILED", message="条款顺序和 token 数不能为负数")
        _normalized_text(item.source_chunk_id, "条款来源标识")
        _normalized_text(item.heading_path, "条款标题路径")
        _normalized_text(item.content_text, "条款正文")
        _validate_hash(item.content_hash_sha256, "条款内容哈希")
        if (
            item.effective_end
            and item.effective_start
            and item.effective_end < item.effective_start
        ):
            raise DomainError(code="VALIDATION_FAILED", message="条款有效期结束日不能早于开始日")


def _validate_hash(value: str, field_name: str) -> None:
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
        raise DomainError(
            code="VALIDATION_FAILED", message=f"{field_name}必须是 SHA-256 十六进制摘要"
        )


def _canonical_key(metadata: DocumentMetadataInput) -> str:
    if metadata.doc_no and metadata.doc_no.strip():
        return f"{metadata.issuing_authority.strip()}::{metadata.doc_no.strip()}"
    digest = hashlib.sha256(metadata.canonical_url.strip().encode("utf-8")).hexdigest()
    return f"url::{digest}"


def _version_record(
    value: VersionInput,
    *,
    document_id: str,
    version_no: int,
    supersedes_version_id: str | None,
    actor_id: str,
    now: datetime,
) -> DocumentVersionRecord:
    return DocumentVersionRecord(
        id=new_id(),
        document_id=document_id,
        version_no=version_no,
        captured_at=now,
        source_url=value.source_url.strip(),
        raw_object_key=_optional_text(value.raw_object_key),
        parsed_object_key=_optional_text(value.parsed_object_key),
        mime_type=value.mime_type.strip(),
        content_hash_sha256=value.content_hash_sha256.strip().lower(),
        parse_status="parsed",
        ocr_status="not_required",
        review_status="draft",
        published_at=None,
        supersedes_version_id=supersedes_version_id,
        created_by=actor_id,
    )


def _chunk_record(
    value: ChunkInput,
    *,
    document: SourceDocumentRecord,
    version: DocumentVersionRecord,
) -> DocumentChunkRecord:
    return DocumentChunkRecord(
        id=new_id(),
        document_id=document.id,
        document_version_id=version.id,
        source_chunk_id=value.source_chunk_id.strip(),
        chunk_order=value.chunk_order,
        chunk_type=value.chunk_type,
        heading_path=value.heading_path.strip(),
        clause_label=_optional_text(value.clause_label),
        content_text=value.content_text.strip(),
        content_hash_sha256=value.content_hash_sha256.strip().lower(),
        token_count=value.token_count,
        effective_start=value.effective_start or document.effective_start,
        effective_end=value.effective_end or document.effective_end,
        region_code=document.region_code,
        policy_status=document.policy_status,
        review_status="draft",
        index_status="pending",
    )
