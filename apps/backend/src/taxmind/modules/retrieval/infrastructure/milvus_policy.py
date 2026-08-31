from __future__ import annotations

from typing import Any, Protocol

from taxmind.modules.retrieval.application.service import RetrievalUnavailable
from taxmind.modules.retrieval.domain import PolicyEvidenceCandidate, PolicyRetrievalRequest


class QueryEmbeddingPort(Protocol):
    async def embed_query(self, query: str) -> list[float]: ...


class MilvusSearchClient(Protocol):
    def search(self, **kwargs: object) -> list[list[dict[str, object]]]: ...


class MilvusPolicySearchAdapter:
    """Search the active Milvus projection behind a non-bypassable scope gate."""

    def __init__(
        self,
        *,
        client: MilvusSearchClient,
        embedder: QueryEmbeddingPort,
        collection_name: str,
    ) -> None:
        if not collection_name.strip():
            raise ValueError("collection_name is required")
        self._client = client
        self._embedder = embedder
        self._collection_name = collection_name

    async def search(
        self, request: PolicyRetrievalRequest, *, limit: int
    ) -> list[PolicyEvidenceCandidate]:
        if limit < 1:
            raise ValueError("limit must be positive")
        try:
            vector = await self._embedder.embed_query(request.query)
            results = self._client.search(
                collection_name=self._collection_name,
                data=[vector],
                anns_field="dense_vector",
                filter=_scope_filter(request),
                output_fields=[
                    "chunk_id",
                    "document_version_id",
                    "source_url",
                    "region_code",
                    "policy_status",
                    "review_status",
                ],
                limit=limit,
            )
        except Exception as exc:
            raise RetrievalUnavailable("Milvus semantic retrieval is unavailable") from exc
        return _candidates(results, request=request)


def _scope_filter(request: PolicyRetrievalRequest) -> str:
    business_date = request.business_date.isoformat()
    return " && ".join(
        (
            'review_status == "published"',
            'policy_status == "active"',
            f'region_code in ["{request.region_code}", "000000"]',
            f'effective_start <= "{business_date}"',
            f'effective_end >= "{business_date}"',
        )
    )


def _candidates(
    results: list[list[dict[str, object]]], *, request: PolicyRetrievalRequest
) -> list[PolicyEvidenceCandidate]:
    candidates: list[PolicyEvidenceCandidate] = []
    for hit in results[0] if results else []:
        entity = hit.get("entity", hit)
        if not isinstance(entity, dict):
            continue
        region_code = entity.get("region_code")
        try:
            candidates.append(
                PolicyEvidenceCandidate(
                    chunk_id=_required_text(entity, "chunk_id"),
                    document_version_id=_required_text(entity, "document_version_id"),
                    source_url=_required_text(entity, "source_url"),
                    region_match=(
                        "local" if region_code == request.region_code else "national_only"
                    ),
                    policy_status=_required_text(entity, "policy_status"),
                    review_status=_required_text(entity, "review_status"),
                    retrieval_reason="milvus_semantic",
                )
            )
        except ValueError:
            continue
    return candidates


def _required_text(entity: dict[str, Any], field: str) -> str:
    value = entity.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required")
    return value
