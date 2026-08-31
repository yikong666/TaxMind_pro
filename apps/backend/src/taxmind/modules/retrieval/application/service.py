from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from taxmind.modules.retrieval.domain import PolicyEvidenceCandidate, PolicyRetrievalRequest


class RetrievalUnavailable(RuntimeError):
    """A rebuildable retrieval projection is temporarily unavailable."""


class PolicyExactSearchPort(Protocol):
    async def search(
        self, request: PolicyRetrievalRequest, *, limit: int
    ) -> list[PolicyEvidenceCandidate]: ...


class PolicySemanticSearchPort(Protocol):
    async def search(
        self, request: PolicyRetrievalRequest, *, limit: int
    ) -> list[PolicyEvidenceCandidate]: ...


@dataclass(frozen=True, slots=True)
class PolicyRetrievalResult:
    exact_candidates: list[PolicyEvidenceCandidate]
    semantic_candidates: list[PolicyEvidenceCandidate]
    degraded: bool
    degradation_reason: str | None


class PolicyRetrievalService:
    """Retrieve authoritative exact evidence before optional vector candidates."""

    def __init__(
        self,
        *,
        exact_search: PolicyExactSearchPort,
        semantic_search: PolicySemanticSearchPort,
    ) -> None:
        self._exact_search = exact_search
        self._semantic_search = semantic_search

    async def search(self, request: PolicyRetrievalRequest, *, limit: int) -> PolicyRetrievalResult:
        if limit < 1:
            raise ValueError("limit must be positive")
        exact_candidates = await self._exact_search.search(request, limit=limit)
        try:
            semantic_candidates = await self._semantic_search.search(request, limit=limit)
        except RetrievalUnavailable:
            return PolicyRetrievalResult(
                exact_candidates=exact_candidates,
                semantic_candidates=[],
                degraded=True,
                degradation_reason="semantic_retrieval_unavailable",
            )
        return PolicyRetrievalResult(
            exact_candidates=exact_candidates,
            semantic_candidates=semantic_candidates,
            degraded=False,
            degradation_reason=None,
        )
