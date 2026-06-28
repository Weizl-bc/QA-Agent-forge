"""SQLAlchemy engine and session lifecycle."""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import get_settings


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return create_engine(
        settings.mysql_url,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args={"connect_timeout": settings.mysql_connect_timeout},
    )


def get_db() -> Generator[Session, None, None]:
    """Provide one SQLAlchemy session per request."""
    session_factory = sessionmaker(
        bind=get_engine(), autoflush=False, expire_on_commit=False
    )
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
