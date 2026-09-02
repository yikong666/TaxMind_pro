from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Protocol

from taxmind.modules.cases.application.service import CasesService
from taxmind.modules.cases.domain import CaseDetail, reject_restricted_identifiers
from taxmind.modules.conversations.domain import (
    AppendMessageResult,
    ContextFact,
    ConversationContext,
    ConversationRecord,
    CreateConversationResult,
    MessageRecord,
    ShortMemoryState,
)
from taxmind.modules.conversations.infrastructure.memory import ShortMemoryUnavailable
from taxmind.modules.conversations.infrastructure.repository import (
    SqlAlchemyConversationsRepository,
)
from taxmind.modules.conversations.infrastructure.uow import (
    SqlAlchemyConversationsUnitOfWork,
)
from taxmind.shared.domain.errors import DomainError
from taxmind.shared.domain.ids import new_id
from taxmind.shared.domain.principal import Principal

logger = logging.getLogger("taxmind.conversations")


class ConversationsUnitOfWorkFactory(Protocol):
    def __call__(self) -> SqlAlchemyConversationsUnitOfWork: ...


class ShortMemoryPort(Protocol):
    async def get(self, org_id: str, conversation_id: str) -> ShortMemoryState | None: ...

    async def set(self, state: ShortMemoryState) -> None: ...


@dataclass(frozen=True, slots=True)
class CreateConversationCommand:
    case_id: str
    title: str
    request_id: str


@dataclass(frozen=True, slots=True)
class AppendUserMessageCommand:
    conversation_id: str
    text: str
    idempotency_key: str
    request_id: str


