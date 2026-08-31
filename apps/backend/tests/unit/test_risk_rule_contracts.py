from __future__ import annotations

import pytest

from taxmind.modules.risk.domain import RiskRuleDefinition


def test_risk_rule_requires_basis_evidence_and_whitelisted_operator() -> None:
    rule = RiskRuleDefinition(
        rule_version_id="rule-v1",
        severity="high",
        trigger_expression={"gte": {"fact_key": "invoice_amount", "value": 100000}},
        missing_fact_policy="manual_review",
        basis_chunk_ids=("chunk-1",),
    )
    assert rule.severity == "high"

    with pytest.raises(ValueError, match="basis"):
        RiskRuleDefinition(
            rule_version_id="rule-v2",
            severity="high",
            trigger_expression={"gte": {"fact_key": "invoice_amount", "value": 100000}},
            missing_fact_policy="manual_review",
            basis_chunk_ids=(),
        )

    with pytest.raises(ValueError, match="operator"):
        RiskRuleDefinition(
            rule_version_id="rule-v3",
            severity="high",
            trigger_expression={"sql": "DROP TABLE risk_rules"},
            missing_fact_policy="manual_review",
            basis_chunk_ids=("chunk-1",),
        )

    with pytest.raises(ValueError, match="operator"):
        RiskRuleDefinition(
            rule_version_id="rule-v4",
            severity="high",
            trigger_expression={
                "all": [
                    {"eq": {"fact_key": "vat_taxpayer_type", "value": "SMALL_SCALE"}},
                    {"sql": "DROP TABLE risk_rules"},
                ]
            },
            missing_fact_policy="manual_review",
            basis_chunk_ids=("chunk-1",),
        )
