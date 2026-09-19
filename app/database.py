"""SQLAlchemy engine/session setup. The only place DATABASE_URL is read."""
import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


def _normalized_database_url() -> str:
    url = os.environ["DATABASE_URL"]
    # Replit's DATABASE_URL uses the plain "postgresql://" scheme, which
    # SQLAlchemy defaults to psycopg2. We use psycopg (v3), so force the driver.
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


engine = create_engine(_normalized_database_url(), pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
