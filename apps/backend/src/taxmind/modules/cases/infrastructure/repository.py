from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from taxmind.modules.audit.infrastructure.models import AuditLogModel
from taxmind.modules.cases.domain import (
    CaseDetail,
    CaseFactRecord,
    CaseRecord,
    SubjectProfileRecord,
)
from taxmind.modules.cases.infrastructure.models import (
    CaseFactModel,
    CaseSubjectProfileModel,
    ConsultationCaseModel,
)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _case_record(model: ConsultationCaseModel) -> CaseRecord:
    return CaseRecord(
        id=model.id,
        org_id=model.org_id,
        case_no=model.case_no,
        title=model.title,
        status=model.status,
        owner_user_id=model.owner_user_id,
        reviewer_user_id=model.reviewer_user_id,
        default_region_code=model.default_region_code,
        current_profile_version=model.current_profile_version,
        version_no=model.version_no,
        opened_at=_as_utc(model.opened_at),
        updated_at=_as_utc(model.updated_at),
    )


def _profile_record(model: CaseSubjectProfileModel) -> SubjectProfileRecord:
    return SubjectProfileRecord(
        id=model.id,
        org_id=model.org_id,
        case_id=model.case_id,
        profile_version=model.profile_version,
        legal_form_code=model.legal_form_code,
        vat_taxpayer_type=model.vat_taxpayer_type,
        small_low_profit_status=model.small_low_profit_status,
        industry_code=model.industry_code,
        region_code=model.region_code,
        business_date=model.business_date,
        business_action_codes=list(model.business_action_codes_json),
        extra_attributes=dict(model.extra_attributes_json),
        data_classification=model.data_classification,
        confirmation_status=model.confirmation_status,
        supersedes_profile_id=model.supersedes_profile_id,
    )


def _fact_record(model: CaseFactModel) -> CaseFactRecord:
    return CaseFactRecord(
        id=model.id,
        org_id=model.org_id,
        case_id=model.case_id,
        profile_version=model.profile_version,
        fact_key=model.fact_key,
        value_type=model.value_type,
        value=model.value_json,
        unit=model.unit,
        source_type=model.source_type,
        effective_date=model.effective_date,
        confirmation_status=model.confirmation_status,
    )


class SqlAlchemyCasesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def flush(self) -> None:
        await self._session.flush()

    async def create_case(self, record: CaseRecord, *, actor_id: str) -> None:
        self._session.add(
            ConsultationCaseModel(
                id=record.id,
                org_id=record.org_id,
                case_no=record.case_no,
                title=record.title,
                status=record.status,
                owner_user_id=record.owner_user_id,
                reviewer_user_id=record.reviewer_user_id,
                default_region_code=record.default_region_code,
                current_profile_version=record.current_profile_version,
                opened_at=record.opened_at,
                version_no=record.version_no,
                created_at=record.opened_at,
                updated_at=record.updated_at,
                created_by=actor_id,
                updated_by=actor_id,
            )
        )

    async def create_profile(self, record: SubjectProfileRecord, *, actor_id: str) -> None:
        now = datetime.now(UTC)
        self._session.add(
            CaseSubjectProfileModel(
                id=record.id,
                org_id=record.org_id,
                case_id=record.case_id,
                profile_version=record.profile_version,
                legal_form_code=record.legal_form_code,
                vat_taxpayer_type=record.vat_taxpayer_type,
                small_low_profit_status=record.small_low_profit_status,
                industry_code=record.industry_code,
                region_code=record.region_code,
                business_date=record.business_date,
                business_action_codes_json=record.business_action_codes,
                extra_attributes_json=record.extra_attributes,
                data_classification=record.data_classification,
                confirmation_status=record.confirmation_status,
                confirmed_by=actor_id,
                confirmed_at=now,
                supersedes_profile_id=record.supersedes_profile_id,
                created_at=now,
                created_by=actor_id,
            )
        )

    async def create_facts(
        self, records: list[CaseFactRecord], *, actor_id: str, occurred_at: datetime
    ) -> None:
        self._session.add_all(
            [
                CaseFactModel(
                    id=record.id,
                    org_id=record.org_id,
                    case_id=record.case_id,
                    profile_version=record.profile_version,
                    fact_key=record.fact_key,
                    value_type=record.value_type,
                    value_json=record.value,
                    unit=record.unit,
                    source_type=record.source_type,
                    confirmation_status=record.confirmation_status,
                    effective_date=record.effective_date,
                    confirmed_by=actor_id,
                    confirmed_at=occurred_at,
                    created_at=occurred_at,
                )
                for record in records
            ]
        )

    async def get_case(self, case_id: str, org_id: str) -> CaseRecord | None:
        model = await self._session.scalar(
            select(ConsultationCaseModel).where(
                ConsultationCaseModel.id == case_id,
                ConsultationCaseModel.org_id == org_id,
            )
        )
        return _case_record(model) if model else None

    async def lock_case(self, case_id: str, org_id: str) -> CaseRecord | None:
        model = await self._session.scalar(
            select(ConsultationCaseModel)
            .where(
                ConsultationCaseModel.id == case_id,
                ConsultationCaseModel.org_id == org_id,
            )
            .with_for_update()
        )
        return _case_record(model) if model else None

    async def list_cases(self, org_id: str, *, owner_user_id: str | None) -> list[CaseRecord]:
        statement = select(ConsultationCaseModel).where(ConsultationCaseModel.org_id == org_id)
        if owner_user_id is not None:
            statement = statement.where(ConsultationCaseModel.owner_user_id == owner_user_id)
        models = await self._session.scalars(
            statement.order_by(
                ConsultationCaseModel.updated_at.desc(), ConsultationCaseModel.id.desc()
            )
        )
        return [_case_record(model) for model in models]

    async def get_profile(
        self, case_id: str, org_id: str, profile_version: int
    ) -> SubjectProfileRecord | None:
        model = await self._session.scalar(
            select(CaseSubjectProfileModel).where(
                CaseSubjectProfileModel.case_id == case_id,
                CaseSubjectProfileModel.org_id == org_id,
                CaseSubjectProfileModel.profile_version == profile_version,
            )
        )
        return _profile_record(model) if model else None

    async def list_facts(
        self, case_id: str, org_id: str, profile_version: int
    ) -> list[CaseFactRecord]:
        models = await self._session.scalars(
            select(CaseFactModel)
            .where(
                CaseFactModel.case_id == case_id,
                CaseFactModel.org_id == org_id,
                CaseFactModel.profile_version == profile_version,
            )
            .order_by(CaseFactModel.fact_key, CaseFactModel.id)
        )
        return [_fact_record(model) for model in models]

    async def set_current_profile(
        self, case_id: str, *, profile_version: int, actor_id: str, updated_at: datetime
    ) -> None:
        await self._session.execute(
            update(ConsultationCaseModel)
            .where(ConsultationCaseModel.id == case_id)
            .values(
                current_profile_version=profile_version,
                version_no=ConsultationCaseModel.version_no + 1,
                updated_by=actor_id,
                updated_at=updated_at,
            )
        )

    async def create_audit_log(
        self,
        *,
        org_id: str,
        actor_user_id: str,
        action_code: str,
        resource_id: str,
        request_id: str,
        occurred_at: datetime,
    ) -> None:
        self._session.add(
            AuditLogModel(
                org_id=org_id,
                actor_user_id=actor_user_id,
                action_code=action_code,
                resource_type="consultation_case",
                resource_id=resource_id,
                request_id=request_id,
                result="success",
                occurred_at=occurred_at,
            )
        )

    async def detail(self, case: CaseRecord) -> CaseDetail | None:
        profile = await self.get_profile(case.id, case.org_id, case.current_profile_version)
        if profile is None:
            return None
        facts = await self.list_facts(case.id, case.org_id, profile.profile_version)
        return CaseDetail(case=case, profile=profile, facts=facts)
