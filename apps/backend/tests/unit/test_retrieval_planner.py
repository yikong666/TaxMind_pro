from __future__ import annotations

from datetime import date

from taxmind.modules.retrieval.application.planner import QueryFacts, build_retrieval_plan


def test_version_question_routes_to_exact_and_controlled_lineage_graph() -> None:
    plan = build_retrieval_plan(
        query="DOC-2026-1 current replacement status",
        facts=QueryFacts(region_code="440300", business_date=date(2026, 8, 31)),
    )

    assert plan.route_code == "policy_version"
    assert plan.use_mysql_exact is True
    assert plan.use_milvus_semantic is True
    assert plan.graph_expansion_type == "policy_lineage"
    assert plan.missing_facts == []


def test_applicability_question_with_missing_scope_facts_stops_for_followup() -> None:
    plan = build_retrieval_plan(query="is this tax benefit applicable", facts=QueryFacts())

    assert plan.route_code == "policy_applicability"
    assert plan.should_interrupt is True
    assert plan.missing_facts == ["business_date", "region_code"]
    assert plan.use_mysql_exact is False
