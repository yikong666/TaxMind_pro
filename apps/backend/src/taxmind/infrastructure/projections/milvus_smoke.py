from __future__ import annotations

from typing import Protocol

from taxmind.modules.knowledge.application.projection_payload_service import (
    SnapshotProjectionPayload,
)
from taxmind.modules.knowledge.domain import KnowledgeSnapshotRecord


class SnapshotPayloadLoader(Protocol):
    async def load(self, snapshot_id: str) -> SnapshotProjectionPayload: ...


class MilvusReadClient(Protocol):
    def get(self, collection_name: str, ids: list[str]) -> list[dict[str, object]]: ...


class MilvusSnapshotSmokeVerifier:
    def __init__(
        self, *, loader: SnapshotPayloadLoader, client: MilvusReadClient, collection_name: str
    ) -> None:
        self._loader = loader
        self._client = client
        self._collection_name = collection_name

    async def verify(self, snapshot: KnowledgeSnapshotRecord) -> bool:
        payload = await self._loader.load(snapshot.id)
        if not payload.policy_records:
            return False
        sample = payload.policy_records[0]
        records = self._client.get(self._collection_name, [sample.chunk_id])
        return any(
            item.get("chunk_id") == sample.chunk_id and item.get("snapshot_id") == snapshot.id
            for item in records
        )
