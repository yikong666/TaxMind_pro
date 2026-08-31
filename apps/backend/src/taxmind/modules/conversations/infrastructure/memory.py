from __future__ import annotations

from datetime import datetime
from typing import cast

import orjson
from redis.asyncio import Redis
from redis.exceptions import RedisError

from taxmind.modules.conversations.domain import ContextFact, MessageRecord, ShortMemoryState


class ShortMemoryUnavailable(RuntimeError):
    """Raised when the short-memory cache cannot be read or updated."""


class RedisShortMemoryAdapter:
    def __init__(self, client: Redis, *, ttl_seconds: int) -> None:
        self._client = client
        self._ttl_seconds = ttl_seconds

    @staticmethod
    def key(org_id: str, conversation_id: str) -> str:
        return f"tm:session:{org_id}:{conversation_id}"

    async def get(self, org_id: str, conversation_id: str) -> ShortMemoryState | None:
        try:
            payload = await self._client.get(self.key(org_id, conversation_id))
        except RedisError as exc:
            raise ShortMemoryUnavailable from exc
        if payload is None:
            return None
        try:
            data = orjson.loads(payload)
            return ShortMemoryState(
                org_id=str(data["org_id"]),
                conversation_id=str(data["conversation_id"]),
                case_id=str(data["case_id"]),
                profile_version=int(data["profile_version"]),
                confirmed_facts=[
                    ContextFact(
                        fact_key=str(item["fact_key"]),
                        value=item["value"],
                        effective_date=item.get("effective_date"),
                    )
                    for item in data["confirmed_facts"]
                ],
                recent_messages=[_message_from_json(item) for item in data["recent_messages"]],
            )
        except (KeyError, TypeError, ValueError, orjson.JSONDecodeError):
            return None

    async def set(self, state: ShortMemoryState) -> None:
        payload = {
            "org_id": state.org_id,
            "conversation_id": state.conversation_id,
            "case_id": state.case_id,
            "profile_version": state.profile_version,
            "confirmed_facts": [
                {
                    "fact_key": fact.fact_key,
                    "value": fact.value,
                    "effective_date": fact.effective_date,
                }
                for fact in state.confirmed_facts
            ],
            "recent_messages": [_message_to_json(message) for message in state.recent_messages],
        }
        try:
            await self._client.set(
                self.key(state.org_id, state.conversation_id),
                orjson.dumps(payload),
                ex=self._ttl_seconds,
            )
        except RedisError as exc:
            raise ShortMemoryUnavailable from exc

    async def close(self) -> None:
        await self._client.aclose()


def _message_to_json(message: MessageRecord) -> dict[str, object]:
    return {
        "id": message.id,
        "org_id": message.org_id,
        "conversation_id": message.conversation_id,
        "case_id": message.case_id,
        "sequence_no": message.sequence_no,
        "role": message.role,
        "content_text": message.content_text,
        "content_json": message.content_json,
        "run_id": message.run_id,
        "parent_message_id": message.parent_message_id,
        "visibility": message.visibility,
        "content_hash": message.content_hash,
        "redaction_status": message.redaction_status,
        "idempotency_key": message.idempotency_key,
        "created_at": message.created_at.isoformat(),
    }


def _message_from_json(data: dict[str, object]) -> MessageRecord:
    return MessageRecord(
        id=str(data["id"]),
        org_id=str(data["org_id"]),
        conversation_id=str(data["conversation_id"]),
        case_id=str(data["case_id"]),
        sequence_no=int(str(data["sequence_no"])),
        role=str(data["role"]),
        content_text=str(data["content_text"]),
        content_json=_object_dict(data["content_json"]),
        run_id=str(data["run_id"]) if data.get("run_id") is not None else None,
        parent_message_id=(
            str(data["parent_message_id"]) if data.get("parent_message_id") is not None else None
        ),
        visibility=str(data["visibility"]),
        content_hash=str(data["content_hash"]),
        redaction_status=str(data["redaction_status"]),
        idempotency_key=str(data["idempotency_key"]),
        created_at=datetime.fromisoformat(str(data["created_at"])),
    )


def _object_dict(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError("cached content_json must be an object")
    return dict(cast(dict[str, object], value))
