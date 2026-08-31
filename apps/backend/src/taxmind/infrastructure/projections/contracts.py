from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PolicyChunkProjectionRecord:
    snapshot_id: str
    snapshot_code: str
    chunk_id: str
    source_chunk_id: str
    document_id: str
    document_version_id: str
    source_url: str
    region_code: str
    effective_start: str | None
    effective_end: str | None
    policy_status: str
    review_status: str
    content_hash: str
    embedding_version: str
    dense_vector: tuple[float, ...]

    def __post_init__(self) -> None:
        _required("snapshot_id", self.snapshot_id)
        _required("source_chunk_id", self.source_chunk_id)
        _required("source_url", self.source_url)
        _sha256(self.content_hash)
        if self.review_status != "published":
            raise ValueError("policy projection requires published review_status")
        if not self.dense_vector:
            raise ValueError("dense_vector is required")


@dataclass(frozen=True, slots=True)
class GraphRelationProjectionRecord:
    snapshot_id: str
    relation_id: str
    from_node_id: str
    to_node_id: str
    relation_type: str
    source_chunk_id: str
    source_url: str
    content_hash: str

    def __post_init__(self) -> None:
        _required("snapshot_id", self.snapshot_id)
        _required("relation_id", self.relation_id)
        _required("from_node_id", self.from_node_id)
        _required("to_node_id", self.to_node_id)
        _required("relation_type", self.relation_type)
        _required("source_chunk_id", self.source_chunk_id)
        _required("source_url", self.source_url)
        _sha256(self.content_hash)


@dataclass(frozen=True, slots=True)
class ProjectionWriteResult:
    projection_type: str
    snapshot_id: str
    projected_count: int
    status: str

    def __post_init__(self) -> None:
        _required("projection_type", self.projection_type)
        _required("snapshot_id", self.snapshot_id)
        if self.projected_count < 0:
            raise ValueError("projected_count must not be negative")
        if self.status not in {"succeeded", "retryable", "dead"}:
            raise ValueError("projection status is invalid")


class MilvusPolicyProjectionPort(Protocol):
    async def upsert_policy_snapshot(
        self,
        records: list[PolicyChunkProjectionRecord],
        *,
        idempotency_key: str,
    ) -> ProjectionWriteResult: ...


class Neo4jGraphProjectionPort(Protocol):
    async def upsert_graph_snapshot(
        self,
        records: list[GraphRelationProjectionRecord],
        *,
        idempotency_key: str,
    ) -> ProjectionWriteResult: ...


def _required(name: str, value: str) -> None:
    if not value.strip():
        raise ValueError(f"{name} is required")


def _sha256(value: str) -> None:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
        raise ValueError("content_hash must be a SHA-256 hex digest")
