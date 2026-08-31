from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Literal

RouteCode = Literal[
    "policy_query",
    "policy_applicability",
    "policy_version",
    "out_of_scope",
]
GraphExpansionType = Literal["policy_lineage", "policy_conditions"]


@dataclass(frozen=True, slots=True)
class QueryFacts:
    region_code: str | None = None
    business_date: date | None = None
    taxpayer_type: str | None = None


@dataclass(frozen=True, slots=True)
class RetrievalPlan:
    route_code: RouteCode
    use_mysql_exact: bool
    use_milvus_semantic: bool
    graph_expansion_type: GraphExpansionType | None
    should_interrupt: bool
    missing_facts: list[str]


def build_retrieval_plan(*, query: str, facts: QueryFacts) -> RetrievalPlan:
    normalized = query.casefold().strip()
    if _is_out_of_scope(normalized):
        return RetrievalPlan("out_of_scope", False, False, None, True, [])
    if _is_version_question(normalized):
        return RetrievalPlan(
            "policy_version",
            use_mysql_exact=True,
            use_milvus_semantic=True,
            graph_expansion_type="policy_lineage",
            should_interrupt=False,
            missing_facts=[],
        )
    if _is_applicability_question(normalized):
        missing = _scope_missing(facts)
        return RetrievalPlan(
            "policy_applicability",
            use_mysql_exact=False,
            use_milvus_semantic=not missing,
            graph_expansion_type="policy_conditions" if not missing else None,
            should_interrupt=bool(missing),
            missing_facts=missing,
        )
    return RetrievalPlan(
        "policy_query",
        use_mysql_exact=bool(_DOCUMENT_NO.search(normalized)),
        use_milvus_semantic=True,
        graph_expansion_type=None,
        should_interrupt=False,
        missing_facts=[],
    )


_DOCUMENT_NO = re.compile(r"\b[a-z]{2,10}-\d{4}-\d+\b")


def _is_version_question(query: str) -> bool:
    return bool(_DOCUMENT_NO.search(query)) and any(
        keyword in query for keyword in ("current", "replacement", "repeal", "现行", "替代", "废止")
    )


def _is_applicability_question(query: str) -> bool:
    return any(keyword in query for keyword in ("applicable", "eligibility", "适用", "优惠"))


def _is_out_of_scope(query: str) -> bool:
    return any(keyword in query for keyword in ("file tax return", "pay tax", "自动申报", "缴税"))


def _scope_missing(facts: QueryFacts) -> list[str]:
    missing: list[str] = []
    if facts.business_date is None:
        missing.append("business_date")
    if not facts.region_code or not facts.region_code.strip():
        missing.append("region_code")
    return missing
