"""Database engine and session management."""

from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from backend.app.core.config import get_settings

Base = declarative_base()
_engine: Engine | None = None
_SessionFactory: sessionmaker | None = None


def get_engine() -> Engine:
    """Return singleton SQLAlchemy engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        url = settings.sync_database_url
        connect_args = {}
        if url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
        _engine = create_engine(
            url,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
    return _engine


def get_session_factory() -> sessionmaker:
    """Return singleton sessionmaker."""
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
        )
    return _SessionFactory


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    factory = get_session_factory()
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database session."""
    with get_db_context() as session:
        yield session
