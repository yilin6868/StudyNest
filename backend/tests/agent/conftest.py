from collections.abc import Callable, Iterator
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import SessionLocal


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
            username=f"agent_{suffix}",
            username_normalized=f"agent_{suffix}",
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
