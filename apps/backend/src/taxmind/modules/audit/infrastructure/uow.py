from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taxmind.modules.audit.infrastructure.repository import SqlAlchemyAuditRepository


class SqlAlchemyAuditUnitOfWork:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions
        self._session: AsyncSession | None = None
        self.repository: SqlAlchemyAuditRepository | None = None

    async def __aenter__(self) -> SqlAlchemyAuditUnitOfWork:
        self._session = self._sessions()
        self.repository = SqlAlchemyAuditRepository(self._session)
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._session is not None:
            await self._session.close()


class SqlAlchemyAuditUnitOfWorkFactory:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    def __call__(self) -> SqlAlchemyAuditUnitOfWork:
        return SqlAlchemyAuditUnitOfWork(self._sessions)
