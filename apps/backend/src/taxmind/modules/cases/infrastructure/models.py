from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from taxmind.infrastructure.mysql.base import Base
from taxmind.shared.domain.ids import new_id


class ConsultationCaseModel(Base):
    __tablename__ = "consultation_cases"
    __table_args__ = (
        UniqueConstraint("org_id", "case_no", name="uq_consultation_cases_org_case_no"),
        Index("ix_consultation_cases_org_scope", "org_id", "status", "owner_user_id", "updated_at"),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("organizations.id"), nullable=False)
    case_no: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    owner_user_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("users.id"), nullable=False)
    reviewer_user_id: Mapped[str | None] = mapped_column(CHAR(36), ForeignKey("users.id"))
    default_region_code: Mapped[str] = mapped_column(String(6), nullable=False)
    current_profile_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current_draft_id: Mapped[str | None] = mapped_column(CHAR(36))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str | None] = mapped_column(CHAR(36))
    updated_by: Mapped[str | None] = mapped_column(CHAR(36))


class CaseSubjectProfileModel(Base):
    __tablename__ = "case_subject_profiles"
    __table_args__ = (
        UniqueConstraint("case_id", "profile_version", name="uq_case_profiles_case_version"),
        Index("ix_case_subject_profiles_org_case", "org_id", "case_id", "profile_version"),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("organizations.id"), nullable=False)
    case_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("consultation_cases.id"), nullable=False
    )
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False)
    legal_form_code: Mapped[str] = mapped_column(String(64), nullable=False)
    vat_taxpayer_type: Mapped[str] = mapped_column(String(64), nullable=False)
    small_low_profit_status: Mapped[str] = mapped_column(String(16), nullable=False)
    industry_code: Mapped[str] = mapped_column(String(64), nullable=False)
    region_code: Mapped[str] = mapped_column(String(6), nullable=False)
    business_date: Mapped[date] = mapped_column(Date, nullable=False)
    business_action_codes_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    extra_attributes_json: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    data_classification: Mapped[str] = mapped_column(String(32), nullable=False)
    confirmation_status: Mapped[str] = mapped_column(String(32), nullable=False)
    confirmed_by: Mapped[str | None] = mapped_column(CHAR(36))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    supersedes_profile_id: Mapped[str | None] = mapped_column(
        CHAR(36), ForeignKey("case_subject_profiles.id")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str | None] = mapped_column(CHAR(36))


class CaseFactModel(Base):
    __tablename__ = "case_facts"
    __table_args__ = (
        Index(
            "ix_case_facts_org_case_profile",
            "org_id",
            "case_id",
            "profile_version",
            "fact_key",
            "confirmation_status",
        ),
    )

    id: Mapped[str] = mapped_column(CHAR(36), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(CHAR(36), ForeignKey("organizations.id"), nullable=False)
    case_id: Mapped[str] = mapped_column(
        CHAR(36), ForeignKey("consultation_cases.id"), nullable=False
    )
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False)
    fact_key: Mapped[str] = mapped_column(String(100), nullable=False)
    value_type: Mapped[str] = mapped_column(String(32), nullable=False)
    value_json: Mapped[object] = mapped_column(JSON, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(32))
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_message_id: Mapped[str | None] = mapped_column(CHAR(36))
    confirmation_status: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    effective_date: Mapped[date | None] = mapped_column(Date)
    confirmed_by: Mapped[str | None] = mapped_column(CHAR(36))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
