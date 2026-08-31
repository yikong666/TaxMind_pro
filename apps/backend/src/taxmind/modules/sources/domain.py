from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SourceSiteRecord:
    id: str
    name: str
    base_url: str
    domain: str
    source_level: str
    authority_name: str
    region_code: str
    collection_method: str
    whitelist_rules: dict[str, object]
    crawl_interval_minutes: int | None
    status: str
    last_checked_at: datetime | None
    created_by: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class IngestionJobRecord:
    id: str
    source_site_id: str
    job_type: str
    trigger_type: str
    source_url: str | None
    input_object_key: str | None
    dedupe_key: str
    status: str
    attempt_count: int
    discovered_count: int
    changed_count: int
    error_code: str | None
    error_detail_safe: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_by: str
    created_at: datetime
    updated_at: datetime
