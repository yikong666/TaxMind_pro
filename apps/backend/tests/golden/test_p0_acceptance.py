from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from _query_run_support import make_service

from taxmind.modules.query.application.service import QueryRunCommand
from taxmind.modules.risk.domain import RiskRuleDefinition


@pytest.mark.asyncio
async def test_p0_golden_scope_gate_requires_business_date_and_region() -> None:
    service, principal, repository = make_service(
        rules=(),
        org_id="golden-org",
        case_id="golden-case-scope",
        conversation_id="golden-conversation-scope",
        user_id="golden-user",
    )

    run = await service.submit(
        QueryRunCommand(
            case_id="golden-case-scope",
            conversation_id="golden-conversation-scope",
            profile_version=1,
            query="虚构优惠是否适用",
            facts={},
            idempotency_key="golden-scope-key",
            request_id="golden-request-scope",
            occurred_at=datetime(2026, 9, 1, tzinfo=UTC),
        ),
        principal,
    )

    assert run.status == "needs_input"
    assert run.follow_up_fact_keys == ("business_date", "region_code")
    assert repository.audit_actions == ["query.run.needs_input"]


@pytest.mark.asyncio
async def test_p0_golden_risk_result_is_deterministic_and_retains_basis() -> None:
    service, principal, _ = make_service(
        rules=(
            RiskRuleDefinition(
                rule_version_id="golden-risk-v1",
                severity="high",
                trigger_expression={"gte": {"fact_key": "invoice_amount", "value": 100}},
                missing_fact_policy="manual_review",
                basis_chunk_ids=("golden-basis-chunk",),
            ),
        ),
        org_id="golden-org",
        case_id="golden-case-risk",
        conversation_id="golden-conversation-risk",
        user_id="golden-user",
    )

    run = await service.submit(
        QueryRunCommand(
            case_id="golden-case-risk",
            conversation_id="golden-conversation-risk",
            profile_version=1,
            query="虚构风险审查",
            facts={
                "business_date": date(2026, 9, 1),
                "region_code": "440300",
                "invoice_amount": 100,
            },
            idempotency_key="golden-risk-key",
            request_id="golden-request-risk",
            occurred_at=datetime(2026, 9, 1, tzinfo=UTC),
        ),
        principal,
    )

    assert run.status == "queued"
    assert [(item.status, item.severity, item.basis_chunk_ids) for item in run.rule_results] == [
        ("hit", "high", ("golden-basis-chunk",))
    ]


def test_p0_golden_api_contract_never_exposes_audit_payload_snapshots(tmp_path: Path) -> None:
    from taxmind.bootstrap.settings import Settings
    from taxmind.entrypoints.api.main import create_app

    schema = create_app(
        Settings(app_env="test", app_debug=False, log_dir=tmp_path / "logs")
    ).openapi()

    properties = schema["components"]["schemas"]["AuditLogData"]["properties"]
    assert {"before_json", "after_json", "ip_hash", "user_agent_hash"}.isdisjoint(properties)
