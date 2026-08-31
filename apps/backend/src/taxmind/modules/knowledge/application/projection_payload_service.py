from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol

from taxmind.infrastructure.projections.contracts import (
    GraphRelationProjectionRecord,
    PolicyChunkProjectionRecord,
)
from taxmind.modules.knowledge.domain import (
    KnowledgeSnapshotRecord,
    SnapshotProjectionCandidateRecord,
)
from taxmind.modules.knowledge.infrastructure.uow import SqlAlchemyKnowledgeUnitOfWork


class EmbeddingPort(Protocol):
    async def embed(self, text: str) -> tuple[float, ...]: ...


class ProjectionPayloadUowFactory(Protocol):
    def __call__(self) -> SqlAlchemyKnowledgeUnitOfWork: ...


@dataclass(frozen=True, slots=True)
class SnapshotProjectionPayload:
    policy_records: list[PolicyChunkProjectionRecord]
    graph_records: list[GraphRelationProjectionRecord]


class SnapshotProjectionPayloadService:
    def __init__(self, *, embedding: EmbeddingPort) -> None:
        self._embedding = embedding

    async def build(
        self, snapshot: KnowledgeSnapshotRecord, candidates: list[SnapshotProjectionCandidateRecord]
    ) -> SnapshotProjectionPayload:
        policy_records: list[PolicyChunkProjectionRecord] = []
        graph_records: list[GraphRelationProjectionRecord] = []
        for source in candidates:
            candidate = source.candidate
            if candidate.candidate_type != "policy_clause" or candidate.review_status != "approved":
                raise ValueError("snapshot contains a non-approved policy clause candidate")
            payload = candidate.payload
            source_url = _text(payload, "source_url")
            excerpt = _text(payload, "text_excerpt")
            vector = await self._embedding.embed(excerpt)
            policy_records.append(
                PolicyChunkProjectionRecord(
                    snapshot_id=snapshot.id,
                    snapshot_code=snapshot.snapshot_code,
                    chunk_id=candidate.id,
                    source_chunk_id=candidate.source_chunk_id,
                    document_id=candidate.source_document_id,
                    document_version_id=source.document_version_id,
                    source_url=source_url,
                    region_code=_text(payload, "region_code"),
                    effective_start=_optional_text(payload, "effective_start"),
                    effective_end=_optional_text(payload, "effective_end"),
                    policy_status=_text(payload, "policy_status"),
                    review_status="published",
                    content_hash=candidate.content_hash,
                    embedding_version="worker-configured",
                    dense_vector=vector,
                )
            )
            graph_records.append(
                GraphRelationProjectionRecord(
                    snapshot_id=snapshot.id,
                    relation_id=_relation_id(snapshot.id, candidate.id),
                    from_node_id=candidate.source_document_id,
                    to_node_id=candidate.source_chunk_id,
                    relation_type="DOCUMENT_CONTAINS_CLAUSE",
                    source_chunk_id=candidate.source_chunk_id,
                    source_url=source_url,
                    content_hash=candidate.content_hash,
                )
            )
        return SnapshotProjectionPayload(policy_records=policy_records, graph_records=graph_records)


class SnapshotProjectionPayloadLoader:
    def __init__(
        self,
        *,
        uow_factory: ProjectionPayloadUowFactory,
        payload_service: SnapshotProjectionPayloadService,
    ) -> None:
        self._uow_factory = uow_factory
        self._payload_service = payload_service

    async def load(self, snapshot_id: str) -> SnapshotProjectionPayload:
        async with self._uow_factory() as uow:
            repository = uow.repository
            if repository is None:
                raise RuntimeError("unit of work repository is unavailable")
            snapshot = await repository.get_snapshot(snapshot_id)
            if snapshot is None:
                raise ValueError("snapshot does not exist")
            if snapshot.status not in {"pending_activation", "active"}:
                raise ValueError("snapshot is not available for projection")
            candidates = await repository.list_snapshot_projection_candidates(snapshot.id)
        return await self._payload_service.build(snapshot, candidates)


def _text(payload: dict[str, object], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"projection payload {name} is required")
    return value


def _optional_text(payload: dict[str, object], name: str) -> str | None:
    value = payload.get(name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"projection payload {name} must be text or null")
    return value


def _relation_id(snapshot_id: str, candidate_id: str) -> str:
    return sha256(f"{snapshot_id}:{candidate_id}:document_contains_clause".encode()).hexdigest()
