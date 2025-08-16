"""Database connection and session management."""

from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool
import os
from typing import Generator


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://dentistry_user:dentistry_pass@localhost:5432/dentistry_db"
)

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    echo=True,  # Set to False in production
    pool_pre_ping=True,
    pool_recycle=300,
)


def create_tables():
    """Create all tables in the database."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Get database session."""
    with Session(engine) as session:
        yield session


def get_db_session() -> Session:
    """Get database session for direct use."""
    return Session(engine)
