from __future__ import annotations

from datetime import datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field, JsonValue

from taxmind.entrypoints.api.dependencies import current_principal
from taxmind.modules.conversations.application.service import (
    AppendUserMessageCommand,
    ConversationsService,
    CreateConversationCommand,
)
from taxmind.modules.conversations.domain import (
    AppendMessageResult,
    ConversationContext,
    ConversationRecord,
    CreateConversationResult,
    MessageRecord,
)
from taxmind.shared.contracts.api import ResponseMeta
from taxmind.shared.domain.principal import Principal

router = APIRouter(tags=["conversations"])


class CreateConversationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)


class AppendUserMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=4000)
    idempotency_key: str = Field(min_length=1, max_length=100)


class ConversationData(BaseModel):
    id: str
    case_id: str
    title: str
    status: str
    started_by: str
    last_message_at: datetime | None
    summary_version: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class MessageData(BaseModel):
    id: str
    conversation_id: str
    case_id: str
    sequence_no: int
    role: str
    content_text: str
    content_json: dict[str, JsonValue]
    visibility: str
    redaction_status: str
    created_at: datetime


class ContextFactData(BaseModel):
    fact_key: str
    value: JsonValue
    effective_date: str | None


class ConversationContextData(BaseModel):
    conversation_id: str
    case_id: str
    profile_version: int
    confirmed_facts: list[ContextFactData]
    recent_messages: list[MessageData]
    memory_source: str


class ConversationResponse(BaseModel):
    data: ConversationData
    memory_sync_status: str
    meta: ResponseMeta


class ConversationLifecycleResponse(BaseModel):
    data: ConversationData
    meta: ResponseMeta


class MessageResponse(BaseModel):
    data: MessageData
    memory_sync_status: str
    meta: ResponseMeta


class MessagesResponse(BaseModel):
    data: list[MessageData]
    meta: ResponseMeta


class ConversationContextResponse(BaseModel):
    data: ConversationContextData
    meta: ResponseMeta


def _service(request: Request) -> ConversationsService:
    services = cast(dict[str, object], request.app.state.services)
    service = services.get("conversations")
    if not isinstance(service, ConversationsService):
        raise RuntimeError("conversations service is not configured")
    return service


def _meta(request: Request) -> ResponseMeta:
    return ResponseMeta(request_id=request.state.request_id)


def _conversation_data(conversation: ConversationRecord) -> ConversationData:
    return ConversationData(
        id=conversation.id,
        case_id=conversation.case_id,
        title=conversation.title,
        status=conversation.status,
        started_by=conversation.started_by,
        last_message_at=conversation.last_message_at,
        summary_version=conversation.summary_version,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        deleted_at=conversation.deleted_at,
    )


def _message_data(message: MessageRecord) -> MessageData:
    return MessageData(
        id=message.id,
        conversation_id=message.conversation_id,
        case_id=message.case_id,
        sequence_no=message.sequence_no,
        role=message.role,
        content_text=message.content_text,
        content_json=cast(dict[str, JsonValue], message.content_json),
        visibility=message.visibility,
        redaction_status=message.redaction_status,
        created_at=message.created_at,
    )


def _context_data(context: ConversationContext) -> ConversationContextData:
    return ConversationContextData(
        conversation_id=context.state.conversation_id,
        case_id=context.state.case_id,
        profile_version=context.state.profile_version,
        confirmed_facts=[
            ContextFactData(
                fact_key=fact.fact_key,
                value=cast(JsonValue, fact.value),
                effective_date=fact.effective_date,
            )
            for fact in context.state.confirmed_facts
        ],
        recent_messages=[_message_data(message) for message in context.state.recent_messages],
        memory_source=context.memory_source,
    )


@router.post("/cases/{case_id}/conversations", response_model=ConversationResponse)
async def create_conversation(
    case_id: str,
    payload: CreateConversationRequest,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> ConversationResponse:
    result: CreateConversationResult = await _service(request).create_conversation(
        CreateConversationCommand(
            case_id=case_id,
            title=payload.title,
            request_id=request.state.request_id,
        ),
        principal,
    )
    return ConversationResponse(
        data=_conversation_data(result.conversation),
        memory_sync_status=result.memory_sync_status,
        meta=_meta(request),
    )


@router.post("/conversations/{conversation_id}/messages", response_model=MessageResponse)
async def append_user_message(
    conversation_id: str,
    payload: AppendUserMessageRequest,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> MessageResponse:
    result: AppendMessageResult = await _service(request).append_user_message(
        AppendUserMessageCommand(
            conversation_id=conversation_id,
            text=payload.text,
            idempotency_key=payload.idempotency_key,
            request_id=request.state.request_id,
        ),
        principal,
    )
    return MessageResponse(
        data=_message_data(result.message),
        memory_sync_status=result.memory_sync_status,
        meta=_meta(request),
    )


@router.get("/conversations/{conversation_id}/messages", response_model=MessagesResponse)
async def list_messages(
    conversation_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
    before_sequence: Annotated[int | None, Query(ge=1)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> MessagesResponse:
    messages = await _service(request).list_messages(
        conversation_id,
        principal,
        before_sequence=before_sequence,
        limit=limit,
    )
    return MessagesResponse(
        data=[_message_data(message) for message in messages], meta=_meta(request)
    )


@router.get("/conversations/{conversation_id}/context", response_model=ConversationContextResponse)
async def get_conversation_context(
    conversation_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> ConversationContextResponse:
    context = await _service(request).get_context(conversation_id, principal)
    return ConversationContextResponse(data=_context_data(context), meta=_meta(request))


@router.delete("/conversations/{conversation_id}", response_model=ConversationLifecycleResponse)
async def soft_delete_conversation(
    conversation_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> ConversationLifecycleResponse:
    conversation = await _service(request).soft_delete_conversation(
        conversation_id,
        request_id=request.state.request_id,
        principal=principal,
    )
    return ConversationLifecycleResponse(data=_conversation_data(conversation), meta=_meta(request))


@router.post(
    "/conversations/{conversation_id}/restore",
    response_model=ConversationLifecycleResponse,
)
async def restore_conversation(
    conversation_id: str,
    request: Request,
    principal: Annotated[Principal, Depends(current_principal)],
) -> ConversationLifecycleResponse:
    conversation = await _service(request).restore_conversation(
        conversation_id,
        request_id=request.state.request_id,
        principal=principal,
    )
    return ConversationLifecycleResponse(data=_conversation_data(conversation), meta=_meta(request))
