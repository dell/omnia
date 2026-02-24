# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Database session management.

Engine and session factory are lazily initialized on first use.
This allows the module to be imported safely even when DATABASE_URL
is not set (e.g. in dev mode with in-memory repositories).
"""

from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import db_config

_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker] = None


def _get_engine() -> Engine:
    """Lazily create and cache the SQLAlchemy engine.

    Raises:
        ValueError: If DATABASE_URL is not configured.
    """
    global _engine
    if _engine is None:
        db_config.validate()
        _engine = create_engine(
            db_config.database_url,
            pool_size=db_config.pool_size,
            max_overflow=db_config.max_overflow,
            pool_recycle=db_config.pool_recycle,
            echo=db_config.echo,
        )
    return _engine


def _get_session_factory() -> sessionmaker:
    """Lazily create and cache the session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_get_engine(),
        )
    return _session_factory


def SessionLocal() -> Session:
    """Create a new database session.

    Returns:
        A new SQLAlchemy Session instance.

    Raises:
        ValueError: If DATABASE_URL is not configured.
    """
    return _get_session_factory()()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Usage:
        with get_db_session() as session:
            session.add(obj)
            session.commit()
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


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
