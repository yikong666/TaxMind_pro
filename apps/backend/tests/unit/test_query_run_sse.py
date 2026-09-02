from datetime import UTC, datetime

import pytest
from fastapi import HTTPException

from taxmind.entrypoints.api.query_runs import _event_cursor, _sse_events
from taxmind.modules.query.domain import QueryRunEvent


def test_event_cursor_accepts_only_the_matching_run_and_non_negative_sequence() -> None:
    assert _event_cursor("run-1", "run-1:3") == 3

    with pytest.raises(HTTPException, match="不匹配"):
        _event_cursor("run-1", "other-run:3")

    with pytest.raises(HTTPException, match="无效"):
        _event_cursor("run-1", "run-1:-1")


@pytest.mark.asyncio
async def test_sse_replay_uses_monotonic_cursor_ids_and_safe_payload() -> None:
    event = QueryRunEvent(
        id="event-1",
        run_id="run-1",
        sequence_no=2,
        event_type="delta",
        occurred_at=datetime(2026, 9, 2, tzinfo=UTC),
        payload={"message_id": "message-1", "text": "已验证内容", "citation_ids": ["chunk-1"]},
    )

    payload = "".join([item async for item in _sse_events([event])])

    assert payload.startswith("id: run-1:2\nevent: delta\ndata: {")
    assert '"citation_ids":["chunk-1"]' in payload
    assert "reasoning" not in payload
