from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class ProcedureDefinition:
    procedure_version_id: str
    procedure_code: str
    title: str
    region_code: str
    effective_start: date | None
    effective_end: date | None
    review_status: str
    official_url: str
    source_chunk_ids: tuple[str, ...]
    materials: tuple[str, ...]
    channels: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.procedure_version_id.strip() or not self.procedure_code.strip():
            raise ValueError("procedure identifiers are required")
        if not self.title.strip() or len(self.region_code) != 6 or not self.region_code.isdigit():
            raise ValueError("title and region_code are required")
        if self.review_status != "published":
            raise ValueError("procedure must be published")
        if not self.official_url.startswith(("https://", "http://")):
            raise ValueError("official_url is required")
        if not self.source_chunk_ids or not all(item.strip() for item in self.source_chunk_ids):
            raise ValueError("source_chunk_ids are required")
        if (
            self.effective_end
            and self.effective_start
            and self.effective_end < self.effective_start
        ):
            raise ValueError("effective_end cannot precede effective_start")
