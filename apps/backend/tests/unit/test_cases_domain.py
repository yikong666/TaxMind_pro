from __future__ import annotations

from datetime import UTC, datetime

import pytest

from taxmind.modules.cases.application.service import (
    FactInput,
    build_confirmed_fact_snapshot,
    validate_fact_decisions,
)
from taxmind.modules.cases.domain import (
    CaseFactRecord,
    CaseRecord,
    reject_restricted_identifiers,
    validate_synthetic_or_anonymized,
)
from taxmind.shared.domain.errors import DomainError


def test_cases_only_accept_synthetic_or_anonymized_data() -> None:
    assert validate_synthetic_or_anonymized("SYNTHETIC") == "synthetic"
    assert validate_synthetic_or_anonymized("anonymized") == "anonymized"

    with pytest.raises(DomainError) as error:
        validate_synthetic_or_anonymized("real_customer")

    assert error.value.code == "VALIDATION_FAILED"


def test_cases_reject_common_restricted_identifiers_recursively() -> None:
    with pytest.raises(DomainError) as error:
        reject_restricted_identifiers({"customer": ["联系电话13800138000"]})

    assert error.value.code == "SENSITIVE_DATA_NOT_ALLOWED"


def test_fact_decisions_require_each_proposal_to_have_one_decision() -> None:
    proposals = [
        FactInput(
            fact_key="invoice_intent",
            value_type="text",
            value="虚构开票咨询",
            unit=None,
            effective_date=None,
        )
    ]

    decisions = validate_fact_decisions(
        proposals,
        confirmed_fact_keys=["invoice_intent"],
        rejected_fact_keys=[],
    )

    assert decisions == {"invoice_intent": "confirmed"}

    with pytest.raises(DomainError) as error:
        validate_fact_decisions(
            proposals,
            confirmed_fact_keys=[],
            rejected_fact_keys=[],
        )

    assert error.value.code == "VALIDATION_FAILED"


def test_fact_decisions_reject_conflicting_decisions() -> None:
    proposals = [
        FactInput(
            fact_key="invoice_intent",
            value_type="text",
            value="虚构开票咨询",
            unit=None,
            effective_date=None,
        )
    ]

    with pytest.raises(DomainError) as error:
        validate_fact_decisions(
            proposals,
            confirmed_fact_keys=["invoice_intent"],
            rejected_fact_keys=["invoice_intent"],
        )

    assert error.value.code == "VALIDATION_FAILED"


def test_confirmed_fact_snapshot_creates_new_version_and_keeps_rejection() -> None:
    now = datetime.now(UTC)
    case = CaseRecord(
        id="case-001",
        org_id="org-001",
        case_no="CASE-001",
        title="虚构事项",
        status="draft",
        owner_user_id="user-001",
        reviewer_user_id=None,
        default_region_code="440300",
        current_profile_version=1,
        version_no=1,
        opened_at=now,
        updated_at=now,
    )
    previous_facts = [
        CaseFactRecord(
            id="fact-001",
            org_id="org-001",
            case_id="case-001",
            profile_version=1,
            fact_key="invoice_intent",
            value_type="text",
            value="虚构开票咨询",
            unit=None,
            source_type="user_input",
            effective_date=None,
            confirmation_status="confirmed",
        )
    ]
    proposal = FactInput(
        fact_key="service_scope",
        value_type="text",
        value="虚构服务范围候选",
        unit=None,
        effective_date=None,
    )

    snapshot = build_confirmed_fact_snapshot(
        case=case,
        previous_facts=previous_facts,
        fact_proposals=[proposal],
        decisions={"service_scope": "rejected"},
        profile_version=2,
        reviewer_decision=True,
    )

    assert {fact.profile_version for fact in snapshot} == {2}
    assert [fact.fact_key for fact in snapshot if fact.confirmation_status == "confirmed"] == [
        "invoice_intent"
    ]
    rejected = [fact for fact in snapshot if fact.confirmation_status == "rejected"]
    assert rejected[0].fact_key == "service_scope"
    assert rejected[0].source_type == "reviewer"
