from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from taxmind.shared.domain.errors import DomainError


class RoleCode(StrEnum):
    ORG_ADMIN = "org_admin"
    CONSULTANT = "consultant"
    REVIEWER = "reviewer"
    KNOWLEDGE_ADMIN = "knowledge_admin"
    AUDITOR = "auditor"


_ROLE_PERMISSIONS: dict[RoleCode, frozenset[str]] = {
    RoleCode.ORG_ADMIN: frozenset(
        {
            "members:read",
            "members:write",
            "org:manage",
            "cases:read",
            "cases:write",
            "feedback:write",
            "feedback:manage",
        }
    ),
    RoleCode.CONSULTANT: frozenset({"cases:read", "cases:write", "feedback:write"}),
    RoleCode.REVIEWER: frozenset({"cases:read", "cases:write", "cases:review", "feedback:write"}),
    RoleCode.KNOWLEDGE_ADMIN: frozenset(
        {
            "knowledge:read",
            "knowledge:write",
            "knowledge:review",
            "feedback:write",
            "feedback:manage",
        }
    ),
    RoleCode.AUDITOR: frozenset({"audit:read", "cases:read", "feedback:write"}),
}


def require_role_code(value: str) -> RoleCode:
    try:
        return RoleCode(value)
    except ValueError as exc:
        raise DomainError(
            code="VALIDATION_FAILED",
            message="角色编码无效",
            details={"field": "role_code"},
        ) from exc


def permissions_for_role(role_code: str) -> frozenset[str]:
    return _ROLE_PERMISSIONS[require_role_code(role_code)]


@dataclass(frozen=True, slots=True)
class UserRecord:
    id: str
    email: str | None
    display_name: str
    password_hash: str
    status: str
    last_login_at: datetime | None


@dataclass(frozen=True, slots=True)
class OrganizationRecord:
    id: str
    code: str
    name: str
    status: str


@dataclass(frozen=True, slots=True)
class MembershipRecord:
    id: str
    org_id: str
    user_id: str
    role_code: str
    status: str
    joined_at: datetime | None
    version_no: int


@dataclass(frozen=True, slots=True)
class MemberView:
    membership: MembershipRecord
    email: str | None
    display_name: str
    user_status: str


@dataclass(frozen=True, slots=True)
class AuthSessionRecord:
    id: str
    user_id: str
    org_id: str
    refresh_token_hash: str
    expires_at: datetime
    revoked_at: datetime | None
    last_seen_at: datetime


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    session_id: str
    access_token: str
    refresh_token: str
    expires_in_seconds: int
    user: UserRecord
    membership: MembershipRecord
