"""Provides a database connection and its base model."""

import datetime
import json

import sqlalchemy as sql
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import alembic
import orch.config as conf


def _custom_json_encode(val):
    """Serializes values to JSON."""

    def _default(unknown):
        if isinstance(unknown, datetime.datetime):
            return unknown.isoformat()
        raise TypeError(f"could not encode {unknown} to json")

    return json.dumps(val, default=_default)


engine = create_async_engine(
    conf.async_database_url,
    json_serializer=_custom_json_encode,
    future=True,
    pool_size=30,
    max_overflow=30,
    pool_timeout=120,
)


Base = declarative_base()


async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


def run_migrations_offline():
    """Generate migration SQL."""
    alembic.context.configure(
        url=conf.database_url,
        target_metadata=Base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with alembic.context.begin_transaction():
        alembic.context.run_migrations()


def run_migrations_online():
    """Apply migrations to a database."""
    engine = sql.create_engine(conf.database_url, future=True)
    with engine.connect() as conn:
        alembic.context.configure(connection=conn, target_metadata=Base.metadata)
        with alembic.context.begin_transaction():
            alembic.context.run_migrations()
