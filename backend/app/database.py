from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

_db_url = make_url(settings.database_url)
_is_sqlite = _db_url.get_backend_name().startswith("sqlite")

engine = create_async_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False, "timeout": 30} if _is_sqlite else {},
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        yield session


async def init_db() -> None:
    if not _is_sqlite:
        return
    async with engine.begin() as conn:
        await conn.execute(__import__("sqlalchemy").text("PRAGMA journal_mode=WAL"))
        await conn.execute(__import__("sqlalchemy").text("PRAGMA busy_timeout=30000"))
        await conn.execute(__import__("sqlalchemy").text("PRAGMA foreign_keys=ON"))
