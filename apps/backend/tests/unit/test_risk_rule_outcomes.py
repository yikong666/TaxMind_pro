from taxmind.modules.risk.domain import RiskRuleDefinition
from taxmind.modules.risk.evaluator import evaluate_rule


def test_missing_fact_policy_maps_unknown_to_a_safe_rule_outcome() -> None:
    rule = RiskRuleDefinition(
        rule_version_id="risk-v1",
        severity="high",
        trigger_expression={"eq": {"fact_key": "invoice_type", "value": "SPECIAL"}},
        missing_fact_policy="manual_review",
        basis_chunk_ids=("chunk-1",),
    )

    result = evaluate_rule(rule, {})

    assert result.status == "manual_review"
    assert result.severity is None
    assert result.missing_fact_keys == ("invoice_type",)


def test_true_trigger_is_a_hit_with_rule_defined_severity() -> None:
    rule = RiskRuleDefinition(
        rule_version_id="risk-v1",
        severity="medium",
        trigger_expression={"eq": {"fact_key": "invoice_type", "value": "SPECIAL"}},
        missing_fact_policy="need_info",
        basis_chunk_ids=("chunk-1",),
    )

    result = evaluate_rule(rule, {"invoice_type": "SPECIAL"})

    assert result.status == "hit"
    assert result.severity == "medium"
