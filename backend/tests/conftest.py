"""pytest 全局配置：所有 API 测试使用隔离的临时数据库。"""
import os
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from collections.abc import Callable, Iterator
from datetime import datetime, timezone

_TEST_ROOT = Path(tempfile.mkdtemp(prefix="sb_test_"))
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
# 强制覆盖调用者环境，保证测试绝不误连外部或生产数据库。
os.environ["DATA_DIR"] = str(_TEST_ROOT / "data")
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_TEST_ROOT / 'test.sqlite3'}"
os.environ["APP_ENV"] = "test"
os.environ["APP_TIMEZONE"] = "Asia/Shanghai"
os.environ["AUTH_SECRET"] = "test-secret"
os.environ["INVITE_CODE_PEPPER"] = "test-invite-pepper"
os.environ["ALLOW_LEGACY_TOKENS"] = "false"
os.environ["LLM_API_KEY"] = ""

alembic_config = Config(str(_BACKEND_ROOT / "alembic.ini"))
alembic_config.set_main_option("script_location", str(_BACKEND_ROOT / "migrations"))
command.upgrade(alembic_config, "head")

from app.main import app  # noqa: E402
from app.db.models import User  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.services.auth import create_invite  # noqa: E402

with SessionLocal() as _db:
    create_invite(_db, "TESTCODE1", max_uses=None)
    create_invite(_db, "TESTCODE2", max_uses=None)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers():
    with TestClient(app) as test_client:
        username = f"test_{uuid4().hex[:12]}"
        r = test_client.post(
            "/api/v1/auth/register",
            json={
                "inviteCode": "TESTCODE1",
                "username": username,
                "password": "Password123",
            },
        )
        assert r.status_code == 200
        return {"Authorization": "Bearer " + r.json()["token"]}


@pytest.fixture
def db_session() -> Iterator[Session]:
    with SessionLocal() as db:
        yield db
        db.rollback()


@pytest.fixture
def user_factory(db_session: Session) -> Callable[..., User]:
    def create(*, status: str = "active", timezone_name: str = "Asia/Shanghai") -> User:
        now = datetime.now(timezone.utc)
        suffix = uuid4().hex[:12]
        user = User(
            username=f"p1c_{suffix}",
            username_normalized=f"p1c_{suffix}",
            password_hash="not-exposed-to-agent",
            timezone=timezone_name,
            status=status,
            created_at=now,
            updated_at=now,
        )
        db_session.add(user)
        db_session.commit()
        return user

    return create
