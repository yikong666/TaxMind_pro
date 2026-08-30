from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class SourceDocumentRecord:
    id: str
    canonical_key: str
    title: str
    doc_no: str | None
    doc_type: str
    source_level: str
    issuing_authority: str
    region_code: str
    publish_date: date | None
    effective_start: date | None
    effective_end: date | None
    policy_status: str
    canonical_url: str
    current_version_id: str | None
    review_status: str
    created_by: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class DocumentVersionRecord:
    id: str
    document_id: str
    version_no: int
    captured_at: datetime
    source_url: str
    raw_object_key: str | None
    parsed_object_key: str | None
    mime_type: str
    content_hash_sha256: str
    parse_status: str
    ocr_status: str
    review_status: str
    published_at: datetime | None
    supersedes_version_id: str | None
    created_by: str


@dataclass(frozen=True, slots=True)
class DocumentChunkRecord:
    id: str
    document_id: str
    document_version_id: str
    source_chunk_id: str
    chunk_order: int
    chunk_type: str
    heading_path: str
    clause_label: str | None
    content_text: str
    content_hash_sha256: str
    token_count: int
    effective_start: date | None
    effective_end: date | None
    region_code: str
    policy_status: str
    review_status: str
    index_status: str


@dataclass(frozen=True, slots=True)
class DocumentDetail:
    document: SourceDocumentRecord
    version: DocumentVersionRecord
    chunks: list[DocumentChunkRecord]


@dataclass(frozen=True, slots=True)
class PolicyEvidence:
    document: SourceDocumentRecord
    version: DocumentVersionRecord
    chunk: DocumentChunkRecord
    region_match: str
