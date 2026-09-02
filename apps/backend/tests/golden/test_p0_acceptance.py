from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from taxmind.modules.query.application.service import QueryRunCommand, QueryRunService
from taxmind.modules.risk.domain import RiskRuleDefinition


class _AuditRecorder:
    def __init__(self) -> None:
        self.entries: list[dict[str, object]] = []

    async def record(self, entry: dict[str, object]) -> None:
        self.entries.append(entry)


@pytest.mark.asyncio
async def test_p0_golden_scope_gate_requires_business_date_and_region() -> None:
    audit = _AuditRecorder()
    service = QueryRunService(rules=(), audit_recorder=audit)

    run = await service.submit(
        QueryRunCommand(
            case_id="golden-case-scope",
            profile_version=1,
            query="虚构优惠是否适用",
            facts={},
            request_id="golden-request-scope",
            org_id="golden-org",
            actor_id="golden-user",
            occurred_at=datetime(2026, 9, 1, tzinfo=UTC),
        )
    )

    assert run.status == "need_info"
    assert run.follow_up_fact_keys == ("business_date", "region_code")
    assert audit.entries[0]["after_json"] == {
        "case_id": "golden-case-scope",
        "profile_version": 1,
        "route_code": None,
        "follow_up_fact_keys": ["business_date", "region_code"],
        "rule_version_ids": [],
    }
    assert "query" not in audit.entries[0]["after_json"]


@pytest.mark.asyncio
async def test_p0_golden_risk_result_is_deterministic_and_retains_basis() -> None:
    audit = _AuditRecorder()
    service = QueryRunService(
        rules=(
            RiskRuleDefinition(
                rule_version_id="golden-risk-v1",
                severity="high",
                trigger_expression={"gte": {"fact_key": "invoice_amount", "value": 100}},
                missing_fact_policy="manual_review",
                basis_chunk_ids=("golden-basis-chunk",),
            ),
        ),
        audit_recorder=audit,
    )

    run = await service.submit(
        QueryRunCommand(
            case_id="golden-case-risk",
            profile_version=1,
            query="虚构风险审查",
            facts={
                "business_date": date(2026, 9, 1),
                "region_code": "440300",
                "invoice_amount": 100,
            },
            request_id="golden-request-risk",
            org_id="golden-org",
            actor_id="golden-user",
            occurred_at=datetime(2026, 9, 1, tzinfo=UTC),
        )
    )

    assert run.status == "completed"
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
