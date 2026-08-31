from __future__ import annotations

from taxmind.bootstrap.settings import Settings
from taxmind.entrypoints.worker.celery_app import create_celery


def test_celery_worker_uses_safe_json_and_controlled_outbox_schedule() -> None:
    app = create_celery(
        Settings(
            app_env="test",
            celery_broker_url="redis://127.0.0.1:6379/1",
            celery_result_backend="redis://127.0.0.1:6379/2",
            outbox_dispatch_batch_size=25,
        )
    )

    assert app.conf.task_serializer == "json"
    assert app.conf.accept_content == ["json"]
    assert app.conf.task_acks_late is True
    assert app.conf.worker_prefetch_multiplier == 1
    assert "taxmind.outbox.dispatch.v1" in app.tasks
    schedule = app.conf.beat_schedule["outbox-dispatch"]
    assert schedule["task"] == "taxmind.outbox.dispatch.v1"
    assert schedule["kwargs"]["limit"] == 25
