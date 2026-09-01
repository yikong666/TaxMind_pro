from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from taxmind.modules.feedback.infrastructure.repository import SqlAlchemyFeedbackRepository


class SqlAlchemyFeedbackUnitOfWork:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions
        self._session: AsyncSession | None = None
        self.repository: SqlAlchemyFeedbackRepository | None = None

    async def __aenter__(self) -> SqlAlchemyFeedbackUnitOfWork:
        self._session = self._sessions()
        self.repository = SqlAlchemyFeedbackRepository(self._session)
        return self

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("unit of work is not active")
        await self._session.commit()

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._session is not None:
            if exc_type is not None:
                await self._session.rollback()
            await self._session.close()


class SqlAlchemyFeedbackUnitOfWorkFactory:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    def __call__(self) -> SqlAlchemyFeedbackUnitOfWork:
        return SqlAlchemyFeedbackUnitOfWork(self._sessions)
