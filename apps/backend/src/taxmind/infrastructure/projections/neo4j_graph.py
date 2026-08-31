from __future__ import annotations

from typing import Any, Protocol

from taxmind.infrastructure.projections.contracts import (
    GraphRelationProjectionRecord,
    Neo4jGraphProjectionPort,
    ProjectionWriteResult,
)


class Neo4jSession(Protocol):
    def run(self, query: str, **parameters: object) -> Any: ...


class Neo4jDriver(Protocol):
    def session(self, **kwargs: object) -> Neo4jSession: ...


class Neo4jGraphProjectionAdapter(Neo4jGraphProjectionPort):
    def __init__(self, *, driver: Neo4jDriver, database: str) -> None:
        self._driver = driver
        self._database = database

    async def upsert_graph_snapshot(
        self, records: list[GraphRelationProjectionRecord], *, idempotency_key: str
    ) -> ProjectionWriteResult:
        if not idempotency_key.strip():
            raise ValueError("idempotency_key is required")
        if not records:
            return ProjectionWriteResult("neo4j_graph", "empty", 0, "succeeded")
        if len({record.snapshot_id for record in records}) != 1:
            raise ValueError("a graph projection batch must contain one snapshot")
        session = self._driver.session(database=self._database)
        try:
            for record in records:
                session.run(
                    "MERGE (source:KnowledgeNode {node_id: $from_node_id}) "
                    "MERGE (target:KnowledgeNode {node_id: $to_node_id}) "
                    "MERGE (source)-[rel:KNOWLEDGE_RELATION {relation_id: $relation_id}]->(target) "
                    "SET rel.relation_type=$relation_type, rel.snapshot_id=$snapshot_id, "
                    "rel.source_chunk_id=$source_chunk_id, rel.source_url=$source_url, "
                    "rel.content_hash=$content_hash",
                    relation_id=record.relation_id,
                    from_node_id=record.from_node_id,
                    to_node_id=record.to_node_id,
                    relation_type=record.relation_type,
                    snapshot_id=record.snapshot_id,
                    source_chunk_id=record.source_chunk_id,
                    source_url=record.source_url,
                    content_hash=record.content_hash,
                )
        finally:
            close = getattr(session, "close", None)
            if callable(close):
                close()
        return ProjectionWriteResult(
            "neo4j_graph", records[0].snapshot_id, len(records), "succeeded"
        )
