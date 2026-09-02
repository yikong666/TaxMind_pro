from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ConversationRecord:
    id: str
    org_id: str
    case_id: str
    title: str
    status: str
    started_by: str
    last_message_at: datetime | None
    summary_version: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class MessageRecord:
    id: str
    org_id: str
    conversation_id: str
    case_id: str
    sequence_no: int
    role: str
    content_text: str
    content_json: dict[str, object]
    run_id: str | None
    parent_message_id: str | None
    visibility: str
    content_hash: str
    redaction_status: str
    idempotency_key: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ContextFact:
    fact_key: str
    value: object
    effective_date: str | None


@dataclass(frozen=True, slots=True)
class ShortMemoryState:
    org_id: str
    conversation_id: str
    case_id: str
    profile_version: int
    confirmed_facts: list[ContextFact]
    recent_messages: list[MessageRecord]


@dataclass(frozen=True, slots=True)
class ConversationContext:
    state: ShortMemoryState
    memory_source: str


@dataclass(frozen=True, slots=True)
class AppendMessageResult:
    message: MessageRecord
    memory_sync_status: str


@dataclass(frozen=True, slots=True)
class CreateConversationResult:
    conversation: ConversationRecord
    memory_sync_status: str
