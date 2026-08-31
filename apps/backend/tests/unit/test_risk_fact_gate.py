from taxmind.modules.risk.fact_gate import require_scope_facts


def test_scope_gate_interrupts_when_required_facts_are_missing() -> None:
    result = require_scope_facts(business_date=None, region_code=None)
    assert result.should_interrupt is True
    assert result.missing_fact_keys == ("business_date", "region_code")
