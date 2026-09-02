from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from taxmind.bootstrap.settings import get_settings
from taxmind.infrastructure.mysql.base import Base
from taxmind.infrastructure.mysql.session import create_engine
from taxmind.modules.audit.infrastructure import models as audit_models  # noqa: F401
from taxmind.modules.cases.infrastructure import models as cases_models  # noqa: F401
from taxmind.modules.conversations.infrastructure import models as conversation_models  # noqa: F401
from taxmind.modules.documents.infrastructure import models as document_models  # noqa: F401
from taxmind.modules.feedback.infrastructure import models as feedback_models  # noqa: F401
from taxmind.modules.identity.infrastructure import models as identity_models  # noqa: F401
from taxmind.modules.knowledge.infrastructure import models as knowledge_models  # noqa: F401
from taxmind.modules.procedures.infrastructure import models as procedure_models  # noqa: F401
from taxmind.modules.query.infrastructure import models as query_models  # noqa: F401
from taxmind.modules.reviews.infrastructure import models as review_models  # noqa: F401
from taxmind.modules.sources.infrastructure import models as source_models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    settings = get_settings()
    context.configure(
        url=create_engine(settings).url.render_as_string(hide_password=True),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine: AsyncEngine = create_engine(get_settings())
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