class ConversationsService:
    def __init__(
        self,
        *,
        uow_factory: ConversationsUnitOfWorkFactory,
        cases_service: CasesService,
        short_memory: ShortMemoryPort,
        recent_message_limit: int,
    ) -> None:
        self._uow_factory = uow_factory
        self._cases_service = cases_service
        self._short_memory = short_memory
        self._recent_message_limit = recent_message_limit

    async def create_conversation(
        self, command: CreateConversationCommand, principal: Principal
    ) -> CreateConversationResult:
        _require_conversation_access(principal)
        case_detail = await self._cases_service.get_case(command.case_id, principal)
        title = _normalized_title(command.title)
        now = datetime.now(UTC)
        conversation = ConversationRecord(
            id=new_id(),
            org_id=principal.org_id,
            case_id=case_detail.case.id,
            title=title,
            status="active",
            started_by=principal.user_id,
            last_message_at=None,
            summary_version=0,
            created_at=now,
            updated_at=now,
        )
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            await repository.create_conversation(conversation)
            await repository.create_audit_log(
                org_id=principal.org_id,
                actor_user_id=principal.user_id,
                action_code="conversation.created",
                resource_id=conversation.id,
                request_id=command.request_id,
                occurred_at=now,
            )
            await uow.commit()
        state = _state_from(case_detail, conversation, [])
        memory_status = await self._persist_short_memory(state)
        return CreateConversationResult(
            conversation=conversation,
            memory_sync_status=memory_status,
        )

    async def append_user_message(
        self, command: AppendUserMessageCommand, principal: Principal
    ) -> AppendMessageResult:
        _require_conversation_access(principal)
        text = _normalized_message(command.text)
        idempotency_key = _normalized_idempotency_key(command.idempotency_key)
        conversation = await self._accessible_conversation(command.conversation_id, principal)
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            locked = await repository.lock_conversation(conversation.id, principal.org_id)
            if locked is None:
                raise DomainError(code="RESOURCE_NOT_FOUND", message="会话不存在或无权访问")
            existing = await repository.get_message_by_idempotency(
                conversation.id, principal.org_id, idempotency_key
            )
            if existing is not None:
                return AppendMessageResult(
                    message=existing,
                    memory_sync_status="already_recorded",
                )
            message = MessageRecord(
                id=new_id(),
                org_id=principal.org_id,
                conversation_id=conversation.id,
                case_id=conversation.case_id,
                sequence_no=await repository.next_sequence(conversation.id, principal.org_id),
                role="user",
                content_text=text,
                content_json={},
                run_id=None,
                parent_message_id=None,
                visibility="user_visible",
                content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                redaction_status="not_needed",
                idempotency_key=idempotency_key,
                created_at=now,
            )
            await repository.create_message(message)
            await repository.touch_conversation(conversation.id, now)
            await repository.create_audit_log(
                org_id=principal.org_id,
                actor_user_id=principal.user_id,
                action_code="conversation.message.appended",
                resource_id=conversation.id,
                request_id=command.request_id,
                occurred_at=now,
            )
            await uow.commit()
        state = await self._rebuild_state(conversation, principal)
        memory_status = await self._persist_short_memory(state)
        return AppendMessageResult(message=message, memory_sync_status=memory_status)

    async def list_messages(
        self,
        conversation_id: str,
        principal: Principal,
        *,
        before_sequence: int | None,
        limit: int,
    ) -> list[MessageRecord]:
        _require_conversation_access(principal)
        conversation = await self._accessible_conversation(conversation_id, principal)
        async with self._uow_factory() as uow:
            return await _repository(uow).list_messages(
                conversation.id,
                principal.org_id,
                before_sequence=before_sequence,
                limit=limit,
            )

    async def get_context(self, conversation_id: str, principal: Principal) -> ConversationContext:
        _require_conversation_access(principal)
        conversation = await self._accessible_conversation(conversation_id, principal)
        case_detail = await self._cases_service.get_case(conversation.case_id, principal)
        try:
            cached = await self._short_memory.get(principal.org_id, conversation.id)
        except ShortMemoryUnavailable:
            cached = None
            cache_available = False
        else:
            cache_available = True
        if cached is not None and cached.profile_version == case_detail.profile.profile_version:
            return ConversationContext(state=cached, memory_source="redis")
        state = await self._rebuild_state(conversation, principal, case_detail=case_detail)
        if not cache_available:
            self._log_memory_degraded(conversation.id, principal.org_id)
            return ConversationContext(state=state, memory_source="mysql_only")
        status = await self._persist_short_memory(state)
        source = "mysql_restored" if status == "synced" else "mysql_only"
        return ConversationContext(state=state, memory_source=source)

    async def soft_delete_conversation(
        self,
        conversation_id: str,
        *,
        request_id: str,
        principal: Principal,
    ) -> ConversationRecord:
        return await self._transition_conversation_lifecycle(
            conversation_id,
            target_status="deleted",
            request_id=request_id,
            principal=principal,
        )

    async def restore_conversation(
        self,
        conversation_id: str,
        *,
        request_id: str,
        principal: Principal,
    ) -> ConversationRecord:
        return await self._transition_conversation_lifecycle(
            conversation_id,
            target_status="active",
            request_id=request_id,
            principal=principal,
        )

    async def _transition_conversation_lifecycle(
        self,
        conversation_id: str,
        *,
        target_status: str,
        request_id: str,
        principal: Principal,
    ) -> ConversationRecord:
        _require_conversation_write(principal)
        now = datetime.now(UTC)
        async with self._uow_factory() as uow:
            repository = _repository(uow)
            conversation = await repository.lock_conversation(conversation_id, principal.org_id)
            if conversation is None or not _can_manage_conversation(conversation, principal):
                raise DomainError(code="RESOURCE_NOT_FOUND", message="会话不存在或无权管理")
            if conversation.status == target_status:
                return conversation
            if conversation.status not in {"active", "deleted"}:
                raise DomainError(code="RESOURCE_CONFLICT", message="当前会话状态不允许此操作")
            updated = replace(
                conversation,
                status=target_status,
                deleted_at=now if target_status == "deleted" else None,
                updated_at=now,
            )
            await repository.update_conversation_lifecycle(updated)
            await repository.create_audit_log(
                org_id=principal.org_id,
                actor_user_id=principal.user_id,
                action_code=(
                    "conversation.deleted"
                    if target_status == "deleted"
                    else "conversation.restored"
                ),
                resource_id=conversation.id,
                request_id=request_id,
                occurred_at=now,
            )
            await uow.commit()
        return updated

    async def _accessible_conversation(
        self, conversation_id: str, principal: Principal
    ) -> ConversationRecord:
        async with self._uow_factory() as uow:
            conversation = await _repository(uow).get_conversation(
                conversation_id, principal.org_id
            )
        if conversation is None or conversation.status != "active":
            raise DomainError(code="RESOURCE_NOT_FOUND", message="会话不存在或无权访问")
        await self._cases_service.get_case(conversation.case_id, principal)
        return conversation

    async def _rebuild_state(
        self,
        conversation: ConversationRecord,
        principal: Principal,
        *,
        case_detail: CaseDetail | None = None,
    ) -> ShortMemoryState:
        resolved_case = case_detail or await self._cases_service.get_case(
            conversation.case_id, principal
        )
        async with self._uow_factory() as uow:
            messages = await _repository(uow).list_messages(
                conversation.id,
                principal.org_id,
                before_sequence=None,
                limit=self._recent_message_limit,
            )
        return _state_from(resolved_case, conversation, messages)

    async def _persist_short_memory(self, state: ShortMemoryState) -> str:
        try:
            await self._short_memory.set(state)
        except ShortMemoryUnavailable:
            self._log_memory_degraded(state.conversation_id, state.org_id)
            return "degraded"
        return "synced"

    @staticmethod
    def _log_memory_degraded(conversation_id: str, org_id: str) -> None:
        logger.warning(
            "short memory unavailable; MySQL remains authoritative",
            extra={
                "event": "conversation.memory.degraded",
                "error_code": "SHORT_MEMORY_UNAVAILABLE",
                "conversation_id": conversation_id,
                "org_id": org_id,
            },
        )


