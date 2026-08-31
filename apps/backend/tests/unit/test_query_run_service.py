from datetime import UTC, date, datetime

import pytest

from taxmind.modules.query.application.service import QueryRunCommand, QueryRunService
from taxmind.modules.risk.domain import RiskRuleDefinition


class _AuditRecorder:
    def __init__(self) -> None:
        self.entries: list[dict[str, object]] = []

    async def record(self, entry: dict[str, object]) -> None:
        self.entries.append(entry)


@pytest.mark.asyncio
async def test_query_run_interrupts_before_retrieval_when_scope_facts_are_missing() -> None:
    audit = _AuditRecorder()
    service = QueryRunService(rules=(), audit_recorder=audit)

    run = await service.submit(
        QueryRunCommand(
            case_id="case-1",
            profile_version=1,
            query="这项优惠是否适用",
            facts={},
            request_id="request-1",
            org_id="org-1",
            actor_id="user-1",
            occurred_at=datetime(2026, 8, 31, tzinfo=UTC),
        )
    )

    assert run.status == "need_info"
    assert run.retrieval_plan is None
    assert run.follow_up_fact_keys == ("business_date", "region_code")
    assert audit.entries[0]["action_code"] == "query.run.completed"


@pytest.mark.asyncio
async def test_query_run_preserves_deterministic_rule_result_and_audit_link() -> None:
    audit = _AuditRecorder()
    service = QueryRunService(
        rules=(
            RiskRuleDefinition(
                rule_version_id="risk-v1",
                severity="high",
                trigger_expression={"gte": {"fact_key": "invoice_amount", "value": 100}},
                missing_fact_policy="manual_review",
                basis_chunk_ids=("chunk-1",),
            ),
        ),
        audit_recorder=audit,
    )

    run = await service.submit(
        QueryRunCommand(
            case_id="case-1",
            profile_version=1,
            query="这项优惠是否适用",
            facts={
                "business_date": date(2026, 8, 31),
                "region_code": "440300",
                "invoice_amount": 120,
            },
            request_id="request-1",
            org_id="org-1",
            actor_id="user-1",
            occurred_at=datetime(2026, 8, 31, tzinfo=UTC),
        )
    )

    assert run.status == "completed"
    assert run.retrieval_plan is not None
    assert run.rule_results[0].status == "hit"
    assert run.rule_results[0].severity == "high"
    assert run.audit_resource_id == run.id
    assert audit.entries[0]["resource_id"] == run.id
