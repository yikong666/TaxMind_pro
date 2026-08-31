from __future__ import annotations

import pytest

from taxmind.modules.retrieval.infrastructure.neo4j_graph import (
    GraphAnchor,
    GraphExpansionRequest,
    Neo4jGraphExpansionAdapter,
)


class _Session:
    def __init__(self) -> None:
        self.query = ""
        self.parameters: dict[str, object] = {}

    def run(self, query: str, **parameters: object) -> list[dict[str, str]]:
        self.query, self.parameters = query, parameters
        return [
            {
                "chunk_id": "chunk-related-1",
                "document_version_id": "version-related-1",
                "source_url": "https://example.invalid/related",
                "source_chunk_id": "source-related-1",
            }
        ]


class _Driver:
    def __init__(self) -> None:
        self.session_instance = _Session()

    def session(self, **_: object) -> _Session:
        return self.session_instance


@pytest.mark.asyncio
async def test_graph_expansion_uses_whitelisted_template_and_traceable_paths() -> None:
    driver = _Driver()
    adapter = Neo4jGraphExpansionAdapter(driver=driver, database="neo4j")

    paths = await adapter.expand(
        GraphExpansionRequest(
            expansion_type="policy_lineage",
            anchors=[GraphAnchor(node_id="document-version-1")],
            max_depth=2,
            max_paths=4,
        )
    )

    assert paths[0].source_chunk_id == "source-related-1"
    assert "KNOWLEDGE_RELATION" in driver.session_instance.query
    assert driver.session_instance.parameters["max_depth"] == 2
    assert driver.session_instance.parameters["anchor_ids"] == ["document-version-1"]
