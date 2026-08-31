from __future__ import annotations

import os
from datetime import UTC, date, datetime
from typing import cast
from uuid import uuid4

import pytest
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from taxmind.bootstrap.settings import Settings
from taxmind.infrastructure.mysql.session import create_engine
from taxmind.modules.cases.application.service import (
    CasesService,
    CasesUnitOfWorkFactory,
    ConfirmFactsCommand,
    CreateCaseCommand,
    FactInput,
    SubjectProfileInput,
)
from taxmind.modules.cases.infrastructure.repository import SqlAlchemyCasesRepository
from taxmind.modules.conversations.application.service import (
    AppendUserMessageCommand,
    ConversationsService,
    ConversationsUnitOfWorkFactory,
    CreateConversationCommand,
)
from taxmind.modules.conversations.infrastructure.memory import RedisShortMemoryAdapter
from taxmind.modules.conversations.infrastructure.repository import (
    SqlAlchemyConversationsRepository,
)
from taxmind.modules.identity.application.service import (
    IdentityService,
    IdentityUnitOfWorkFactory,
    LoginCommand,
)
from taxmind.modules.identity.infrastructure.models import (
    OrganizationMemberModel,
    OrganizationModel,
    UserModel,
)
from taxmind.modules.identity.infrastructure.repository import SqlAlchemyIdentityRepository
from taxmind.modules.identity.infrastructure.security import (
    Argon2PasswordService,
    JwtTokenService,
)
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.ids import new_id
from taxmind.shared.domain.principal import Principal


class SharedIdentityUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.repository: SqlAlchemyIdentityRepository | None = None

    async def __aenter__(self) -> SharedIdentityUnitOfWork:
        self.repository = SqlAlchemyIdentityRepository(self._session)
        return self

    async def commit(self) -> None:
        await self._session.flush()

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


class SharedIdentityUnitOfWorkFactory:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def __call__(self) -> SharedIdentityUnitOfWork:
        return SharedIdentityUnitOfWork(self._session)


class SharedCasesUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.repository: SqlAlchemyCasesRepository | None = None

    async def __aenter__(self) -> SharedCasesUnitOfWork:
        self.repository = SqlAlchemyCasesRepository(self._session)
        return self

    async def commit(self) -> None:
        await self._session.flush()

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


class SharedCasesUnitOfWorkFactory:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def __call__(self) -> SharedCasesUnitOfWork:
        return SharedCasesUnitOfWork(self._session)


class SharedConversationsUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.repository: SqlAlchemyConversationsRepository | None = None

    async def __aenter__(self) -> SharedConversationsUnitOfWork:
        self.repository = SqlAlchemyConversationsRepository(self._session)
        return self

    async def commit(self) -> None:
        await self._session.flush()

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None


class SharedConversationsUnitOfWorkFactory:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def __call__(self) -> SharedConversationsUnitOfWork:
        return SharedConversationsUnitOfWork(self._session)


