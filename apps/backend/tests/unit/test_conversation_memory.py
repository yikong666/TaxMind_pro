from __future__ import annotations

from datetime import UTC, date, datetime
from typing import cast

import pytest
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from taxmind.modules.cases.application.service import CasesService
from taxmind.modules.cases.domain import (
    CaseDetail,
    CaseFactRecord,
    CaseRecord,
    SubjectProfileRecord,
)
from taxmind.modules.conversations.application.service import (
    AppendUserMessageCommand,
    ConversationsService,
    ConversationsUnitOfWorkFactory,
)
from taxmind.modules.conversations.domain import (
    ContextFact,
    ConversationRecord,
    MessageRecord,
    ShortMemoryState,
)
from taxmind.modules.conversations.infrastructure.memory import RedisShortMemoryAdapter
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.principal import Principal


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, bytes] = {}
        self.ttl: int | None = None
        self.fail_reads = False

    async def get(self, key: str) -> bytes | None:
        if self.fail_reads:
            raise RedisConnectionError("test cache unavailable")
        return self.values.get(key)

    async def set(self, key: str, value: bytes, *, ex: int) -> None:
        self.values[key] = value
        self.ttl = ex

    async def aclose(self) -> None:
        return None


class FakeCasesService:
    def __init__(self, detail: CaseDetail) -> None:
        self.detail = detail

    async def get_case(self, case_id: str, principal: Principal) -> CaseDetail:
        assert case_id == self.detail.case.id
        assert principal.org_id == self.detail.case.org_id
        return self.detail


class FakeConversationRepository:
    def __init__(self, conversation: ConversationRecord, messages: list[MessageRecord]) -> None:
        self.conversation = conversation
        self.messages = messages

    async def get_conversation(
        self, conversation_id: str, org_id: str
    ) -> ConversationRecord | None:
        if conversation_id == self.conversation.id and org_id == self.conversation.org_id:
            return self.conversation
        return None

    async def lock_conversation(
        self, conversation_id: str, org_id: str
    ) -> ConversationRecord | None:
        return await self.get_conversation(conversation_id, org_id)

    async def get_message_by_idempotency(
        self, conversation_id: str, org_id: str, idempotency_key: str
    ) -> MessageRecord | None:
        return next(
            (
                message
                for message in self.messages
                if message.conversation_id == conversation_id
                and message.org_id == org_id
                and message.idempotency_key == idempotency_key
            ),
            None,
        )

    async def next_sequence(self, conversation_id: str, org_id: str) -> int:
        scoped = [
            message.sequence_no
            for message in self.messages
            if message.conversation_id == conversation_id and message.org_id == org_id
        ]
        return max(scoped, default=0) + 1

    async def create_message(self, record: MessageRecord) -> None:
        self.messages.append(record)

    async def touch_conversation(self, conversation_id: str, occurred_at: datetime) -> None:
        assert conversation_id == self.conversation.id

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
        assert org_id == self.conversation.org_id
        assert actor_user_id == self.conversation.started_by
        assert action_code == "conversation.message.appended"
        assert resource_id == self.conversation.id
        assert request_id

    async def list_messages(
        self,
        conversation_id: str,
        org_id: str,
        *,
        before_sequence: int | None,
        limit: int,
    ) -> list[MessageRecord]:
        assert conversation_id == self.conversation.id
        assert org_id == self.conversation.org_id
        assert before_sequence is None
        return self.messages[-limit:]


class FakeConversationUnitOfWork:
    def __init__(self, repository: FakeConversationRepository) -> None:
        self.repository = repository

    async def __aenter__(self) -> FakeConversationUnitOfWork:
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    async def commit(self) -> None:
        return None


class FakeConversationUnitOfWorkFactory:
    def __init__(self, repository: FakeConversationRepository) -> None:
        self.repository = repository

    def __call__(self) -> FakeConversationUnitOfWork:
        return FakeConversationUnitOfWork(self.repository)


