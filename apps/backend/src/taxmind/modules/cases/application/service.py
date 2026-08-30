from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from typing import Protocol

from taxmind.modules.cases.domain import (
    CaseDetail,
    CaseFactRecord,
    CaseRecord,
    SubjectProfileRecord,
    reject_restricted_identifiers,
    validate_synthetic_or_anonymized,
)
from taxmind.modules.cases.infrastructure.repository import SqlAlchemyCasesRepository
from taxmind.modules.cases.infrastructure.uow import SqlAlchemyCasesUnitOfWork
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.ids import new_id
from taxmind.shared.domain.principal import Principal


class CasesUnitOfWorkFactory(Protocol):
    def __call__(self) -> SqlAlchemyCasesUnitOfWork: ...


@dataclass(frozen=True, slots=True)
class FactInput:
    fact_key: str
    value_type: str
    value: object
    unit: str | None
    effective_date: date | None


@dataclass(frozen=True, slots=True)
class SubjectProfileInput:
    legal_form_code: str
    vat_taxpayer_type: str
    small_low_profit_status: str
    industry_code: str
    region_code: str
    business_date: date
    business_action_codes: list[str]
    extra_attributes: dict[str, object]
    data_classification: str
    facts: list[FactInput]


@dataclass(frozen=True, slots=True)
class CreateCaseCommand:
    title: str
    default_region_code: str
    profile: SubjectProfileInput
    request_id: str


@dataclass(frozen=True, slots=True)
class CreateProfileCommand:
    case_id: str
    supersedes_profile_version: int
    profile: SubjectProfileInput
    request_id: str


