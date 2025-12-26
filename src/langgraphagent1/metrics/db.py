from __future__ import annotations

import os
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from dotenv import load_dotenv
load_dotenv()

def make_engine() -> AsyncEngine:
    # пример:
    # DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db

    POSTGRES_USER = os.environ["POSTGRES_USER"]
    POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
    POSTGRES_DB = os.environ["POSTGRES_DB"]
    POSTGRES_HOST = os.environ["POSTGRES_HOST"]
    POSTGRES_PORT = os.environ["POSTGRES_PORT"]
    POSTGRES_DIALECT = os.environ["POSTGRES_DIALECT"]

    dsn = f"{POSTGRES_DIALECT}://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    return create_async_engine(dsn, pool_pre_ping=True)


ENGINE: AsyncEngine = make_engine()
SESSION_FACTORY = async_sessionmaker(bind=ENGINE, expire_on_commit=False, class_=AsyncSession)
