from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

FeedbackStatus = Literal["submitted", "accepted", "resolved", "rejected"]
FeedbackErrorType = Literal[
    "citation_error", "policy_scope_error", "risk_rule_error", "procedure_error", "other"
]
FeedbackDecision = Literal["accepted", "resolved", "rejected"]


@dataclass(frozen=True, slots=True)
class FeedbackItem:
    id: str
    org_id: str
    case_id: str | None
    profile_version: int | None
    resource_type: str
    resource_id: str
    location_key: str | None
    error_type: FeedbackErrorType
    description_safe: str
    status: FeedbackStatus
    linked_knowledge_object_id: str | None
    resolution_safe: str | None
    submitted_by: str
    handled_by: str | None
    version_no: int
    submitted_at: datetime
    resolved_at: datetime | None