def _repository(uow: SqlAlchemyConversationsUnitOfWork) -> SqlAlchemyConversationsRepository:
    if uow.repository is None:
        raise RuntimeError("unit of work repository is unavailable")
    return uow.repository


def _require_conversation_access(principal: Principal) -> None:
    if not principal.has_permission("cases:read"):
        raise DomainError(code="AUTH_FORBIDDEN", message="当前角色无会话访问权限")


def _require_conversation_write(principal: Principal) -> None:
    if not principal.has_permission("cases:write"):
        raise DomainError(code="AUTH_FORBIDDEN", message="当前角色无会话管理权限")


def _can_manage_conversation(conversation: ConversationRecord, principal: Principal) -> bool:
    return conversation.started_by == principal.user_id or "org_admin" in principal.roles


def _normalized_title(value: str) -> str:
    title = value.strip()
    if not title:
        raise DomainError(code="VALIDATION_FAILED", message="会话标题不能为空")
    reject_restricted_identifiers(title)
    return title


def _normalized_message(value: str) -> str:
    text = value.strip()
    if not text:
        raise DomainError(code="VALIDATION_FAILED", message="消息不能为空")
    if len(text) > 4000:
        raise DomainError(code="VALIDATION_FAILED", message="消息不能超过 4000 个字符")
    reject_restricted_identifiers(text)
    return text


def _normalized_idempotency_key(value: str) -> str:
    key = value.strip()
    if not key or len(key) > 100:
        raise DomainError(code="VALIDATION_FAILED", message="幂等键无效")
    return key


def _state_from(
    case_detail: CaseDetail,
    conversation: ConversationRecord,
    messages: list[MessageRecord],
) -> ShortMemoryState:
    facts = [
        ContextFact(
            fact_key=fact.fact_key,
            value=fact.value,
            effective_date=fact.effective_date.isoformat() if fact.effective_date else None,
        )
        for fact in case_detail.facts
        if fact.confirmation_status == "confirmed"
    ]
    return ShortMemoryState(
        org_id=conversation.org_id,
        conversation_id=conversation.id,
        case_id=conversation.case_id,
        profile_version=case_detail.profile.profile_version,
        confirmed_facts=facts,
        recent_messages=messages,
    )
