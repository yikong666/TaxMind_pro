from __future__ import annotations

from datetime import timedelta

from celery import Celery

from taxmind.bootstrap.settings import Settings, get_settings
from taxmind.entrypoints.worker.task_registry import register_tasks


def create_celery(settings: Settings) -> Celery:
    app = Celery(
        "taxmind",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
    )
    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        task_time_limit=settings.worker_task_time_limit_seconds,
        task_default_queue="maintenance",
        task_routes={"taxmind.outbox.dispatch.v1": {"queue": "maintenance"}},
        beat_schedule={
            "outbox-dispatch": {
                "task": "taxmind.outbox.dispatch.v1",
                "schedule": timedelta(seconds=settings.outbox_dispatch_interval_seconds),
                "kwargs": {"limit": settings.outbox_dispatch_batch_size},
            }
        },
    )
    register_tasks(app)
    return app


app = create_celery(get_settings())
