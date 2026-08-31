from __future__ import annotations

from datetime import date
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, JsonValue

from taxmind.entrypoints.api.dependencies import current_principal
from taxmind.modules.cases.application.service import (
    CasesService,
    ConfirmFactsCommand,
    CreateCaseCommand,
    CreateProfileCommand,
    FactInput,
    SubjectProfileInput,
)
from taxmind.modules.cases.domain import (
    CaseDetail,
    CaseFactRecord,
    CaseRecord,
    SubjectProfileRecord,
)
from taxmind.shared.contracts.api import ResponseMeta
from taxmind.shared.domain.principal import Principal

router = APIRouter(tags=["cases"])


class FactPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_key: str = Field(min_length=1, max_length=100)
    value_type: str = Field(pattern="^(text|number|boolean|date|object|array)$")
    value: JsonValue
    unit: str | None = Field(default=None, max_length=32)
    effective_date: date | None = None


class SubjectProfilePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    legal_form_code: str = Field(min_length=1, max_length=64)
    vat_taxpayer_type: str = Field(min_length=1, max_length=64)
    small_low_profit_status: str = Field(pattern="^(yes|no|unknown)$")
    industry_code: str = Field(min_length=1, max_length=64)
    region_code: str = Field(pattern="^\\d{6}$")
    business_date: date
    business_action_codes: list[str] = Field(min_length=1, max_length=20)
    extra_attributes: dict[str, JsonValue] = Field(default_factory=dict)
    data_classification: str = Field(pattern="^(synthetic|anonymized)$")
    facts: list[FactPayload] = Field(default_factory=list, max_length=50)


class CreateCaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=2, max_length=200)
    default_region_code: str = Field(pattern="^\\d{6}$")
    subject_profile: SubjectProfilePayload


class CreateProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supersedes_profile_version: int = Field(ge=1)
    subject_profile: SubjectProfilePayload


class ConfirmFactsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_version: int = Field(ge=1)
    fact_proposals: list[FactPayload] = Field(min_length=1, max_length=50)
    confirmed_fact_keys: list[str] = Field(default_factory=list, max_length=50)
    rejected_fact_keys: list[str] = Field(default_factory=list, max_length=50)


class CaseData(BaseModel):
    id: str
    case_no: str
    title: str
    status: str
    owner_user_id: str
    default_region_code: str
    current_profile_version: int
    version_no: int


class SubjectProfileData(BaseModel):
    id: str
    profile_version: int
    legal_form_code: str
    vat_taxpayer_type: str
    small_low_profit_status: str
    industry_code: str
    region_code: str
    business_date: date
    business_action_codes: list[str]
    extra_attributes: dict[str, JsonValue]
    data_classification: str
    confirmation_status: str
    supersedes_profile_id: str | None


class FactData(BaseModel):
    id: str
    profile_version: int
    fact_key: str
    value_type: str
    value: JsonValue
    unit: str | None
    source_type: str
    effective_date: date | None
    confirmation_status: str


class CaseDetailData(BaseModel):
    case: CaseData
    profile: SubjectProfileData
    facts: list[FactData]


class CaseDetailResponse(BaseModel):
    data: CaseDetailData
    meta: ResponseMeta


class CasesResponse(BaseModel):
    data: list[CaseData]
    meta: ResponseMeta


def _service(request: Request) -> CasesService:
    services = cast(dict[str, object], request.app.state.services)
    service = services.get("cases")
    if not isinstance(service, CasesService):
        raise RuntimeError("cases service is not configured")
    return service


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(request_id=request.state.request_id)


def _profile_input(payload: SubjectProfilePayload) -> SubjectProfileInput:
    return SubjectProfileInput(
        legal_form_code=payload.legal_form_code,
        vat_taxpayer_type=payload.vat_taxpayer_type,
        small_low_profit_status=payload.small_low_profit_status,
        industry_code=payload.industry_code,
        region_code=payload.region_code,
        business_date=payload.business_date,
        business_action_codes=payload.business_action_codes,
        extra_attributes=dict(payload.extra_attributes),
        data_classification=payload.data_classification,
        facts=[
            FactInput(
                fact_key=fact.fact_key,
                value_type=fact.value_type,
                value=fact.value,
                unit=fact.unit,
                effective_date=fact.effective_date,
            )
            for fact in payload.facts
        ],
    )


