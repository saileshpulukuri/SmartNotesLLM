"""
Database utilities for initializing SQLAlchemy sessions and metadata.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from .config import get_settings


settings = get_settings()
engine = create_engine(settings.database_url, future=True, echo=settings.debug)
SessionLocal = scoped_session(
    sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
)


@contextmanager
def session_scope() -> Iterator[scoped_session]:
    """
    Provide a transactional scope around a series of operations.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


__all__ = ["engine", "SessionLocal", "session_scope"]

