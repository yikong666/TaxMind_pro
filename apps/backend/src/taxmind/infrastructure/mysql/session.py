from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from taxmind.bootstrap.settings import Settings


def database_url(settings: Settings) -> URL:
    return URL.create(
        "mysql+asyncmy",
        username=settings.mysql_user,
        password=settings.mysql_password.get_secret_value(),
        host=settings.mysql_host,
        port=settings.mysql_port,
        database=settings.mysql_database,
        query={"charset": "utf8mb4"},
    )


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        database_url(settings),
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_size=settings.mysql_pool_size,
        max_overflow=settings.mysql_max_overflow,
        echo=False,
    )


def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
