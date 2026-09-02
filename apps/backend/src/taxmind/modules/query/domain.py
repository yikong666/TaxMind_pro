from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from taxmind.modules.retrieval.application.planner import RetrievalPlan
from taxmind.modules.risk.evaluator import RuleEvaluation

QueryRunStatus = Literal["queued", "running", "completed", "failed", "needs_input"]
QueryRunEventType = Literal["started", "needs_input", "delta", "completed", "failed"]


@dataclass(frozen=True, slots=True)
class FinalAnswer:
    message_id: str
    text: str
    citation_ids: tuple[str, ...]
    gap_codes: tuple[str, ...]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class QueryRunEvent:
    id: str
    run_id: str
    sequence_no: int
    event_type: QueryRunEventType
    occurred_at: datetime
    payload: dict[str, object]


@dataclass(frozen=True, slots=True)
class QueryRun:
    id: str
    status: QueryRunStatus
    org_id: str
    case_id: str
    conversation_id: str
    request_message_id: str
    profile_version: int
    query_text: str
    facts_snapshot: dict[str, object]
    public_knowledge_snapshot_id: str | None
    org_knowledge_snapshot_id: str | None
    retrieval_plan: RetrievalPlan | None
    rule_results: tuple[RuleEvaluation, ...]
    rule_version_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    follow_up_fact_keys: tuple[str, ...]
    degradation_events: tuple[str, ...]
    model_profile_id: str | None
    prompt_bundle_version: str | None
    router_version: str
    retrieval_config_version: str
    idempotency_key: str
    request_id: str
    started_at: datetime | None
    completed_at: datetime | None
    error_code: str | None
    error_detail_safe: str | None
    final_answer: FinalAnswer | None
    created_at: datetime
    updated_at: datetime
    audit_resource_id: str
