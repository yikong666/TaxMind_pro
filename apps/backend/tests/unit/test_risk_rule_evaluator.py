from taxmind.modules.risk.evaluator import evaluate_trigger


def test_missing_fact_produces_unknown_and_reports_key() -> None:
    result = evaluate_trigger({"gte": {"fact_key": "invoice_amount", "value": 100}}, {})
    assert result.truth_value == "unknown"
    assert result.missing_fact_keys == ("invoice_amount",)


def test_nested_boolean_expression_propagates_unknown_and_short_circuits_false() -> None:
    result = evaluate_trigger(
        {
            "all": [
                {"eq": {"fact_key": "vat_taxpayer_type", "value": "SMALL_SCALE"}},
                {"gte": {"fact_key": "invoice_amount", "value": 100}},
            ]
        },
        {"vat_taxpayer_type": "SMALL_SCALE"},
    )
    assert result.truth_value == "unknown"
    assert result.missing_fact_keys == ("invoice_amount",)

    false_result = evaluate_trigger(
        {
            "all": [
                {"eq": {"fact_key": "vat_taxpayer_type", "value": "GENERAL"}},
                {"gte": {"fact_key": "invoice_amount", "value": 100}},
            ]
        },
        {"vat_taxpayer_type": "SMALL_SCALE"},
    )
    assert false_result.truth_value == "false"
    assert false_result.missing_fact_keys == ()


def test_any_not_and_exists_use_deterministic_three_valued_semantics() -> None:
    result = evaluate_trigger(
        {
            "any": [
                {"not": {"exists": {"fact_key": "special_invoice"}}},
                {"eq": {"fact_key": "vat_taxpayer_type", "value": "GENERAL"}},
            ]
        },
        {"vat_taxpayer_type": "SMALL_SCALE"},
    )
    assert result.truth_value == "true"
    assert result.missing_fact_keys == ()
