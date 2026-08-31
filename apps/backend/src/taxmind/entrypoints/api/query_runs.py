from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from taxmind.entrypoints.api.dependencies import current_principal
from taxmind.modules.cases.application.service import CasesService
from taxmind.modules.query.application.service import QueryRun, QueryRunCommand, QueryRunService
from taxmind.modules.risk.evaluator import RuleEvaluation
from taxmind.shared.contracts.api import ResponseMeta
from taxmind.shared.domain.principal import Principal

router = APIRouter(tags=["query-runs"])


class QueryRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=4000)


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
    profile_version: int
    retrieval_plan: RetrievalPlanData | None
    rule_results: list[RuleResultData]
    follow_up_fact_keys: list[str]
    degradation_events: list[str]
    audit_resource_id: str


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
            profile_version=detail.profile.profile_version,
            query=payload.query.strip(),
            facts=facts,
            request_id=request.state.request_id,
            org_id=principal.org_id,
            actor_id=principal.user_id,
            occurred_at=datetime.now(UTC),
        )
    )
    return QueryRunResponse(data=_run_data(run), meta=_meta(request))


@router.get("/query-runs/{run_id}", response_model=QueryRunResponse)
async def get_query_run(
    run_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> QueryRunResponse:
    run = _query_service(request).get(run_id)
    if run is None or run.org_id != principal.org_id:
        raise HTTPException(status_code=404, detail="查询运行不存在或已过期")
    return QueryRunResponse(data=_run_data(run), meta=_meta(request))


def _run_data(run: QueryRun) -> QueryRunData:
    return QueryRunData(
        id=run.id,
        status=run.status,
        case_id=run.case_id,
        profile_version=run.profile_version,
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
