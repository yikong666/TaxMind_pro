from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from taxmind.modules.audit.infrastructure.models import AuditLogModel
from taxmind.modules.identity.domain import (
    AuthSessionRecord,
    MembershipRecord,
    MemberView,
    OrganizationRecord,
    UserRecord,
)
from taxmind.modules.identity.infrastructure.models import (
    AuthSessionModel,
    OrganizationMemberModel,
    OrganizationModel,
    UserModel,
)


def _user_record(model: UserModel) -> UserRecord:
    return UserRecord(
        id=model.id,
        email=model.email,
        display_name=model.display_name,
        password_hash=model.password_hash,
        status=model.status,
        last_login_at=model.last_login_at,
    )


def _membership_record(model: OrganizationMemberModel) -> MembershipRecord:
    return MembershipRecord(
        id=model.id,
        org_id=model.org_id,
        user_id=model.user_id,
        role_code=model.role_code,
        status=model.status,
        joined_at=model.joined_at,
        version_no=model.version_no,
    )


def _utc(value: datetime) -> datetime:
    """MySQL DATETIME values are timezone-naive; application time remains UTC."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class SqlAlchemyIdentityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_users(self) -> int:
        return int((await self._session.scalar(select(func.count()).select_from(UserModel))) or 0)

    async def flush(self) -> None:
        """Persist parent rows before a child row that has no ORM relationship mapping."""
        await self._session.flush()

    async def get_user_by_email(self, email: str) -> UserRecord | None:
        model = await self._session.scalar(select(UserModel).where(UserModel.email == email))
        return _user_record(model) if model else None

    async def get_user_by_id(self, user_id: str) -> UserRecord | None:
        model = await self._session.get(UserModel, user_id)
        return _user_record(model) if model else None

    async def create_organization(self, org: OrganizationRecord) -> None:
        self._session.add(
            OrganizationModel(
                id=org.id,
                code=org.code,
                name=org.name,
                status=org.status,
                settings_json={},
            )
        )

    async def create_user(self, user: UserRecord) -> None:
        self._session.add(
            UserModel(
                id=user.id,
                email=user.email,
                display_name=user.display_name,
                password_hash=user.password_hash,
                status=user.status,
                last_login_at=user.last_login_at,
            )
        )

    async def update_last_login(self, user_id: str, occurred_at: datetime) -> None:
        await self._session.execute(
            update(UserModel).where(UserModel.id == user_id).values(last_login_at=occurred_at)
        )

    async def memberships_for_user(self, user_id: str) -> list[MembershipRecord]:
        rows = await self._session.scalars(
            select(OrganizationMemberModel).where(OrganizationMemberModel.user_id == user_id)
        )
        return [_membership_record(row) for row in rows]

    async def get_membership(self, org_id: str, user_id: str) -> MembershipRecord | None:
        model = await self._session.scalar(
            select(OrganizationMemberModel).where(
                OrganizationMemberModel.org_id == org_id,
                OrganizationMemberModel.user_id == user_id,
            )
        )
        return _membership_record(model) if model else None

    async def get_membership_by_id(self, org_id: str, member_id: str) -> MembershipRecord | None:
        model = await self._session.scalar(
            select(OrganizationMemberModel).where(
                OrganizationMemberModel.org_id == org_id,
                OrganizationMemberModel.id == member_id,
            )
        )
        return _membership_record(model) if model else None

    async def create_membership(self, membership: MembershipRecord) -> None:
        self._session.add(
            OrganizationMemberModel(
                id=membership.id,
                org_id=membership.org_id,
                user_id=membership.user_id,
                role_code=membership.role_code,
                status=membership.status,
                joined_at=membership.joined_at,
                version_no=membership.version_no,
            )
        )

    async def list_members(self, org_id: str) -> list[MemberView]:
        rows = await self._session.execute(
            select(OrganizationMemberModel, UserModel)
            .join(UserModel, UserModel.id == OrganizationMemberModel.user_id)
            .where(OrganizationMemberModel.org_id == org_id)
            .order_by(UserModel.display_name, OrganizationMemberModel.id)
        )
        return [
            MemberView(
                membership=_membership_record(membership),
                email=user.email,
                display_name=user.display_name,
                user_status=user.status,
            )
            for membership, user in rows
        ]

    async def count_active_admins(self, org_id: str) -> int:
        statement = (
            select(func.count())
            .select_from(OrganizationMemberModel)
            .where(
                OrganizationMemberModel.org_id == org_id,
                OrganizationMemberModel.role_code == "org_admin",
                OrganizationMemberModel.status == "active",
            )
        )
        return int((await self._session.scalar(statement)) or 0)

    async def update_membership(
        self,
        member_id: str,
        *,
        role_code: str,
        status: str,
        expected_version: int,
    ) -> bool:
        result = await self._session.execute(
            update(OrganizationMemberModel)
            .where(
                OrganizationMemberModel.id == member_id,
                OrganizationMemberModel.version_no == expected_version,
            )
            .values(role_code=role_code, status=status, version_no=expected_version + 1)
        )
        return isinstance(result, CursorResult) and result.rowcount == 1

    async def create_session(self, record: AuthSessionRecord, device_label: str | None) -> None:
        self._session.add(
            AuthSessionModel(
                id=record.id,
                user_id=record.user_id,
                org_id=record.org_id,
                refresh_token_hash=record.refresh_token_hash,
                device_label=device_label,
                expires_at=record.expires_at,
                revoked_at=record.revoked_at,
                last_seen_at=record.last_seen_at,
                created_at=record.last_seen_at,
            )
        )

    async def get_session_by_refresh_hash(self, refresh_hash: str) -> AuthSessionRecord | None:
        model = await self._session.scalar(
            select(AuthSessionModel).where(AuthSessionModel.refresh_token_hash == refresh_hash)
        )
        if model is None:
            return None
        return AuthSessionRecord(
            id=model.id,
            user_id=model.user_id,
            org_id=model.org_id,
            refresh_token_hash=model.refresh_token_hash,
            expires_at=_utc(model.expires_at),
            revoked_at=_utc(model.revoked_at) if model.revoked_at is not None else None,
            last_seen_at=_utc(model.last_seen_at),
        )

    async def revoke_session(self, session_id: str, revoked_at: datetime) -> None:
        await self._session.execute(
            update(AuthSessionModel)
            .where(AuthSessionModel.id == session_id, AuthSessionModel.revoked_at.is_(None))
            .values(revoked_at=revoked_at)
        )

    async def session_is_active(self, session_id: str, now: datetime) -> bool:
        session = await self._session.scalar(
            select(AuthSessionModel).where(
                AuthSessionModel.id == session_id,
                AuthSessionModel.revoked_at.is_(None),
            )
        )
        return session is not None and _utc(session.expires_at) > now

    async def create_audit_log(
        self,
        *,
        org_id: str | None,
        actor_user_id: str | None,
        action_code: str,
        resource_type: str,
        resource_id: str | None,
        request_id: str,
        occurred_at: datetime,
    ) -> None:
        self._session.add(
            AuditLogModel(
                org_id=org_id,
                actor_user_id=actor_user_id,
                action_code=action_code,
                resource_type=resource_type,
                resource_id=resource_id,
                request_id=request_id,
                result="success",
                occurred_at=occurred_at,
            )
        )
