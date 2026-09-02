from __future__ import annotations

from datetime import UTC, date, datetime
from time import perf_counter

import pytest

from taxmind.modules.query.application.service import QueryRunCommand, QueryRunService


class _AuditRecorder:
    async def record(self, entry: dict[str, object]) -> None:
        del entry


@pytest.mark.asyncio
async def test_p0_scope_and_deterministic_routing_complete_within_one_second() -> None:
    service = QueryRunService(rules=(), audit_recorder=_AuditRecorder())
    started_at = perf_counter()

    run = await service.submit(
        QueryRunCommand(
            case_id="golden-performance-case",
            profile_version=1,
            query="虚构政策查询",
            facts={"business_date": date(2026, 9, 1), "region_code": "440300"},
            request_id="golden-performance-request",
            org_id="golden-org",
            actor_id="golden-user",
            occurred_at=datetime(2026, 9, 1, tzinfo=UTC),
        )
    )
    elapsed_seconds = perf_counter() - started_at

    assert run.status == "completed"
    assert elapsed_seconds < 1