class CasesService:
    def __init__(self, *, uow_factory: CasesUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def create_case(self, command: CreateCaseCommand, principal: Principal) -> CaseDetail:
        _require_cases_write(principal)
        _validate_profile(command.profile)
        title = _normalized_title(command.title)
        region_code = _region_code(command.default_region_code)
        if command.profile.region_code != region_code:
            raise DomainError(
                code="VALIDATION_FAILED",
                message="初始画像地区必须与事项默认地区一致",
                details={"field": "subject_profile.region_code"},
            )
        now = datetime.now(UTC)
        case_id = new_id()
        case = CaseRecord(
            id=case_id,
            org_id=principal.org_id,
            case_no=f"CASE-{now:%Y%m%d}-{case_id.split('-', maxsplit=1)[0]}",
            title=title,
            status="draft",
            owner_user_id=principal.user_id,
            reviewer_user_id=None,
            default_region_code=region_code,
            current_profile_version=1,
            version_no=1,
            opened_at=now,
            updated_at=now,
        )
        profile = _profile_record(
            command.profile,
            case_id=case.id,
            org_id=case.org_id,
            profile_version=1,
            supersedes_profile_id=None,
        )
        facts = _fact_records(command.profile.facts, case=case, profile_version=1)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            await repository.create_case(case, actor_id=principal.user_id)
            await repository.flush()
            await repository.create_profile(profile, actor_id=principal.user_id)
            await repository.flush()
            await repository.create_facts(facts, actor_id=principal.user_id, occurred_at=now)
            await repository.create_audit_log(
                org_id=principal.org_id,
                actor_user_id=principal.user_id,
                action_code="case.created",
                resource_id=case.id,
                request_id=command.request_id,
                occurred_at=now,
            )
            await uow.commit()
        return CaseDetail(case=case, profile=profile, facts=facts)

    async def list_cases(self, principal: Principal) -> list[CaseRecord]:
        _require_cases_read(principal)
        owner_user_id = principal.user_id if _only_own_cases(principal) else None
        async with self._uow_factory() as uow:
            return await _repository(uow).list_cases(principal.org_id, owner_user_id=owner_user_id)

    async def get_case(self, case_id: str, principal: Principal) -> CaseDetail:
        _require_cases_read(principal)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            case = await repository.get_case(case_id, principal.org_id)
            if case is None or not _can_access_case(case, principal):
                raise DomainError(code="RESOURCE_NOT_FOUND", message="事项不存在或无权访问")
            detail = await repository.detail(case)
            if detail is None:
                raise DomainError(
                    code="RESOURCE_CONFLICT", message="事项画像版本不完整, 请联系管理员"
                )
            return detail

    async def create_profile_version(
        self, command: CreateProfileCommand, principal: Principal
    ) -> CaseDetail:
        _require_cases_write(principal)
        _validate_profile(command.profile)
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            case = await repository.lock_case(command.case_id, principal.org_id)
            if case is None or not _can_modify_case(case, principal):
                raise DomainError(code="RESOURCE_NOT_FOUND", message="事项不存在或无权编辑")
            if case.current_profile_version != command.supersedes_profile_version:
                raise DomainError(
                    code="RESOURCE_VERSION_CONFLICT",
                    message="事项画像已更新, 请刷新后重试",
                )
            if command.profile.region_code != case.default_region_code:
                raise DomainError(
                    code="VALIDATION_FAILED",
                    message="画像地区必须与事项默认地区一致",
                    details={"field": "subject_profile.region_code"},
                )
            previous = await repository.get_profile(
                case.id, case.org_id, command.supersedes_profile_version
            )
            if previous is None:
                raise DomainError(code="RESOURCE_CONFLICT", message="上一画像版本不存在")
            new_version = previous.profile_version + 1
            profile = _profile_record(
                command.profile,
                case_id=case.id,
                org_id=case.org_id,
                profile_version=new_version,
                supersedes_profile_id=previous.id,
            )
            facts = _fact_records(command.profile.facts, case=case, profile_version=new_version)
            await repository.create_profile(profile, actor_id=principal.user_id)
            await repository.flush()
            await repository.create_facts(facts, actor_id=principal.user_id, occurred_at=now)
            await repository.set_current_profile(
                case.id,
                profile_version=new_version,
                actor_id=principal.user_id,
                updated_at=now,
            )
            await repository.create_audit_log(
                org_id=case.org_id,
                actor_user_id=principal.user_id,
                action_code="case.profile_version.created",
                resource_id=case.id,
                request_id=command.request_id,
                occurred_at=now,
            )
            await uow.commit()
            updated_case = replace(
                case,
                current_profile_version=new_version,
                version_no=case.version_no + 1,
                updated_at=now,
            )
            return CaseDetail(case=updated_case, profile=profile, facts=facts)


def _repository(uow: SqlAlchemyCasesUnitOfWork) -> SqlAlchemyCasesRepository:
    if uow.repository is None:
        raise RuntimeError("unit of work repository is unavailable")
    return uow.repository


def _require_cases_read(principal: Principal) -> None:
    if not principal.has_permission("cases:read"):
        raise DomainError(code="AUTH_FORBIDDEN", message="当前角色无事项查看权限")


def _require_cases_write(principal: Principal) -> None:
    if not principal.has_permission("cases:write"):
        raise DomainError(code="AUTH_FORBIDDEN", message="当前角色无事项编辑权限")


def _only_own_cases(principal: Principal) -> bool:
    return not principal.roles.intersection({"reviewer", "org_admin", "auditor"})


def _can_access_case(case: CaseRecord, principal: Principal) -> bool:
    return case.owner_user_id == principal.user_id or not _only_own_cases(principal)


def _can_modify_case(case: CaseRecord, principal: Principal) -> bool:
    return case.owner_user_id == principal.user_id or "org_admin" in principal.roles


def _normalized_title(value: str) -> str:
    title = value.strip()
    if not title:
        raise DomainError(code="VALIDATION_FAILED", message="事项标题不能为空")
    reject_restricted_identifiers(title)
    return title


def _region_code(value: str) -> str:
    region_code = value.strip()
    if len(region_code) != 6 or not region_code.isdigit():
        raise DomainError(
            code="VALIDATION_FAILED",
            message="地区必须使用六位 GB/T 2260 代码",
            details={"field": "default_region_code"},
        )
    return region_code


def _validate_profile(profile: SubjectProfileInput) -> None:
    validate_synthetic_or_anonymized(profile.data_classification)
    _region_code(profile.region_code)
    if profile.small_low_profit_status not in {"yes", "no", "unknown"}:
        raise DomainError(code="VALIDATION_FAILED", message="小型微利企业状态无效")
    if not profile.business_action_codes:
        raise DomainError(code="VALIDATION_FAILED", message="至少需要一个业务行为代码")
    reject_restricted_identifiers(profile.extra_attributes)
    seen_fact_keys: set[str] = set()
    for fact in profile.facts:
        if fact.fact_key in seen_fact_keys:
            raise DomainError(code="VALIDATION_FAILED", message="同一画像中事实键不能重复")
        seen_fact_keys.add(fact.fact_key)
        if fact.value_type not in {"text", "number", "boolean", "date", "object", "array"}:
            raise DomainError(code="VALIDATION_FAILED", message="事实值类型无效")
        reject_restricted_identifiers(fact.value)


def _profile_record(
    profile: SubjectProfileInput,
    *,
    case_id: str,
    org_id: str,
    profile_version: int,
    supersedes_profile_id: str | None,
) -> SubjectProfileRecord:
    return SubjectProfileRecord(
        id=new_id(),
        org_id=org_id,
        case_id=case_id,
        profile_version=profile_version,
        legal_form_code=profile.legal_form_code,
        vat_taxpayer_type=profile.vat_taxpayer_type,
        small_low_profit_status=profile.small_low_profit_status,
        industry_code=profile.industry_code,
        region_code=profile.region_code,
        business_date=profile.business_date,
        business_action_codes=profile.business_action_codes,
        extra_attributes=profile.extra_attributes,
        data_classification=validate_synthetic_or_anonymized(profile.data_classification),
        confirmation_status="confirmed",
        supersedes_profile_id=supersedes_profile_id,
    )


def _fact_records(
    facts: list[FactInput], *, case: CaseRecord, profile_version: int
) -> list[CaseFactRecord]:
    return [
        CaseFactRecord(
            id=new_id(),
            org_id=case.org_id,
            case_id=case.id,
            profile_version=profile_version,
            fact_key=fact.fact_key,
            value_type=fact.value_type,
            value=fact.value,
            unit=fact.unit,
            effective_date=fact.effective_date,
            confirmation_status="confirmed",
        )
        for fact in facts
    ]
