from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from taxmind.modules.retrieval.application.service import RetrievalUnavailable

GraphExpansionType = Literal["policy_lineage", "policy_conditions", "policy_obligations"]


@dataclass(frozen=True, slots=True)
class GraphAnchor:
    node_id: str

    def __post_init__(self) -> None:
        if not self.node_id.strip():
            raise ValueError("node_id is required")


@dataclass(frozen=True, slots=True)
class GraphExpansionRequest:
    expansion_type: GraphExpansionType
    anchors: list[GraphAnchor]
    max_depth: int
    max_paths: int

    def __post_init__(self) -> None:
        if not self.anchors:
            raise ValueError("at least one graph anchor is required")
        if not 1 <= self.max_depth <= 2:
            raise ValueError("max_depth must be between 1 and 2")
        if self.max_paths < 1:
            raise ValueError("max_paths must be positive")


@dataclass(frozen=True, slots=True)
class GraphEvidencePath:
    chunk_id: str
    document_version_id: str
    source_url: str
    source_chunk_id: str


class Neo4jSession(Protocol):
    def run(self, query: str, **parameters: object) -> list[dict[str, str]]: ...


class Neo4jDriver(Protocol):
    def session(self, **kwargs: object) -> Neo4jSession: ...


class Neo4jGraphExpansionAdapter:
    def __init__(self, *, driver: Neo4jDriver, database: str) -> None:
        self._driver, self._database = driver, database

    async def expand(self, request: GraphExpansionRequest) -> list[GraphEvidencePath]:
        session = self._driver.session(database=self._database)
        try:
            rows = session.run(
                _template(request.expansion_type),
                anchor_ids=[anchor.node_id for anchor in request.anchors],
                max_depth=request.max_depth,
                max_paths=request.max_paths,
            )
        except Exception as exc:
            raise RetrievalUnavailable("Neo4j graph expansion is unavailable") from exc
        return [
            GraphEvidencePath(
                chunk_id=row["chunk_id"],
                document_version_id=row["document_version_id"],
                source_url=row["source_url"],
                source_chunk_id=row["source_chunk_id"],
            )
            for row in rows
            if all(row.get(field, "").strip() for field in _TRACE_FIELDS)
        ]


_TRACE_FIELDS = ("chunk_id", "document_version_id", "source_url", "source_chunk_id")


def _template(expansion_type: GraphExpansionType) -> str:
    relation_types = {
        "policy_lineage": "REPLACES|REPEALS|AMENDS",
        "policy_conditions": "HAS_CONDITION|EXCLUDES",
        "policy_obligations": "IMPOSES_OBLIGATION|HAS_PROCEDURE",
    }
    try:
        types = relation_types[expansion_type]
    except KeyError as exc:
        raise ValueError("unsupported graph expansion type") from exc
    return (
        "MATCH (anchor:KnowledgeNode) WHERE anchor.node_id IN $anchor_ids "
        f"MATCH path=(anchor)-[rels:KNOWLEDGE_RELATION*1..2]->(target:KnowledgeNode) "
        f"WHERE all(rel IN rels WHERE rel.relation_type IN split('{types}', '|')) "
        "RETURN target.chunk_id AS chunk_id, "
        "target.document_version_id AS document_version_id, "
        "target.source_url AS source_url, "
        "target.source_chunk_id AS source_chunk_id LIMIT $max_paths"
    )
