from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class FactGateResult:
    should_interrupt: bool
    missing_fact_keys: tuple[str, ...]


def require_scope_facts(*, business_date: date | None, region_code: str | None) -> FactGateResult:
    missing: list[str] = []
    if business_date is None:
        missing.append("business_date")
    if not region_code or not region_code.strip():
        missing.append("region_code")
    return FactGateResult(bool(missing), tuple(missing))
