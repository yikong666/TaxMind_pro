from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

logger = logging.getLogger("taxmind.lifecycle")


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
    container = app.state.container
    await container.startup()
    logger.info("application started", extra={"event": "application.started"})
    try:
        yield
    finally:
        await container.shutdown()
        logger.info("application stopped", extra={"event": "application.stopped"})