def _case_data(case: CaseRecord) -> CaseData:
    return CaseData(
        id=case.id,
        case_no=case.case_no,
        title=case.title,
        status=case.status,
        owner_user_id=case.owner_user_id,
        default_region_code=case.default_region_code,
        current_profile_version=case.current_profile_version,
        version_no=case.version_no,
    )


def _profile_data(profile: SubjectProfileRecord) -> SubjectProfileData:
    return SubjectProfileData(
        id=profile.id,
        profile_version=profile.profile_version,
        legal_form_code=profile.legal_form_code,
        vat_taxpayer_type=profile.vat_taxpayer_type,
        small_low_profit_status=profile.small_low_profit_status,
        industry_code=profile.industry_code,
        region_code=profile.region_code,
        business_date=profile.business_date,
        business_action_codes=profile.business_action_codes,
        extra_attributes=profile.extra_attributes,
        data_classification=profile.data_classification,
        confirmation_status=profile.confirmation_status,
        supersedes_profile_id=profile.supersedes_profile_id,
    )


def _fact_data(fact: CaseFactRecord) -> FactData:
    return FactData(
        id=fact.id,
        profile_version=fact.profile_version,
        fact_key=fact.fact_key,
        value_type=fact.value_type,
        value=fact.value,
        unit=fact.unit,
        source_type=fact.source_type,
        effective_date=fact.effective_date,
        confirmation_status=fact.confirmation_status,
    )


def _detail_data(detail: CaseDetail) -> CaseDetailData:
    return CaseDetailData(
        case=_case_data(detail.case),
        profile=_profile_data(detail.profile),
        facts=[_fact_data(fact) for fact in detail.facts],
    )


@router.post("/cases", response_model=CaseDetailResponse)
async def create_case(
    payload: CreateCaseRequest,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> CaseDetailResponse:
    detail = await _service(request).create_case(
        CreateCaseCommand(
            title=payload.title,
            default_region_code=payload.default_region_code,
            profile=_profile_input(payload.subject_profile),
            request_id=request.state.request_id,
        ),
        principal,
    )
    return CaseDetailResponse(data=_detail_data(detail), meta=_meta(request))


@router.get("/cases", response_model=CasesResponse)
async def list_cases(
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> CasesResponse:
    cases = await _service(request).list_cases(principal)
    return CasesResponse(data=[_case_data(case) for case in cases], meta=_meta(request))


@router.get("/cases/{case_id}", response_model=CaseDetailResponse)
async def get_case(
    case_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> CaseDetailResponse:
    detail = await _service(request).get_case(case_id, principal)
    return CaseDetailResponse(data=_detail_data(detail), meta=_meta(request))


@router.post("/cases/{case_id}/profiles", response_model=CaseDetailResponse)
async def create_profile_version(
    case_id: str,
    payload: CreateProfileRequest,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> CaseDetailResponse:
    detail = await _service(request).create_profile_version(
        CreateProfileCommand(
            case_id=case_id,
            supersedes_profile_version=payload.supersedes_profile_version,
            profile=_profile_input(payload.subject_profile),
            request_id=request.state.request_id,
        ),
        principal,
    )
    return CaseDetailResponse(data=_detail_data(detail), meta=_meta(request))


@router.post("/cases/{case_id}/facts/confirm", response_model=CaseDetailResponse)
async def confirm_case_facts(
    case_id: str,
    payload: ConfirmFactsRequest,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> CaseDetailResponse:
    detail = await _service(request).confirm_facts(
        ConfirmFactsCommand(
            case_id=case_id,
            profile_version=payload.profile_version,
            fact_proposals=[
                FactInput(
                    fact_key=fact.fact_key,
                    value_type=fact.value_type,
                    value=fact.value,
                    unit=fact.unit,
                    effective_date=fact.effective_date,
                )
                for fact in payload.fact_proposals
            ],
            confirmed_fact_keys=payload.confirmed_fact_keys,
            rejected_fact_keys=payload.rejected_fact_keys,
            request_id=request.state.request_id,
        ),
        principal,
    )
    return CaseDetailResponse(data=_detail_data(detail), meta=_meta(request))
