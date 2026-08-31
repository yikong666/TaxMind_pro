from __future__ import annotations

import asyncio
from typing import Any

from celery import Celery

from taxmind.bootstrap.settings import Settings, get_settings
from taxmind.entrypoints.worker.outbox import (
    build_outbox_dispatch_service,
    dispatch_pending_projection_events,
)
from taxmind.infrastructure.mysql.session import create_engine, session_factory


def register_outbox_tasks(app: Celery) -> None:
    @app.task(name="taxmind.outbox.dispatch.v1", bind=True)
    def dispatch_outbox_task(task: Any, limit: int | None = None) -> dict[str, int]:
        settings = get_settings()
        selected_limit = limit if limit is not None else settings.outbox_dispatch_batch_size
        worker_id = f"celery-{task.request.id or 'unknown'}"
        return asyncio.run(_dispatch(settings, selected_limit, worker_id))


async def _dispatch(settings: Settings, limit: int, worker_id: str) -> dict[str, int]:
    engine = create_engine(settings)
    try:
        service = build_outbox_dispatch_service(settings, sessions=session_factory(engine))
        completed, retryable, dead = await dispatch_pending_projection_events(
            service,
            limit=limit,
            worker_id=worker_id,
        )
        return {"completed": completed, "retryable": retryable, "dead": dead}
    finally:
        await engine.dispose()
