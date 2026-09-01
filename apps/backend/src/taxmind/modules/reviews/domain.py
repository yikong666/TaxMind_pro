from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

ReviewDecision = Literal["approved", "conditionally_approved", "returned", "escalated"]
ReviewTaskStatus = Literal["pending_review", "returned", "approved", "escalated", "superseded"]


@dataclass(frozen=True, slots=True)
class ReviewTaskRecord:
    id: str
    org_id: str
    case_id: str
    profile_version: int
    query_run_id: str | None
    submitted_by: str
    assigned_to: str | None
    status: ReviewTaskStatus
    priority: str
    package_summary: dict[str, object]
    version_no: int
    submitted_at: datetime
    resolved_at: datetime | None


@dataclass(frozen=True, slots=True)
class ReviewActionRecord:
    id: str
    task_id: str
    action_no: int
    decision: ReviewDecision
    comment_safe: str | None
    actor_user_id: str
    occurred_at: datetime | None


@dataclass(frozen=True, slots=True)
class ReviewTaskDetail:
    task: ReviewTaskRecord
    actions: list[ReviewActionRecord]


def aggregate_decisions(actions: list[ReviewActionRecord]) -> ReviewTaskStatus:
    if not actions:
        return "pending_review"
    decision = actions[-1].decision
    if decision == "conditionally_approved":
        return "approved"
    return decision
