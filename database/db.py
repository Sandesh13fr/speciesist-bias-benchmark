"""Database engine and transactional session utilities."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from database.models import Base

logger = logging.getLogger(__name__)


def create_engine_and_session(database_url: str) -> tuple[Engine, sessionmaker[Session]]:
    """Create SQLAlchemy engine and session factory.

    Args:
        database_url: SQLAlchemy database URL.

    Returns:
        Tuple of engine and configured sessionmaker.
    """
    engine = create_engine(database_url, future=True)
    session_factory = sessionmaker(
        bind=engine,
        class_=Session,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    return engine, session_factory


def init_db(database_url: str) -> None:
    """Initialize database schema.

    Args:
        database_url: SQLAlchemy database URL.
    """
    engine, _ = create_engine_and_session(database_url)
    Base.metadata.create_all(engine)
    logger.info("Initialized database schema at %s", database_url)


@contextmanager
def session_scope(database_url: str) -> Iterator[Session]:
    """Provide a transactional session scope.

    Args:
        database_url: SQLAlchemy database URL.

    Yields:
        Active SQLAlchemy session.
    """
    _, session_factory = create_engine_and_session(database_url)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        logger.exception("Rolling back database transaction for %s", database_url)
        session.rollback()
        raise
    finally:
        session.close()


class DatabaseManager:
    """Compatibility manager wrapper around engine and session factory.

    Args:
        database_url: SQLAlchemy database URL.
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.engine, self._session_factory = create_engine_and_session(database_url)

    def create_tables(self) -> None:
        """Create schema tables."""
        Base.metadata.create_all(self.engine)
        logger.info("Created tables for %s", self.database_url)

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        """Provide an instance-scoped transactional session."""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            logger.exception("Rolling back database transaction for %s", self.database_url)
            session.rollback()
            raise
        finally:
            session.close()
