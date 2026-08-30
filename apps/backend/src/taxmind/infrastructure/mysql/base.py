from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Metadata root; schema is created only through Alembic migrations."""
