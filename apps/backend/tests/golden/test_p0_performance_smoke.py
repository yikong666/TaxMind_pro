from __future__ import annotations

from datetime import UTC, date, datetime
from time import perf_counter

import pytest
from _query_run_support import make_service

from taxmind.modules.query.application.service import QueryRunCommand


@pytest.mark.asyncio
async def test_p0_scope_and_deterministic_routing_complete_within_one_second() -> None:
    service, principal, _ = make_service(
        rules=(),
        org_id="golden-org",
        case_id="golden-performance-case",
        conversation_id="golden-performance-conversation",
        user_id="golden-user",
    )
    started_at = perf_counter()

    run = await service.submit(
        QueryRunCommand(
            case_id="golden-performance-case",
            conversation_id="golden-performance-conversation",
            profile_version=1,
            query="虚构政策查询",
            facts={"business_date": date(2026, 9, 1), "region_code": "440300"},
            idempotency_key="golden-performance-key",
            request_id="golden-performance-request",
            occurred_at=datetime(2026, 9, 1, tzinfo=UTC),
        ),
        principal,
    )
    elapsed_seconds = perf_counter() - started_at

    assert run.status == "queued"
    assert elapsed_seconds < 1
