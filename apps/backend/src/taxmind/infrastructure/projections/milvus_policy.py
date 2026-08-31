from __future__ import annotations

from typing import Any, Protocol

from pymilvus import DataType, MilvusClient  # type: ignore[import-untyped]

from taxmind.bootstrap.settings import Settings
from taxmind.infrastructure.projections.contracts import (
    MilvusPolicyProjectionPort,
    PolicyChunkProjectionRecord,
    ProjectionWriteResult,
)


class MilvusUpsertClient(Protocol):
    def upsert(self, collection_name: str, data: list[dict[str, object]]) -> dict[str, int]: ...


class MilvusPolicyProjectionAdapter(MilvusPolicyProjectionPort):
    def __init__(self, *, client: MilvusUpsertClient, collection_name: str) -> None:
        if not collection_name.strip():
            raise ValueError("collection_name is required")
        self._client = client
        self._collection_name = collection_name

    async def upsert_policy_snapshot(
        self,
        records: list[PolicyChunkProjectionRecord],
        *,
        idempotency_key: str,
    ) -> ProjectionWriteResult:
        if not idempotency_key.strip():
            raise ValueError("idempotency_key is required")
        if not records:
            return ProjectionWriteResult(
                projection_type="milvus_policy",
                snapshot_id="empty",
                projected_count=0,
                status="succeeded",
            )
        snapshot_ids = {record.snapshot_id for record in records}
        if len(snapshot_ids) != 1:
            raise ValueError("a Milvus projection batch must contain one snapshot")
        self._client.upsert(
            self._collection_name,
            [
                {
                    "chunk_id": record.chunk_id,
                    "snapshot_id": record.snapshot_id,
                    "snapshot_code": record.snapshot_code,
                    "source_chunk_id": record.source_chunk_id,
                    "document_id": record.document_id,
                    "document_version_id": record.document_version_id,
                    "source_url": record.source_url,
                    "region_code": record.region_code,
                    "effective_start": record.effective_start,
                    "effective_end": record.effective_end,
                    "policy_status": record.policy_status,
                    "review_status": record.review_status,
                    "content_hash": record.content_hash,
                    "embedding_version": record.embedding_version,
                    "dense_vector": list(record.dense_vector),
                }
                for record in records
            ],
        )
        return ProjectionWriteResult(
            projection_type="milvus_policy",
            snapshot_id=records[0].snapshot_id,
            projected_count=len(records),
            status="succeeded",
        )


def create_milvus_client(settings: Settings) -> Any:
    token = settings.milvus_token.get_secret_value() or None
    return MilvusClient(
        uri=settings.milvus_uri,
        token=token,
        db_name=settings.milvus_database,
    )


def ensure_policy_collection(client: Any, *, collection_name: str, dimension: int) -> None:
    """Create a versioned, non-aliased policy collection only during worker bootstrap."""
    if dimension < 1:
        raise ValueError("dimension must be positive")
    if client.has_collection(collection_name):
        return
    schema = client.create_schema(auto_id=False, enable_dynamic_field=True)
    schema.add_field("chunk_id", DataType.VARCHAR, is_primary=True, max_length=64)
    schema.add_field("dense_vector", DataType.FLOAT_VECTOR, dim=dimension)
    index_params = client.prepare_index_params()
    index_params.add_index(field_name="dense_vector", index_type="AUTOINDEX", metric_type="COSINE")
    client.create_collection(
        collection_name=collection_name,
        schema=schema,
        index_params=index_params,
    )
