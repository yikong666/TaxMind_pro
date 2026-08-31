from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Severity = Literal["high", "medium", "low", "info"]
MissingFactPolicy = Literal["need_info", "not_hit", "manual_review"]

_OPERATORS = {
    "all",
    "any",
    "not",
    "eq",
    "ne",
    "in",
    "not_in",
    "gt",
    "gte",
    "lt",
    "lte",
    "between",
    "exists",
    "contains_any",
    "contains_all",
}


@dataclass(frozen=True, slots=True)
class RiskRuleDefinition:
    rule_version_id: str
    severity: Severity
    trigger_expression: dict[str, object]
    missing_fact_policy: MissingFactPolicy
    basis_chunk_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.rule_version_id.strip():
            raise ValueError("rule_version_id is required")
        if not self.basis_chunk_ids or not all(
            chunk_id.strip() for chunk_id in self.basis_chunk_ids
        ):
            raise ValueError("basis evidence is required")
        _validate_expression(self.trigger_expression)


def _validate_expression(expression: object) -> None:
    if not isinstance(expression, dict) or len(expression) != 1:
        raise ValueError("rule expression must contain one operator")
    operator, operand = next(iter(expression.items()))
    if operator not in _OPERATORS:
        raise ValueError("rule operator is not allowed")
    if operator in {"all", "any"}:
        if not isinstance(operand, list) or not operand:
            raise ValueError(f"{operator} requires one or more expressions")
        for item in operand:
            _validate_expression(item)
    elif operator == "not":
        _validate_expression(operand)
