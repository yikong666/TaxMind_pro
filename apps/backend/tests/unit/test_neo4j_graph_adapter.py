from __future__ import annotations

from taxmind.infrastructure.projections.contracts import GraphRelationProjectionRecord
from taxmind.infrastructure.projections.neo4j_graph import Neo4jGraphProjectionAdapter


class _Session:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def run(self, query: str, **parameters: object) -> None:
        self.calls.append((query, parameters))


class _Driver:
    def __init__(self) -> None:
        self.session_instance = _Session()

    def session(self, **kwargs: object) -> _Session:
        return self.session_instance


async def test_neo4j_adapter_merges_traceable_relation_idempotently() -> None:
    driver = _Driver()
    adapter = Neo4jGraphProjectionAdapter(driver=driver, database="neo4j")
    record = GraphRelationProjectionRecord(
        snapshot_id="snapshot-1",
        relation_id="relation-1",
        from_node_id="document-1",
        to_node_id="clause-1",
        relation_type="CONTAINS",
        source_chunk_id="doc-1:1",
        source_url="https://example.invalid/policy/1",
        content_hash="b" * 64,
    )

    result = await adapter.upsert_graph_snapshot([record], idempotency_key="snapshot-1:b")

    assert result.status == "succeeded"
    assert result.projected_count == 1
    assert "MERGE" in driver.session_instance.calls[0][0]
    assert driver.session_instance.calls[0][1]["relation_id"] == "relation-1"