@pytest.mark.skipif(
    os.getenv("TAXMIND_RUN_INTEGRATION") != "1",
    reason="requires the local MySQL and Redis Compose services",
)
async def test_login_case_fact_conversation_flow_rolls_back_and_restores_memory() -> None:
    settings = Settings(app_env="test")
    engine = create_engine(settings)
    redis_client = Redis.from_url(settings.redis_url)
    memory = RedisShortMemoryAdapter(
        redis_client,
        ttl_seconds=settings.short_memory_ttl_seconds,
    )
    session = AsyncSession(engine, expire_on_commit=False)
    transaction = await session.begin()
    unique = uuid4().hex
    org_id = new_id()
    user_id = new_id()
    email = f"stage4-{unique}@example.invalid"
    password = "Synthetic-stage4-password-123!"  # noqa: S105
    memory_key: str | None = None

    try:
        passwords = Argon2PasswordService()
        now = datetime.now(UTC)
        session.add_all(
            [
                OrganizationModel(
                    id=org_id,
                    code=f"stage4-{unique}",
                    name="阶段四虚构验收机构",
                    status="active",
                    settings_json={},
                    version_no=1,
                ),
                UserModel(
                    id=user_id,
                    email=email,
                    display_name="阶段四虚构顾问",
                    password_hash=passwords.hash(password),
                    status="active",
                    last_login_at=None,
                ),
            ]
        )
        await session.flush()
        session.add(
            OrganizationMemberModel(
                id=new_id(),
                org_id=org_id,
                user_id=user_id,
                role_code="consultant",
                status="active",
                joined_at=now,
                version_no=1,
            )
        )
        await session.flush()

        identity = IdentityService(
            settings=settings,
            uow_factory=cast(
                IdentityUnitOfWorkFactory,
                SharedIdentityUnitOfWorkFactory(session),
            ),
            password_service=passwords,
            token_service=JwtTokenService(settings),
        )
        authenticated = await identity.login(
            LoginCommand(
                email=email,
                password=password,
                org_id=org_id,
                device_label="stage4-integration",
                request_id=new_id(),
            )
        )
        principal = await identity.authenticate_access_token(authenticated.access_token)

        cases = CasesService(
            uow_factory=cast(
                CasesUnitOfWorkFactory,
                SharedCasesUnitOfWorkFactory(session),
            )
        )
        initial_profile = SubjectProfileInput(
            legal_form_code="LIMITED_COMPANY",
            vat_taxpayer_type="SMALL_SCALE",
            small_low_profit_status="unknown",
            industry_code="GENERAL_TRADE",
            region_code="440300",
            business_date=date(2026, 8, 31),
            business_action_codes=["INVOICE_ISSUANCE"],
            extra_attributes={"scenario": "synthetic-stage4-acceptance"},
            data_classification="synthetic",
            facts=[
                FactInput(
                    fact_key="business_context",
                    value_type="text",
                    value="虚构企业咨询开票事项",
                    unit=None,
                    effective_date=date(2026, 8, 31),
                )
            ],
        )
        created_case = await cases.create_case(
            CreateCaseCommand(
                title="阶段四虚构链路验收事项",
                default_region_code="440300",
                profile=initial_profile,
                request_id=new_id(),
            ),
            principal,
        )
        confirmed_case = await cases.confirm_facts(
            ConfirmFactsCommand(
                case_id=created_case.case.id,
                profile_version=1,
                fact_proposals=[
                    FactInput(
                        fact_key="invoice_intent",
                        value_type="text",
                        value="虚构开票咨询",
                        unit=None,
                        effective_date=date(2026, 8, 31),
                    )
                ],
                confirmed_fact_keys=["invoice_intent"],
                rejected_fact_keys=[],
                request_id=new_id(),
            ),
            principal,
        )
        assert confirmed_case.profile.profile_version == 2

        conversations = ConversationsService(
            uow_factory=cast(
                ConversationsUnitOfWorkFactory,
                SharedConversationsUnitOfWorkFactory(session),
            ),
            cases_service=cases,
            short_memory=memory,
            recent_message_limit=settings.short_memory_recent_message_limit,
        )
        created_conversation = await conversations.create_conversation(
            CreateConversationCommand(
                case_id=created_case.case.id,
                title="阶段四虚构咨询会话",
                request_id=new_id(),
            ),
            principal,
        )
        conversation_id = created_conversation.conversation.id
        memory_key = memory.key(org_id, conversation_id)
        command = AppendUserMessageCommand(
            conversation_id=conversation_id,
            text="请基于已确认事实整理待核对信息。",
            idempotency_key=f"stage4-{unique}",
            request_id=new_id(),
        )
        first_message = await conversations.append_user_message(command, principal)
        repeated_message = await conversations.append_user_message(command, principal)
        assert first_message.message.sequence_no == 1
        assert repeated_message.message.id == first_message.message.id
        assert repeated_message.memory_sync_status == "already_recorded"

        await redis_client.delete(memory_key)
        restored = await conversations.get_context(conversation_id, principal)
        assert restored.memory_source == "mysql_restored"
        assert restored.state.profile_version == 2
        assert {fact.fact_key for fact in restored.state.confirmed_facts} == {
            "business_context",
            "invoice_intent",
        }
        assert [message.sequence_no for message in restored.state.recent_messages] == [1]

        other_org_principal = Principal(
            user_id=user_id,
            org_id=new_id(),
            session_id=authenticated.session_id,
            roles=frozenset({"consultant"}),
            permissions=principal.permissions,
        )
        with pytest.raises(DomainError) as captured:
            await conversations.get_context(conversation_id, other_org_principal)
        assert captured.value.code == "RESOURCE_NOT_FOUND"
    finally:
        if memory_key is not None:
            await redis_client.delete(memory_key)
        if transaction.is_active:
            await transaction.rollback()
        await session.close()
        await memory.close()

    async with AsyncSession(engine) as verification_session:
        remaining = await verification_session.scalar(
            select(func.count())
            .select_from(OrganizationModel)
            .where(OrganizationModel.id == org_id)
        )
        assert remaining == 0
    await engine.dispose()
