from __future__ import annotations

import pytest

from taxmind.infrastructure.projections.contracts import (
    GraphRelationProjectionRecord,
    PolicyChunkProjectionRecord,
    ProjectionWriteResult,
)


def test_policy_projection_record_keeps_snapshot_and_evidence_traceability() -> None:
    record = PolicyChunkProjectionRecord(
        snapshot_id="snapshot-1",
        snapshot_code="public-20260831",
        chunk_id="chunk-1",
        source_chunk_id="doc-1:article-1",
        document_id="document-1",
        document_version_id="version-1",
        source_url="https://example.invalid/policy/1",
        region_code="440300",
        effective_start="2026-01-01",
        effective_end=None,
        policy_status="active",
        review_status="published",
        content_hash="a" * 64,
        embedding_version="pending-v1",
        dense_vector=(0.1, 0.2),
    )

    assert record.snapshot_id == "snapshot-1"
    assert record.review_status == "published"


def test_graph_projection_record_requires_source_chunk_reference() -> None:
    with pytest.raises(ValueError, match="source_chunk_id"):
        GraphRelationProjectionRecord(
            snapshot_id="snapshot-1",
            relation_id="relation-1",
            from_node_id="document-1",
            to_node_id="clause-1",
            relation_type="CONTAINS",
            source_chunk_id="",
            source_url="https://example.invalid/policy/1",
            content_hash="b" * 64,
        )


def test_projection_write_result_never_implies_snapshot_activation() -> None:
    result = ProjectionWriteResult(
        projection_type="milvus_policy",
        snapshot_id="snapshot-1",
        projected_count=1,
        status="succeeded",
    )

    assert result.status == "succeeded"
    assert not hasattr(result, "activated")
