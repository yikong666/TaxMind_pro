from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from taxmind.modules.risk.domain import RiskRuleDefinition, Severity

TruthValue = Literal["true", "false", "unknown"]


@dataclass(frozen=True, slots=True)
class TriggerEvaluation:
    truth_value: TruthValue
    missing_fact_keys: tuple[str, ...]


RuleOutcomeStatus = Literal["hit", "not_hit", "need_info", "manual_review"]


@dataclass(frozen=True, slots=True)
class RuleEvaluation:
    rule_version_id: str
    status: RuleOutcomeStatus
    severity: Severity | None
    missing_fact_keys: tuple[str, ...]
    basis_chunk_ids: tuple[str, ...]


def evaluate_trigger(expression: dict[str, object], facts: dict[str, object]) -> TriggerEvaluation:
    operator, operand = next(iter(expression.items()))
    if operator in {"all", "any"}:
        if not isinstance(operand, list) or not operand:
            raise ValueError(f"{operator} requires one or more expressions")
        evaluations = [_evaluate_child(item, facts) for item in operand]
        if operator == "all":
            false_result = next((item for item in evaluations if item.truth_value == "false"), None)
            if false_result is not None:
                return TriggerEvaluation("false", ())
            return _unknown_or("true", evaluations)
        true_result = next((item for item in evaluations if item.truth_value == "true"), None)
        if true_result is not None:
            return TriggerEvaluation("true", ())
        return _unknown_or("false", evaluations)
    if operator == "not":
        result = _evaluate_child(operand, facts)
        if result.truth_value == "unknown":
            return result
        return TriggerEvaluation("false" if result.truth_value == "true" else "true", ())
    if not isinstance(operand, dict):
        raise ValueError(f"{operator} requires an object operand")
    fact_key = operand.get("fact_key")
    if not isinstance(fact_key, str) or not fact_key.strip():
        raise ValueError("fact_key is required")
    if operator == "exists":
        return TriggerEvaluation("true" if fact_key in facts else "false", ())
    if fact_key not in facts:
        return TriggerEvaluation("unknown", (fact_key,))
    actual = facts[fact_key]
    expected = operand.get("value")
    if operator in {"eq", "ne"}:
        is_equal = actual == expected
        return TriggerEvaluation("true" if is_equal == (operator == "eq") else "false", ())
    if operator in {"gt", "gte", "lt", "lte"}:
        if not isinstance(expected, (int, float)) or not isinstance(actual, (int, float)):
            raise ValueError(f"{operator} requires numeric values")
        comparisons = {
            "gt": actual > expected,
            "gte": actual >= expected,
            "lt": actual < expected,
            "lte": actual <= expected,
        }
        return TriggerEvaluation("true" if comparisons[operator] else "false", ())
    if operator in {"in", "not_in"}:
        if not isinstance(expected, list):
            raise ValueError(f"{operator} requires a list value")
        included = actual in expected
        return TriggerEvaluation("true" if included == (operator == "in") else "false", ())
    if operator == "between":
        if not isinstance(expected, list) or len(expected) != 2:
            raise ValueError("between requires a two-value list")
        lower, upper = expected
        if not all(isinstance(item, (int, float)) for item in (actual, lower, upper)):
            raise ValueError("between requires numeric values")
        return TriggerEvaluation("true" if lower <= actual <= upper else "false", ())
    if operator in {"contains_any", "contains_all"}:
        if not isinstance(actual, list) or not isinstance(expected, list):
            raise ValueError(f"{operator} requires list values")
        matches = [item in actual for item in expected]
        matched = any(matches) if operator == "contains_any" else all(matches)
        return TriggerEvaluation("true" if matched else "false", ())
    raise ValueError("unsupported rule operator")


def evaluate_rule(rule: RiskRuleDefinition, facts: dict[str, object]) -> RuleEvaluation:
    trigger = evaluate_trigger(rule.trigger_expression, facts)
    if trigger.truth_value == "true":
        return RuleEvaluation(rule.rule_version_id, "hit", rule.severity, (), rule.basis_chunk_ids)
    if trigger.truth_value == "false":
        return RuleEvaluation(rule.rule_version_id, "not_hit", None, (), rule.basis_chunk_ids)
    return RuleEvaluation(
        rule.rule_version_id,
        rule.missing_fact_policy,
        None,
        trigger.missing_fact_keys,
        rule.basis_chunk_ids,
    )


def _evaluate_child(expression: object, facts: dict[str, object]) -> TriggerEvaluation:
    if not isinstance(expression, dict) or len(expression) != 1:
        raise ValueError("nested expression must contain one operator")
    return evaluate_trigger(expression, facts)


def _unknown_or(default: TruthValue, evaluations: list[TriggerEvaluation]) -> TriggerEvaluation:
    missing = tuple(dict.fromkeys(key for item in evaluations for key in item.missing_fact_keys))
    return TriggerEvaluation("unknown", missing) if missing else TriggerEvaluation(default, ())
