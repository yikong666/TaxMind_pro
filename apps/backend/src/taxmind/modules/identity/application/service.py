from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from taxmind.bootstrap.settings import Settings
from taxmind.modules.identity.domain import (
    AuthenticatedSession,
    AuthSessionRecord,
    MembershipRecord,
    MemberView,
    OrganizationRecord,
    RoleCode,
    UserRecord,
    permissions_for_role,
    require_role_code,
)
from taxmind.modules.identity.infrastructure.repository import SqlAlchemyIdentityRepository
from taxmind.modules.identity.infrastructure.security import Argon2PasswordService, JwtTokenService
from taxmind.modules.identity.infrastructure.uow import SqlAlchemyIdentityUnitOfWork
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.ids import new_id
from taxmind.shared.domain.principal import Principal

logger = logging.getLogger("taxmind.identity")


class IdentityUnitOfWorkFactory(Protocol):
    def __call__(self) -> SqlAlchemyIdentityUnitOfWork: ...


@dataclass(frozen=True, slots=True)
class LoginCommand:
    email: str
    password: str
    org_id: str | None
    device_label: str | None
    request_id: str


@dataclass(frozen=True, slots=True)
class BootstrapCommand:
    org_name: str
    admin_name: str
    email: str
    password: str
    role_code: str
    request_id: str


