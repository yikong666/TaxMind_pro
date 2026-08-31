from __future__ import annotations

from celery import Celery

from taxmind.entrypoints.worker.outbox_tasks import register_outbox_tasks


def register_tasks(app: Celery) -> None:
    register_outbox_tasks(app)