async def test_redis_short_memory_round_trip_uses_scoped_key_and_ttl() -> None:
    fake = FakeRedis()
    adapter = RedisShortMemoryAdapter(cast(Redis, fake), ttl_seconds=259200)
    now = datetime.now(UTC)
    state = ShortMemoryState(
        org_id="org-001",
        conversation_id="conversation-001",
        case_id="case-001",
        profile_version=2,
        confirmed_facts=[ContextFact("invoice_intent", "虚构开票咨询", "2026-08-31")],
        recent_messages=[
            MessageRecord(
                id="message-001",
                org_id="org-001",
                conversation_id="conversation-001",
                case_id="case-001",
                sequence_no=1,
                role="user",
                content_text="虚构咨询消息",
                content_json={},
                run_id=None,
                parent_message_id=None,
                visibility="user_visible",
                content_hash="a" * 64,
                redaction_status="not_needed",
                idempotency_key="message-001",
                created_at=now,
            )
        ],
    )

    await adapter.set(state)
    restored = await adapter.get("org-001", "conversation-001")

    assert fake.ttl == 259200
    assert list(fake.values) == ["tm:session:org-001:conversation-001"]
    assert restored == state


async def test_context_rebuilds_from_mysql_when_redis_state_is_missing() -> None:
    now = datetime.now(UTC)
    case = CaseRecord(
        id="case-001",
        org_id="org-001",
        case_no="CASE-001",
        title="虚构事项",
        status="draft",
        owner_user_id="user-001",
        reviewer_user_id=None,
        default_region_code="440300",
        current_profile_version=2,
        version_no=2,
        opened_at=now,
        updated_at=now,
    )
    detail = CaseDetail(
        case=case,
        profile=SubjectProfileRecord(
            id="profile-002",
            org_id="org-001",
            case_id="case-001",
            profile_version=2,
            legal_form_code="LIMITED_COMPANY",
            vat_taxpayer_type="SMALL_SCALE",
            small_low_profit_status="unknown",
            industry_code="GENERAL_TRADE",
            region_code="440300",
            business_date=date(2026, 8, 31),
            business_action_codes=["INVOICE_ISSUANCE"],
            extra_attributes={},
            data_classification="synthetic",
            confirmation_status="confirmed",
            supersedes_profile_id="profile-001",
        ),
        facts=[
            CaseFactRecord(
                id="fact-001",
                org_id="org-001",
                case_id="case-001",
                profile_version=2,
                fact_key="invoice_intent",
                value_type="text",
                value="虚构开票咨询",
                unit=None,
                source_type="user_input",
                effective_date=None,
                confirmation_status="confirmed",
            )
        ],
    )
    conversation = ConversationRecord(
        id="conversation-001",
        org_id="org-001",
        case_id="case-001",
        title="虚构咨询会话",
        status="active",
        started_by="user-001",
        last_message_at=None,
        summary_version=0,
        created_at=now,
        updated_at=now,
    )
    repository = FakeConversationRepository(conversation, [])
    fake_redis = FakeRedis()
    memory = RedisShortMemoryAdapter(cast(Redis, fake_redis), ttl_seconds=259200)
    service = ConversationsService(
        uow_factory=cast(
            ConversationsUnitOfWorkFactory,
            FakeConversationUnitOfWorkFactory(repository),
        ),
        cases_service=cast(CasesService, FakeCasesService(detail)),
        short_memory=memory,
        recent_message_limit=20,
    )
    principal = Principal(
        user_id="user-001",
        org_id="org-001",
        session_id="session-001",
        roles=frozenset({"consultant"}),
        permissions=frozenset({"cases:read", "cases:write"}),
    )

    context = await service.get_context("conversation-001", principal)

    assert context.memory_source == "mysql_restored"
    assert context.state.profile_version == 2
    assert context.state.confirmed_facts[0].fact_key == "invoice_intent"
    assert await memory.get("org-001", "conversation-001") == context.state

    fake_redis.fail_reads = True
    degraded_context = await service.get_context("conversation-001", principal)

    assert degraded_context.memory_source == "mysql_only"
    assert degraded_context.state.confirmed_facts == context.state.confirmed_facts


