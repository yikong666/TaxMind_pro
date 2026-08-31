from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

from taxmind.shared.domain.errors import DomainError

_RESTRICTED_PATTERNS = (
    re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    re.compile(r"(?<!\d)\d{17}[\dXx](?![\dA-Za-z])"),
    re.compile(r"(?<![0-9A-Za-z])[0-9A-Z]{18}(?![0-9A-Za-z])"),
)


@dataclass(frozen=True, slots=True)
class CaseRecord:
    id: str
    org_id: str
    case_no: str
    title: str
    status: str
    owner_user_id: str
    reviewer_user_id: str | None
    default_region_code: str
    current_profile_version: int
    version_no: int
    opened_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class SubjectProfileRecord:
    id: str
    org_id: str
    case_id: str
    profile_version: int
    legal_form_code: str
    vat_taxpayer_type: str
    small_low_profit_status: str
    industry_code: str
    region_code: str
    business_date: date
    business_action_codes: list[str]
    extra_attributes: dict[str, object]
    data_classification: str
    confirmation_status: str
    supersedes_profile_id: str | None


@dataclass(frozen=True, slots=True)
class CaseFactRecord:
    id: str
    org_id: str
    case_id: str
    profile_version: int
    fact_key: str
    value_type: str
    value: object
    unit: str | None
    source_type: str
    effective_date: date | None
    confirmation_status: str


@dataclass(frozen=True, slots=True)
class CaseDetail:
    case: CaseRecord
    profile: SubjectProfileRecord
    facts: list[CaseFactRecord]


def validate_synthetic_or_anonymized(classification: str) -> str:
    normalized = classification.strip().lower()
    if normalized not in {"synthetic", "anonymized"}:
        raise DomainError(
            code="VALIDATION_FAILED",
            message="事项数据仅允许标记为虚构或匿名化",
            details={"field": "data_classification"},
        )
    return normalized


def reject_restricted_identifiers(value: object) -> None:
    if isinstance(value, str):
        if any(pattern.search(value) for pattern in _RESTRICTED_PATTERNS):
            raise DomainError(
                code="SENSITIVE_DATA_NOT_ALLOWED",
                message="事项输入疑似包含受限个人或企业标识, 请使用虚构或匿名化摘要",
            )
    elif isinstance(value, dict):
        for item in value.values():
            reject_restricted_identifiers(item)
    elif isinstance(value, list):
        for item in value:
            reject_restricted_identifiers(item)