class IdentityService:
    def __init__(
        self,
        *,
        settings: Settings,
        uow_factory: IdentityUnitOfWorkFactory,
        password_service: Argon2PasswordService,
        token_service: JwtTokenService,
    ) -> None:
        self._settings = settings
        self._uow_factory = uow_factory
        self._passwords = password_service
        self._tokens = token_service
        self._refresh_ttl = timedelta(days=settings.refresh_token_ttl_days)

    async def login(self, command: LoginCommand) -> AuthenticatedSession:
        now = datetime.now(UTC)
        email = _normalize_email(command.email)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            user = await repository.get_user_by_email(email)
            if (
                user is None
                or user.status != "active"
                or not self._passwords.verify(user.password_hash, command.password)
            ):
                raise DomainError(code="AUTH_INVALID_CREDENTIALS", message="邮箱或密码错误")
            membership = await self._select_membership(repository, user.id, command.org_id)
            _require_active_membership(membership)
            await repository.update_last_login(user.id, now)
            result = await self._create_authenticated_session(
                repository,
                user=user,
                membership=membership,
                device_label=command.device_label,
                now=now,
            )
            await repository.create_audit_log(
                org_id=membership.org_id,
                actor_user_id=user.id,
                action_code="auth.login",
                resource_type="auth_session",
                resource_id=result.session_id,
                request_id=command.request_id,
                occurred_at=now,
            )
            await uow.commit()
            return result

    async def refresh(self, refresh_token: str, *, request_id: str) -> AuthenticatedSession:
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            existing = await repository.get_session_by_refresh_hash(_token_hash(refresh_token))
            if existing is None or existing.revoked_at is not None or existing.expires_at <= now:
                raise DomainError(code="AUTH_REQUIRED", message="登录状态无效或已过期")
            user = await repository.get_user_by_id(existing.user_id)
            membership = await repository.get_membership(existing.org_id, existing.user_id)
            if user is None or user.status != "active" or membership is None:
                raise DomainError(code="AUTH_REQUIRED", message="登录状态无效或已过期")
            _require_active_membership(membership)
            await repository.revoke_session(existing.id, now)
            result = await self._create_authenticated_session(
                repository, user=user, membership=membership, device_label=None, now=now
            )
            await repository.create_audit_log(
                org_id=membership.org_id,
                actor_user_id=user.id,
                action_code="auth.refresh",
                resource_type="auth_session",
                resource_id=existing.id,
                request_id=request_id,
                occurred_at=now,
            )
            await uow.commit()
            return result

    async def logout(self, refresh_token: str, *, request_id: str) -> None:
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            session = await repository.get_session_by_refresh_hash(_token_hash(refresh_token))
            if session is not None and session.revoked_at is None:
                await repository.revoke_session(session.id, now)
                await repository.create_audit_log(
                    org_id=session.org_id,
                    actor_user_id=session.user_id,
                    action_code="auth.logout",
                    resource_type="auth_session",
                    resource_id=session.id,
                    request_id=request_id,
                    occurred_at=now,
                )
                await uow.commit()

    async def authenticate_access_token(self, raw_token: str) -> Principal:
        principal = self._tokens.verify(raw_token)
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            user = await repository.get_user_by_id(principal.user_id)
            membership = await repository.get_membership(principal.org_id, principal.user_id)
            reason = _access_rejection_reason(user, membership, principal)
            if reason is None and not await repository.session_is_active(principal.session_id, now):
                reason = "session_inactive_or_expired"
            if reason is not None:
                logger.warning(
                    f"access token rejected: {reason}",
                    extra={
                        "event": "auth.access_token.rejected",
                        "error_code": "AUTH_SESSION_REJECTED",
                    },
                )
                raise DomainError(code="AUTH_REQUIRED", message="登录状态无效或已过期")
        return principal

    async def me(self, principal: Principal) -> tuple[UserRecord, MembershipRecord]:
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            user = await repository.get_user_by_id(principal.user_id)
            membership = await repository.get_membership(principal.org_id, principal.user_id)
            if user is None or membership is None:
                raise DomainError(code="AUTH_REQUIRED", message="登录状态无效或已过期")
            return user, membership

    async def list_members(self, principal: Principal, org_id: str) -> list[MemberView]:
        self._require_org_permission(principal, org_id, "members:read")
        async with self._uow_factory() as uow:
            return await _repository(uow).list_members(org_id)

    async def add_member(
        self,
        principal: Principal,
        *,
        org_id: str,
        email: str,
        role_code: str,
        request_id: str,
    ) -> MembershipRecord:
        self._require_org_permission(principal, org_id, "members:write")
        role = require_role_code(role_code)
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            user = await repository.get_user_by_email(_normalize_email(email))
            if user is None or user.status != "active":
                raise DomainError(
                    code="RESOURCE_NOT_FOUND",
                    message="未找到可添加的已激活账号",
                )
            if await repository.get_membership(org_id, user.id) is not None:
                raise DomainError(code="RESOURCE_CONFLICT", message="该成员已在当前机构中")
            membership = MembershipRecord(
                id=new_id(),
                org_id=org_id,
                user_id=user.id,
                role_code=role.value,
                status="active",
                joined_at=now,
                version_no=1,
            )
            await repository.create_membership(membership)
            await repository.create_audit_log(
                org_id=org_id,
                actor_user_id=principal.user_id,
                action_code="organization_member.added",
                resource_type="organization_member",
                resource_id=membership.id,
                request_id=request_id,
                occurred_at=now,
            )
            await uow.commit()
            return membership

    async def update_member(
        self,
        principal: Principal,
        *,
        org_id: str,
        member_id: str,
        role_code: str,
        status: str,
        version_no: int,
        request_id: str,
    ) -> MembershipRecord:
        self._require_org_permission(principal, org_id, "members:write")
        role = require_role_code(role_code)
        if status not in {"active", "disabled"}:
            raise DomainError(code="VALIDATION_FAILED", message="成员状态无效")
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            member = await repository.get_membership_by_id(org_id, member_id)
            if member is None:
                raise DomainError(code="RESOURCE_NOT_FOUND", message="成员不存在")
            if member.version_no != version_no:
                raise DomainError(
                    code="RESOURCE_VERSION_CONFLICT", message="成员信息已被其他操作更新"
                )
            removes_last_admin = (
                member.role_code == RoleCode.ORG_ADMIN.value
                and member.status == "active"
                and (role is not RoleCode.ORG_ADMIN or status != "active")
            )
            if removes_last_admin and await repository.count_active_admins(org_id) <= 1:
                raise DomainError(
                    code="RESOURCE_CONFLICT", message="机构至少需要保留一名激活管理员"
                )
            updated = await repository.update_membership(
                member_id,
                role_code=role.value,
                status=status,
                expected_version=version_no,
            )
            if not updated:
                raise DomainError(
                    code="RESOURCE_VERSION_CONFLICT", message="成员信息已被其他操作更新"
                )
            await repository.create_audit_log(
                org_id=org_id,
                actor_user_id=principal.user_id,
                action_code="organization_member.updated",
                resource_type="organization_member",
                resource_id=member_id,
                request_id=request_id,
                occurred_at=now,
            )
            await uow.commit()
            return MembershipRecord(
                id=member.id,
                org_id=member.org_id,
                user_id=member.user_id,
                role_code=role.value,
                status=status,
                joined_at=member.joined_at,
                version_no=version_no + 1,
            )

    async def bootstrap_development_admin(self, command: BootstrapCommand) -> AuthenticatedSession:
        if self._settings.app_env != "development":
            raise DomainError(code="AUTH_FORBIDDEN", message="仅开发环境允许初始化管理员")
        role = require_role_code(command.role_code)
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            if await repository.count_users() > 0:
                raise DomainError(code="RESOURCE_CONFLICT", message="开发环境管理员已经初始化")
            user = UserRecord(
                id=new_id(),
                email=_normalize_email(command.email),
                display_name=command.admin_name.strip(),
                password_hash=self._passwords.hash(command.password),
                status="active",
                last_login_at=now,
            )
            org = OrganizationRecord(
                id=new_id(),
                code=f"dev-{new_id().split('-', maxsplit=1)[0]}",
                name=command.org_name.strip(),
                status="active",
            )
            membership = MembershipRecord(
                id=new_id(),
                org_id=org.id,
                user_id=user.id,
                role_code=role.value,
                status="active",
                joined_at=now,
                version_no=1,
            )
            await repository.create_organization(org)
            await repository.create_user(user)
            await repository.flush()
            await repository.create_membership(membership)
            await repository.flush()
            result = await self._create_authenticated_session(
                repository,
                user=user,
                membership=membership,
                device_label="development-bootstrap",
                now=now,
            )
            await repository.create_audit_log(
                org_id=org.id,
                actor_user_id=user.id,
                action_code="auth.development_bootstrap",
                resource_type="organization",
                resource_id=org.id,
                request_id=command.request_id,
                occurred_at=now,
            )
            await uow.commit()
            return result

    async def _select_membership(
        self, repository: SqlAlchemyIdentityRepository, user_id: str, org_id: str | None
    ) -> MembershipRecord:
        memberships = [
            member
            for member in await repository.memberships_for_user(user_id)
            if member.status == "active"
        ]
        if org_id is not None:
            for membership in memberships:
                if membership.org_id == org_id:
                    return membership
            raise DomainError(code="AUTH_INVALID_CREDENTIALS", message="邮箱或密码错误")
        if len(memberships) != 1:
            raise DomainError(
                code="AUTH_ORGANIZATION_REQUIRED",
                message="该账号需要指定所属机构后登录",
            )
        return memberships[0]

    async def _create_authenticated_session(
        self,
        repository: SqlAlchemyIdentityRepository,
        *,
        user: UserRecord,
        membership: MembershipRecord,
        device_label: str | None,
        now: datetime,
    ) -> AuthenticatedSession:
        refresh_token = secrets.token_urlsafe(48)
        session = AuthSessionRecord(
            id=new_id(),
            user_id=user.id,
            org_id=membership.org_id,
            refresh_token_hash=_token_hash(refresh_token),
            expires_at=now + self._refresh_ttl,
            revoked_at=None,
            last_seen_at=now,
        )
        await repository.create_session(session, device_label)
        principal = Principal(
            user_id=user.id,
            org_id=membership.org_id,
            session_id=session.id,
            roles=frozenset({membership.role_code}),
            permissions=permissions_for_role(membership.role_code),
        )
        return AuthenticatedSession(
            session_id=session.id,
            access_token=self._tokens.issue(principal, now=now),
            refresh_token=refresh_token,
            expires_in_seconds=self._tokens.expires_in_seconds,
            user=user,
            membership=membership,
        )

    @staticmethod
    def _require_org_permission(principal: Principal, org_id: str, permission: str) -> None:
        if principal.org_id != org_id:
            raise DomainError(code="TENANT_SCOPE_VIOLATION", message="不能访问其他机构的数据范围")
        if not principal.has_permission(permission):
            raise DomainError(code="AUTH_FORBIDDEN", message="当前角色无此操作权限")


def _repository(uow: SqlAlchemyIdentityUnitOfWork) -> SqlAlchemyIdentityRepository:
    if uow.repository is None:
        raise RuntimeError("unit of work repository is unavailable")
    return uow.repository


def _normalize_email(value: str) -> str:
    email = value.strip().casefold()
    if not email or "@" not in email:
        raise DomainError(
            code="VALIDATION_FAILED", message="邮箱格式无效", details={"field": "email"}
        )
    return email


def _require_active_membership(membership: MembershipRecord) -> None:
    if membership.status != "active":
        raise DomainError(code="AUTH_REQUIRED", message="当前机构成员资格未激活")


def _token_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _access_rejection_reason(
    user: UserRecord | None,
    membership: MembershipRecord | None,
    principal: Principal,
) -> str | None:
    if user is None:
        return "user_missing"
    if user.status != "active":
        return "user_inactive"
    if membership is None:
        return "membership_missing"
    if membership.status != "active":
        return "membership_inactive"
    if membership.role_code not in principal.roles:
        return "membership_role_changed"
    return None
