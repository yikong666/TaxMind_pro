from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class PolicyRetrievalRequest:
    query: str
    region_code: str
    business_date: date

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise ValueError("query is required")
        if not self.region_code.strip():
            raise ValueError("region_code is required")


@dataclass(frozen=True, slots=True)
class PolicyEvidenceCandidate:
    chunk_id: str
    document_version_id: str
    source_url: str
    region_match: str
    policy_status: str
    review_status: str
    retrieval_reason: str

    def __post_init__(self) -> None:
        if not all(
            (self.chunk_id.strip(), self.document_version_id.strip(), self.source_url.strip())
        ):
            raise ValueError("evidence traceability fields are required")
        if self.policy_status != "active" or self.review_status != "published":
            raise ValueError("only active published evidence may enter retrieval")
