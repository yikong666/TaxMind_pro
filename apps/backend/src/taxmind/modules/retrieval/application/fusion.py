from __future__ import annotations

from dataclasses import dataclass

from taxmind.modules.retrieval.domain import PolicyEvidenceCandidate

_CHANNEL_WEIGHTS = {"exact": 1.4, "semantic": 1.0, "graph": 0.9}


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    candidate: PolicyEvidenceCandidate
    channel: str
    rank: int

    def __post_init__(self) -> None:
        if self.channel not in _CHANNEL_WEIGHTS:
            raise ValueError("unsupported retrieval channel")
        if self.rank < 1:
            raise ValueError("rank must be positive")


@dataclass(frozen=True, slots=True)
class EvidenceBundleItem:
    candidate: PolicyEvidenceCandidate
    rrf_score: float
    retrieval_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    items: tuple[EvidenceBundleItem, ...]


def build_evidence_bundle(
    ranked_candidates: list[RankedCandidate], *, limit: int = 12, rrf_k: int = 60
) -> EvidenceBundle:
    if not 1 <= limit <= 12:
        raise ValueError("limit must be between 1 and 12")
    if rrf_k < 1:
        raise ValueError("rrf_k must be positive")
    grouped: dict[str, list[RankedCandidate]] = {}
    for ranked in ranked_candidates:
        grouped.setdefault(ranked.candidate.chunk_id, []).append(ranked)
    items = [
        EvidenceBundleItem(
            candidate=entries[0].candidate,
            rrf_score=sum(
                _CHANNEL_WEIGHTS[entry.channel] / (rrf_k + entry.rank) for entry in entries
            ),
            retrieval_reasons=tuple(
                dict.fromkeys(entry.candidate.retrieval_reason for entry in entries)
            ),
        )
        for entries in grouped.values()
    ]
    return EvidenceBundle(
        items=tuple(sorted(items, key=lambda item: item.rrf_score, reverse=True)[:limit])
    )
