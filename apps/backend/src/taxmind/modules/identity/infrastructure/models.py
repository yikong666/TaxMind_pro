from datetime import datetime

from sqlalchemy import CHAR, JSON, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from taxmind.infrastructure.mysql.base import Base
from taxmind.shared.domain.ids import new_id


class OrganizationModel(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    settings_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (Index("ix_organizations_status", "status"),)


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    email: Mapped[str | None] = mapped_column(String(254), unique=True)
    mobile_hash: Mapped[str | None] = mapped_column(CHAR(64), index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="invited", index=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OrganizationMemberModel(Base):
    __tablename__ = "organization_members"
    __table_args__ = (
        UniqueConstraint("org_id", "user_id", name="uq_organization_members_org_user"),
        Index("ix_organization_members_scope", "org_id", "role_code", "status"),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("organizations.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"), nullable=False)
    role_code: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="invited")
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
