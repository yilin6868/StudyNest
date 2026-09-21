"""数据库 Engine、请求级 Session 和 readiness 检查。"""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ..core.config import settings

HEAD_REVISION = "20260909_0006"


def create_app_engine(database_url: str | None = None) -> Engine:
    url = database_url or settings.database_url
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        kwargs["pool_size"] = settings.database_pool_size
        kwargs["pool_timeout"] = settings.database_pool_timeout
    return create_engine(url, **kwargs)


engine = create_app_engine()
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session


def database_ready() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            ).scalar_one_or_none()
            return revision == HEAD_REVISION
    except Exception:  # noqa: BLE001 —— readiness 不泄露连接信息
        return False