async def test_cross_org_conversation_access_returns_resource_not_found() -> None:
    now = datetime.now(UTC)
    conversation = ConversationRecord(
        id="conversation-001",
        org_id="org-001",
        case_id="case-001",
        title="虚构咨询会话",
        status="active",
        started_by="user-001",
        last_message_at=None,
        summary_version=0,
        created_at=now,
        updated_at=now,
    )
    repository = FakeConversationRepository(conversation, [])
    service = ConversationsService(
        uow_factory=cast(
            ConversationsUnitOfWorkFactory,
            FakeConversationUnitOfWorkFactory(repository),
        ),
        cases_service=cast(CasesService, object()),
        short_memory=RedisShortMemoryAdapter(cast(Redis, FakeRedis()), ttl_seconds=259200),
        recent_message_limit=20,
    )
    other_org_principal = Principal(
        user_id="user-002",
        org_id="org-002",
        session_id="session-002",
        roles=frozenset({"consultant"}),
        permissions=frozenset({"cases:read"}),
    )

    with pytest.raises(DomainError) as captured:
        await service.list_messages(
            conversation.id,
            other_org_principal,
            before_sequence=None,
            limit=20,
        )

    assert captured.value.code == "RESOURCE_NOT_FOUND"


async def test_append_user_message_is_idempotent_without_duplicate_sequence() -> None:
    now = datetime.now(UTC)
    case = CaseRecord(
        id="case-001",
        org_id="org-001",
        case_no="CASE-001",
        title="虚构事项",
        status="draft",
        owner_user_id="user-001",
        reviewer_user_id=None,
        default_region_code="440300",
        current_profile_version=1,
        version_no=1,
        opened_at=now,
        updated_at=now,
    )
    detail = CaseDetail(
        case=case,
        profile=SubjectProfileRecord(
            id="profile-001",
            org_id="org-001",
            case_id="case-001",
            profile_version=1,
            legal_form_code="LIMITED_COMPANY",
            vat_taxpayer_type="SMALL_SCALE",
            small_low_profit_status="unknown",
            industry_code="GENERAL_TRADE",
            region_code="440300",
            business_date=date(2026, 8, 31),
            business_action_codes=["INVOICE_ISSUANCE"],
            extra_attributes={},
            data_classification="synthetic",
            confirmation_status="confirmed",
            supersedes_profile_id=None,
        ),
        facts=[],
    )
    conversation = ConversationRecord(
        id="conversation-001",
        org_id="org-001",
        case_id="case-001",
        title="虚构咨询会话",
        status="active",
        started_by="user-001",
        last_message_at=None,
        summary_version=0,
        created_at=now,
        updated_at=now,
    )
    messages: list[MessageRecord] = []
    repository = FakeConversationRepository(conversation, messages)
    service = ConversationsService(
        uow_factory=cast(
            ConversationsUnitOfWorkFactory,
            FakeConversationUnitOfWorkFactory(repository),
        ),
        cases_service=cast(CasesService, FakeCasesService(detail)),
        short_memory=RedisShortMemoryAdapter(cast(Redis, FakeRedis()), ttl_seconds=259200),
        recent_message_limit=20,
    )
    principal = Principal(
        user_id="user-001",
        org_id="org-001",
        session_id="session-001",
        roles=frozenset({"consultant"}),
        permissions=frozenset({"cases:read", "cases:write"}),
    )
    command = AppendUserMessageCommand(
        conversation_id=conversation.id,
        text="虚构咨询消息",
        idempotency_key="message-idempotency-001",
        request_id="request-001",
    )

    first = await service.append_user_message(command, principal)
    repeated = await service.append_user_message(command, principal)

    assert first.memory_sync_status == "synced"
    assert repeated.memory_sync_status == "already_recorded"
    assert repeated.message.id == first.message.id
    assert [message.sequence_no for message in messages] == [1]
