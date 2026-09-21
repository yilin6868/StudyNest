from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func, select

from app.db.models import DailyStudyRecord, StudySession
from app.db.session import SessionLocal
from app.repositories.study import StudyRepository
from app.services import auth


def test_database_enforces_session_idempotency_across_sessions():
    with SessionLocal() as db:
        username = f"reliability_{uuid4().hex[:10]}"
        account = auth.register(db, "TESTCODE1", username, "Password123")
    session_id = str(uuid4())

    def complete_once():
        with SessionLocal() as db:
            created = StudyRepository(db).complete(
                user_id=account["user_id"],
                client_session_id=session_id,
                minutes=25,
                completed_at=datetime.now(timezone.utc),
            )
            db.commit()
            return created

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: complete_once(), range(2)))

    with SessionLocal() as db:
        sessions = db.scalar(
            select(func.count()).select_from(StudySession).where(
                StudySession.user_id == account["user_id"],
                StudySession.client_session_id == session_id,
            )
        )
        daily = db.scalar(
            select(DailyStudyRecord).where(
                DailyStudyRecord.user_id == account["user_id"],
                DailyStudyRecord.study_date == datetime.now(timezone.utc).date(),
            )
        )
    assert sorted(results) == [False, True]
    assert sessions == 1
    assert daily is not None
    assert daily.tomato_count == 1


def test_last_invite_slot_can_only_be_used_once():
    code = f"ONE-SLOT-{uuid4().hex}"
    with SessionLocal() as db:
        auth.create_invite(db, code, max_uses=1)

    def register_once(index: int):
        with SessionLocal() as db:
            try:
                auth.register(
                    db,
                    code,
                    f"concurrent_{index}_{uuid4().hex[:8]}",
                    "Password123",
                )
                return True
            except auth.AccountError:
                return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(register_once, range(2)))
    assert sorted(results) == [False, True]
