from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal, Protocol

from taxmind.modules.retrieval.application.planner import (
    QueryFacts,
    RetrievalPlan,
    build_retrieval_plan,
)
from taxmind.modules.risk.domain import RiskRuleDefinition
from taxmind.modules.risk.evaluator import RuleEvaluation, evaluate_rule
from taxmind.modules.risk.fact_gate import require_scope_facts
from taxmind.shared.domain.ids import new_id

QueryRunStatus = Literal["completed", "need_info"]


class QueryAuditRecorder(Protocol):
    async def record(self, entry: dict[str, object]) -> None: ...


@dataclass(frozen=True, slots=True)
class QueryRunCommand:
    case_id: str
    profile_version: int
    query: str
    facts: dict[str, object]
    request_id: str
    org_id: str
    actor_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class QueryRun:
    id: str
    status: QueryRunStatus
    org_id: str
    case_id: str
    profile_version: int
    retrieval_plan: RetrievalPlan | None
    rule_results: tuple[RuleEvaluation, ...]
    follow_up_fact_keys: tuple[str, ...]
    degradation_events: tuple[str, ...]
    audit_resource_id: str


class QueryRunService:
    """Runs scope gates, routing and governed rules without an LLM decision path."""

    def __init__(
        self,
        *,
        rules: tuple[RiskRuleDefinition, ...],
        audit_recorder: QueryAuditRecorder,
    ) -> None:
        self._rules = rules
        self._audit_recorder = audit_recorder
        self._runs: dict[str, QueryRun] = {}

    async def submit(self, command: QueryRunCommand) -> QueryRun:
        run_id = new_id()
        gate = require_scope_facts(
            business_date=_as_date(command.facts.get("business_date")),
            region_code=_as_region(command.facts.get("region_code")),
        )
        if gate.should_interrupt:
            run = QueryRun(
                id=run_id,
                status="need_info",
                org_id=command.org_id,
                case_id=command.case_id,
                profile_version=command.profile_version,
                retrieval_plan=None,
                rule_results=(),
                follow_up_fact_keys=gate.missing_fact_keys,
                degradation_events=(),
                audit_resource_id=run_id,
            )
        else:
            plan = build_retrieval_plan(
                query=command.query,
                facts=QueryFacts(
                    business_date=_as_date(command.facts.get("business_date")),
                    region_code=_as_region(command.facts.get("region_code")),
                    taxpayer_type=_as_text(command.facts.get("vat_taxpayer_type")),
                ),
            )
            rule_results = tuple(evaluate_rule(rule, command.facts) for rule in self._rules)
            follow_up = tuple(
                dict.fromkeys(key for result in rule_results for key in result.missing_fact_keys)
            )
            run = QueryRun(
                id=run_id,
                status="need_info" if plan.should_interrupt or follow_up else "completed",
                org_id=command.org_id,
                case_id=command.case_id,
                profile_version=command.profile_version,
                retrieval_plan=plan,
                rule_results=rule_results,
                follow_up_fact_keys=tuple(dict.fromkeys((*plan.missing_facts, *follow_up))),
                degradation_events=("out_of_scope",) if plan.route_code == "out_of_scope" else (),
                audit_resource_id=run_id,
            )
        await self._audit_recorder.record(
            {
                "action_code": "query.run.completed",
                "resource_id": run.id,
                "org_id": command.org_id,
                "actor_id": command.actor_id,
                "request_id": command.request_id,
                "occurred_at": command.occurred_at,
                "result": run.status,
                "after_json": {
                    "case_id": command.case_id,
                    "profile_version": command.profile_version,
                    "route_code": run.retrieval_plan.route_code
                    if run.retrieval_plan is not None
                    else None,
                    "follow_up_fact_keys": list(run.follow_up_fact_keys),
                    "rule_version_ids": [result.rule_version_id for result in run.rule_results],
                },
            }
        )
        self._runs[run.id] = run
        return run

    def get(self, run_id: str) -> QueryRun | None:
        return self._runs.get(run_id)


def _as_date(value: object) -> date | None:
    return value if isinstance(value, date) else None


def _as_region(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _as_text(value: object) -> str | None:
    return value if isinstance(value, str) else None
