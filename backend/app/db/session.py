"""Database session and connection management with graceful fallback."""

import logging
import time
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session as SQLAlchemySession
from sqlalchemy.exc import OperationalError, DatabaseError

from app.core.config import settings
from app.db.models import Base

logger = logging.getLogger(__name__)

# Determine if initial target is SQLite or PostgreSQL
initial_url = settings.get_database_url
is_sqlite = initial_url.startswith("sqlite")

connect_args = {"check_same_thread": False} if is_sqlite else {}
pool_kwargs = {} if is_sqlite else {"pool_pre_ping": True, "pool_size": 10, "max_overflow": 20}

engine = create_engine(
    initial_url,
    connect_args=connect_args,
    **pool_kwargs,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def _activate_sqlite_fallback() -> None:
    """Seamlessly reconfigure database engine and SessionLocal to use local SQLite."""
    global engine, is_sqlite
    logger.info("Activating seamless local SQLite database fallback (lenny_growth_local.db)...")
    is_sqlite = True
    engine = create_engine(
        "sqlite:///./lenny_growth_local.db",
        connect_args={"check_same_thread": False},
    )
    SessionLocal.configure(bind=engine)
    Base.metadata.create_all(bind=engine)
    logger.info("Local SQLite database initialized and SessionLocal bound successfully.")


def get_db_session() -> SQLAlchemySession:
    """Factory function returning an active, validated database session."""
    global engine, is_sqlite
    try:
        session = SessionLocal()
        session.execute(text("SELECT 1"))
        return session
    except Exception as err:
        if not is_sqlite:
            logger.warning("Primary database offline (%s). Engaging local SQLite fallback.", err)
            _activate_sqlite_fallback()
            return SessionLocal()
        raise


def get_db() -> Generator[SQLAlchemySession, None, None]:
    """FastAPI dependency yielding a scoped database session."""
    session = get_db_session()
    try:
        yield session
    finally:
        session.close()


def ping_db() -> bool:
    """Execute a simple query to verify database reachability."""
    try:
        session = get_db_session()
        session.execute(text("SELECT 1"))
        session.close()
        return True
    except Exception as err:
        logger.warning("Database ping failed: %s", err)
        return False


def init_db(max_retries: int = 2, initial_backoff: float = 0.5) -> None:
    """Initialize database tables with automatic SQLite fallback."""
    global engine, is_sqlite
    backoff = initial_backoff
    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Initializing database tables (attempt %d/%d)...", attempt, max_retries)
            if not is_sqlite:
                with engine.connect() as conn:
                    try:
                        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                        conn.commit()
                    except Exception as ext_err:
                        logger.warning("pgvector extension check note: %s", ext_err)

            Base.metadata.create_all(bind=engine)
            logger.info("Database tables initialized successfully.")
            return
        except (OperationalError, DatabaseError) as err:
            if attempt == max_retries:
                if not is_sqlite:
                    logger.warning(
                        "PostgreSQL is offline (%s). Seamlessly activating local SQLite persistence fallback.",
                        err,
                    )
                    _activate_sqlite_fallback()
                    return
                logger.error("Max database initialization retries reached: %s", err)
                raise
            logger.warning("Database initialization attempt %d failed (%s). Retrying...", attempt, err)
            time.sleep(backoff)
            backoff *= 1.5
