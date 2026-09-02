from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import StreamingResponse

from taxmind.entrypoints.api.dependencies import current_principal
from taxmind.modules.cases.application.service import CasesService
from taxmind.modules.query.application.service import QueryRunCommand, QueryRunService
from taxmind.modules.query.domain import QueryRun, QueryRunEvent
from taxmind.modules.risk.evaluator import RuleEvaluation
from taxmind.shared.contracts.api import ResponseMeta
from taxmind.shared.domain.principal import Principal

router = APIRouter(tags=["query-runs"])


class QueryRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=4000)
    conversation_id: str = Field(min_length=1, max_length=36)
    idempotency_key: str = Field(min_length=8, max_length=100)


class RetrievalPlanData(BaseModel):
    route_code: str
    use_mysql_exact: bool
    use_milvus_semantic: bool
    graph_expansion_type: str | None


class RuleResultData(BaseModel):
    rule_version_id: str
    status: str
    severity: str | None
    missing_fact_keys: list[str]
    basis_chunk_ids: list[str]


class QueryRunData(BaseModel):
    id: str
    status: str
    case_id: str
    conversation_id: str
    profile_version: int
    facts_snapshot: dict[str, object]
    public_knowledge_snapshot_id: str | None
    org_knowledge_snapshot_id: str | None
    retrieval_plan: RetrievalPlanData | None
    rule_results: list[RuleResultData]
    follow_up_fact_keys: list[str]
    degradation_events: list[str]
    rule_version_ids: list[str]
    evidence_ids: list[str]
    model_profile_id: str | None
    prompt_bundle_version: str | None
    started_at: datetime | None
    completed_at: datetime | None
    error_code: str | None
    error_detail_safe: str | None
    final_answer: FinalAnswerData | None
    audit_resource_id: str


class FinalAnswerData(BaseModel):
    message_id: str
    text: str
    citation_ids: list[str]
    gap_codes: list[str]
    created_at: datetime


class QueryRunResponse(BaseModel):
    data: QueryRunData
    meta: ResponseMeta


def _query_service(request: Request) -> QueryRunService:
    service = cast(dict[str, object], request.app.state.services).get("query_runs")
    if not isinstance(service, QueryRunService):
        raise RuntimeError("query runs service is not configured")
    return service


def _cases_service(request: Request) -> CasesService:
    service = cast(dict[str, object], request.app.state.services).get("cases")
    if not isinstance(service, CasesService):
        raise RuntimeError("cases service is not configured")
    return service


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(request_id=request.state.request_id)


@router.post("/cases/{case_id}/query-runs", response_model=QueryRunResponse)
async def submit_query_run(
    case_id: str,
    payload: QueryRunRequest,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> QueryRunResponse:
    detail = await _cases_service(request).get_case(case_id, principal)
    facts: dict[str, object] = {
        "business_date": detail.profile.business_date,
        "region_code": detail.profile.region_code,
        "vat_taxpayer_type": detail.profile.vat_taxpayer_type,
        **{
            fact.fact_key: fact.value
            for fact in detail.facts
            if fact.confirmation_status == "confirmed"
        },
    }
    run = await _query_service(request).submit(
        QueryRunCommand(
            case_id=detail.case.id,
            conversation_id=payload.conversation_id,
            profile_version=detail.profile.profile_version,
            query=payload.query.strip(),
            facts=facts,
            idempotency_key=payload.idempotency_key,
            request_id=request.state.request_id,
            occurred_at=datetime.now(UTC),
        ),
        principal,
    )
    return QueryRunResponse(data=_run_data(run), meta=_meta(request))


@router.get("/query-runs/{run_id}", response_model=QueryRunResponse)
async def get_query_run(
    run_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> QueryRunResponse:
    run = await _query_service(request).get(run_id, principal)
    if run is None:
        raise HTTPException(status_code=404, detail="查询运行不存在或已过期")
    await _cases_service(request).get_case(run.case_id, principal)
    return QueryRunResponse(data=_run_data(run), meta=_meta(request))


@router.get(
    "/query-runs/{run_id}/events",
    responses={
        200: {
            "description": "按事件序号重放的查询运行 SSE 事件流",
            "content": {"text/event-stream": {"schema": {"type": "string"}}},
        }
    },
)
async def stream_query_run_events(
    run_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    after_sequence = _event_cursor(run_id, last_event_id)
    events = await _query_service(request).list_events(
        run_id,
        after_sequence=after_sequence,
        principal=principal,
    )
    return StreamingResponse(
        _sse_events(events),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _run_data(run: QueryRun) -> QueryRunData:
    return QueryRunData(
        id=run.id,
        status=run.status,
        case_id=run.case_id,
        conversation_id=run.conversation_id,
        profile_version=run.profile_version,
        facts_snapshot=run.facts_snapshot,
        public_knowledge_snapshot_id=run.public_knowledge_snapshot_id,
        org_knowledge_snapshot_id=run.org_knowledge_snapshot_id,
        retrieval_plan=(
            RetrievalPlanData(
                route_code=run.retrieval_plan.route_code,
                use_mysql_exact=run.retrieval_plan.use_mysql_exact,
                use_milvus_semantic=run.retrieval_plan.use_milvus_semantic,
                graph_expansion_type=run.retrieval_plan.graph_expansion_type,
            )
            if run.retrieval_plan is not None
            else None
        ),
        rule_results=[_rule_result_data(item) for item in run.rule_results],
        follow_up_fact_keys=list(run.follow_up_fact_keys),
        degradation_events=list(run.degradation_events),
        rule_version_ids=list(run.rule_version_ids),
        evidence_ids=list(run.evidence_ids),
        model_profile_id=run.model_profile_id,
        prompt_bundle_version=run.prompt_bundle_version,
        started_at=run.started_at,
        completed_at=run.completed_at,
        error_code=run.error_code,
        error_detail_safe=run.error_detail_safe,
        final_answer=(
            FinalAnswerData(
                message_id=run.final_answer.message_id,
                text=run.final_answer.text,
                citation_ids=list(run.final_answer.citation_ids),
                gap_codes=list(run.final_answer.gap_codes),
                created_at=run.final_answer.created_at,
            )
            if run.final_answer is not None
            else None
        ),
        audit_resource_id=run.audit_resource_id,
    )


def _rule_result_data(result: RuleEvaluation) -> RuleResultData:
    return RuleResultData(
        rule_version_id=result.rule_version_id,
        status=result.status,
        severity=result.severity,
        missing_fact_keys=list(result.missing_fact_keys),
        basis_chunk_ids=list(result.basis_chunk_ids),
    )


def _event_cursor(run_id: str, last_event_id: str | None) -> int:
    if last_event_id is None:
        return 0
    prefix, separator, raw_sequence = last_event_id.rpartition(":")
    if separator != ":" or prefix != run_id:
        raise HTTPException(status_code=400, detail="Last-Event-ID 与当前运行不匹配")
    try:
        sequence_no = int(raw_sequence)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Last-Event-ID 无效") from exc
    if sequence_no < 0:
        raise HTTPException(status_code=400, detail="Last-Event-ID 无效")
    return sequence_no


async def _sse_events(events: list[QueryRunEvent]) -> AsyncIterator[str]:
    for event in events:
        payload = {
            "run_id": event.run_id,
            "sequence_no": event.sequence_no,
            "occurred_at": event.occurred_at.isoformat(),
            **event.payload,
        }
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        yield f"id: {event.run_id}:{event.sequence_no}\nevent: {event.event_type}\ndata: {data}\n\n"
