from __future__ import annotations

from taxmind.modules.retrieval.application.fusion import RankedCandidate, build_evidence_bundle
from taxmind.modules.retrieval.domain import PolicyEvidenceCandidate


def _candidate(chunk_id: str, reason: str) -> PolicyEvidenceCandidate:
    return PolicyEvidenceCandidate(
        chunk_id=chunk_id,
        document_version_id=f"version-{chunk_id}",
        source_url=f"https://example.invalid/{chunk_id}",
        region_match="local",
        policy_status="active",
        review_status="published",
        retrieval_reason=reason,
    )


def test_evidence_bundle_deduplicates_candidates_and_preserves_retrieval_reasons() -> None:
    bundle = build_evidence_bundle(
        [
            RankedCandidate(_candidate("chunk-1", "mysql_exact"), channel="exact", rank=1),
            RankedCandidate(_candidate("chunk-1", "milvus_semantic"), channel="semantic", rank=2),
            RankedCandidate(_candidate("chunk-2", "milvus_semantic"), channel="semantic", rank=1),
        ]
    )

    assert [item.candidate.chunk_id for item in bundle.items] == ["chunk-1", "chunk-2"]
    assert bundle.items[0].retrieval_reasons == ("mysql_exact", "milvus_semantic")
    assert bundle.items[0].rrf_score > bundle.items[1].rrf_score
