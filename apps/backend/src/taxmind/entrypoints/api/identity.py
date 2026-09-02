from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from taxmind.entrypoints.api.dependencies import current_principal, identity_service_from
from taxmind.modules.identity.application.service import BootstrapCommand, LoginCommand
from taxmind.modules.identity.domain import (
    AuthenticatedSession,
    MembershipRecord,
    MemberView,
    UserRecord,
)
from taxmind.shared.contracts.api import ResponseMeta
from taxmind.shared.domain.principal import Principal

router = APIRouter(tags=["identity"])


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)
    password: SecretStr = Field(min_length=12, max_length=128)
    org_id: str | None = Field(default=None, min_length=36, max_length=36)
    device_label: str | None = Field(default=None, max_length=120)


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: SecretStr = Field(min_length=32, max_length=512)


class LogoutRequest(RefreshRequest):
    pass


class DevelopmentBootstrapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_name: str = Field(min_length=2, max_length=200)
    admin_name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=3, max_length=254)
    password: SecretStr = Field(min_length=12, max_length=128)
    role_code: str = Field(
        default="org_admin",
        pattern="^(org_admin|consultant|reviewer|knowledge_admin|auditor)$",
    )


class MemberCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)
    role_code: str = Field(min_length=3, max_length=32)


class MemberUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role_code: str = Field(min_length=3, max_length=32)
    status: str = Field(pattern="^(active|disabled)$")
    version_no: int = Field(ge=1)


class UserData(BaseModel):
    id: str
    email: str | None
    display_name: str
    status: str


class MembershipData(BaseModel):
    id: str
    org_id: str
    user_id: str
    role_code: str
    status: str
    version_no: int


class SessionData(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"  # noqa: S105 - public OAuth response constant
    expires_in_seconds: int
    user: UserData
    membership: MembershipData


class SessionResponse(BaseModel):
    data: SessionData
    meta: ResponseMeta


class MeResponse(BaseModel):
    data: UserData
    membership: MembershipData
    meta: ResponseMeta


class MemberData(MembershipData):
    email: str | None
    display_name: str
    user_status: str


class MembersResponse(BaseModel):
    data: list[MemberData]
    meta: ResponseMeta


class MemberResponse(BaseModel):
    data: MembershipData
    meta: ResponseMeta


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(request_id=request.state.request_id)


def _user_data(user: UserRecord) -> UserData:
    return UserData(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        status=user.status,
    )


def _membership_data(membership: MembershipRecord) -> MembershipData:
    return MembershipData(
        id=membership.id,
        org_id=membership.org_id,
        user_id=membership.user_id,
        role_code=membership.role_code,
        status=membership.status,
        version_no=membership.version_no,
    )


def _member_data(member: MemberView) -> MemberData:
    return MemberData(
        **_membership_data(member.membership).model_dump(),
        email=member.email,
        display_name=member.display_name,
        user_status=member.user_status,
    )


def _session_data(session: AuthenticatedSession) -> SessionData:
    return SessionData(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in_seconds=session.expires_in_seconds,
        user=_user_data(session.user),
        membership=_membership_data(session.membership),
    )


@router.post("/auth/login", response_model=SessionResponse)
async def login(payload: LoginRequest, request: Request) -> SessionResponse:
    session = await identity_service_from(request).login(
        LoginCommand(
            email=str(payload.email),
            password=payload.password.get_secret_value(),
            org_id=payload.org_id,
            device_label=payload.device_label,
            request_id=request.state.request_id,
        )
    )
    return SessionResponse(data=_session_data(session), meta=_meta(request))


@router.post("/auth/refresh", response_model=SessionResponse)
async def refresh(payload: RefreshRequest, request: Request) -> SessionResponse:
    session = await identity_service_from(request).refresh(
        payload.refresh_token.get_secret_value(), request_id=request.state.request_id
    )
    return SessionResponse(data=_session_data(session), meta=_meta(request))


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: LogoutRequest, request: Request) -> None:
    await identity_service_from(request).logout(
        payload.refresh_token.get_secret_value(), request_id=request.state.request_id
    )


@router.post("/auth/development-bootstrap", response_model=SessionResponse)
async def development_bootstrap(
    payload: DevelopmentBootstrapRequest, request: Request
) -> SessionResponse:
    session = await identity_service_from(request).bootstrap_development_admin(
        BootstrapCommand(
            org_name=payload.org_name,
            admin_name=payload.admin_name,
            email=str(payload.email),
            password=payload.password.get_secret_value(),
            role_code=payload.role_code,
            request_id=request.state.request_id,
        )
    )
    return SessionResponse(data=_session_data(session), meta=_meta(request))


@router.get("/me", response_model=MeResponse)
async def me(
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> MeResponse:
    user, membership = await identity_service_from(request).me(principal)
    return MeResponse(
        data=_user_data(user),
        membership=_membership_data(membership),
        meta=_meta(request),
    )


@router.get("/organizations/{org_id}/members", response_model=MembersResponse)
async def list_members(
    org_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> MembersResponse:
    members = await identity_service_from(request).list_members(principal, org_id)
    return MembersResponse(data=[_member_data(member) for member in members], meta=_meta(request))


@router.post("/organizations/{org_id}/members", response_model=MemberResponse)
async def add_member(
    org_id: str,
    payload: MemberCreateRequest,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> MemberResponse:
    membership = await identity_service_from(request).add_member(
        principal,
        org_id=org_id,
        email=str(payload.email),
        role_code=payload.role_code,
        request_id=request.state.request_id,
    )
    return MemberResponse(data=_membership_data(membership), meta=_meta(request))


@router.patch("/organizations/{org_id}/members/{member_id}", response_model=MemberResponse)
async def update_member(
    org_id: str,
    member_id: str,
    payload: MemberUpdateRequest,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> MemberResponse:
    membership = await identity_service_from(request).update_member(
        principal,
        org_id=org_id,
        member_id=member_id,
        role_code=payload.role_code,
        status=payload.status,
        version_no=payload.version_no,
        request_id=request.state.request_id,
    )
    return MemberResponse(data=_membership_data(membership), meta=_meta(request))
