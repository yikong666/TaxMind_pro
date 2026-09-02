from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from taxmind.modules.audit.infrastructure.models import AuditLogModel
from taxmind.modules.conversations.domain import ConversationRecord, MessageRecord
from taxmind.modules.conversations.infrastructure.models import ConversationModel, MessageModel


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _conversation_record(model: ConversationModel) -> ConversationRecord:
    return ConversationRecord(
        id=model.id,
        org_id=model.org_id,
        case_id=model.case_id,
        title=model.title,
        status=model.status,
        started_by=model.started_by,
        last_message_at=_as_utc(model.last_message_at) if model.last_message_at else None,
        summary_version=model.summary_version,
        created_at=_as_utc(model.created_at),
        updated_at=_as_utc(model.updated_at),
        deleted_at=_as_utc(model.deleted_at) if model.deleted_at else None,
    )


def _message_record(model: MessageModel) -> MessageRecord:
    return MessageRecord(
        id=model.id,
        org_id=model.org_id,
        conversation_id=model.conversation_id,
        case_id=model.case_id,
        sequence_no=model.sequence_no,
        role=model.role,
        content_text=model.content_text,
        content_json=dict(model.content_json),
        run_id=model.run_id,
        parent_message_id=model.parent_message_id,
        visibility=model.visibility,
        content_hash=model.content_hash,
        redaction_status=model.redaction_status,
        idempotency_key=model.idempotency_key,
        created_at=_as_utc(model.created_at),
    )


class SqlAlchemyConversationsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_conversation(self, record: ConversationRecord) -> None:
        self._session.add(
            ConversationModel(
                id=record.id,
                org_id=record.org_id,
                case_id=record.case_id,
                title=record.title,
                status=record.status,
                started_by=record.started_by,
                last_message_at=record.last_message_at,
                summary_version=record.summary_version,
                created_at=record.created_at,
                updated_at=record.updated_at,
                deleted_at=record.deleted_at,
            )
        )

    async def update_conversation_lifecycle(self, record: ConversationRecord) -> None:
        await self._session.execute(
            update(ConversationModel)
            .where(
                ConversationModel.id == record.id,
                ConversationModel.org_id == record.org_id,
            )
            .values(
                status=record.status,
                deleted_at=record.deleted_at,
                updated_at=record.updated_at,
            )
        )

    async def get_conversation(
        self, conversation_id: str, org_id: str
    ) -> ConversationRecord | None:
        model = await self._session.scalar(
            select(ConversationModel).where(
                ConversationModel.id == conversation_id,
                ConversationModel.org_id == org_id,
            )
        )
        return _conversation_record(model) if model else None

    async def lock_conversation(
        self, conversation_id: str, org_id: str
    ) -> ConversationRecord | None:
        model = await self._session.scalar(
            select(ConversationModel)
            .where(
                ConversationModel.id == conversation_id,
                ConversationModel.org_id == org_id,
            )
            .with_for_update()
        )
        return _conversation_record(model) if model else None

    async def get_message_by_idempotency(
        self, conversation_id: str, org_id: str, idempotency_key: str
    ) -> MessageRecord | None:
        model = await self._session.scalar(
            select(MessageModel).where(
                MessageModel.conversation_id == conversation_id,
                MessageModel.org_id == org_id,
                MessageModel.idempotency_key == idempotency_key,
            )
        )
        return _message_record(model) if model else None

    async def next_sequence(self, conversation_id: str, org_id: str) -> int:
        current = await self._session.scalar(
            select(func.max(MessageModel.sequence_no)).where(
                MessageModel.conversation_id == conversation_id,
                MessageModel.org_id == org_id,
            )
        )
        return int(current or 0) + 1

    async def create_message(self, record: MessageRecord) -> None:
        self._session.add(
            MessageModel(
                id=record.id,
                org_id=record.org_id,
                conversation_id=record.conversation_id,
                case_id=record.case_id,
                sequence_no=record.sequence_no,
                role=record.role,
                content_text=record.content_text,
                content_json=record.content_json,
                run_id=record.run_id,
                parent_message_id=record.parent_message_id,
                visibility=record.visibility,
                content_hash=record.content_hash,
                redaction_status=record.redaction_status,
                idempotency_key=record.idempotency_key,
                created_at=record.created_at,
            )
        )

    async def touch_conversation(self, conversation_id: str, occurred_at: datetime) -> None:
        await self._session.execute(
            update(ConversationModel)
            .where(ConversationModel.id == conversation_id)
            .values(last_message_at=occurred_at, updated_at=occurred_at)
        )

    async def list_messages(
        self,
        conversation_id: str,
        org_id: str,
        *,
        before_sequence: int | None,
        limit: int,
    ) -> list[MessageRecord]:
        statement = select(MessageModel).where(
            MessageModel.conversation_id == conversation_id,
            MessageModel.org_id == org_id,
            MessageModel.visibility == "user_visible",
        )
        if before_sequence is not None:
            statement = statement.where(MessageModel.sequence_no < before_sequence)
        models = list(
            await self._session.scalars(
                statement.order_by(MessageModel.sequence_no.desc()).limit(limit)
            )
        )
        return [_message_record(model) for model in reversed(models)]

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
        self._session.add(
            AuditLogModel(
                org_id=org_id,
                actor_user_id=actor_user_id,
                action_code=action_code,
                resource_type="conversation",
                resource_id=resource_id,
                request_id=request_id,
                result="success",
                occurred_at=occurred_at,
            )
        )
