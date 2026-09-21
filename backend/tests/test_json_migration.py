import json
from datetime import date
from uuid import uuid4

from sqlalchemy import func, select

from app.db.models import DailyGoal, DailyStudyRecord, MigrationRun, StudySession, User
from app.db.session import SessionLocal
from app.services.json_migration import run_json_migration


def _sample(tmp_path):
    user_dir = tmp_path / f"legacy-{uuid4().hex}"
    user_dir.mkdir()
    (user_dir / "history.json").write_text(
        json.dumps(
            {
                "schemaVersion": 2,
                "days": {"2026-09-08": {"tomato": 2, "minutes": 50}},
                "completedSessions": {
                    str(uuid4()): {
                        "date": "2026-09-08",
                        "minutes": 25,
                        "completedAt": "2026-09-08T10:00:00+08:00",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (user_dir / "goal.json").write_text(
        json.dumps({"schemaVersion": 1, "text": "复习数据库"}), encoding="utf-8"
    )
    return user_dir


def test_dry_run_does_not_write_database(tmp_path):
    _sample(tmp_path)
    with SessionLocal() as db:
        before = db.scalar(select(func.count()).select_from(User))
        report = run_json_migration(db, tmp_path, mode="dry-run")
        after = db.scalar(select(func.count()).select_from(User))
    assert report.succeeded == 1
    assert report.tomatoes == 2
    assert report.minutes == 50
    assert len(report.source_checksums) == 1
    assert report.batch_id
    assert before == after


def test_import_is_repeatable_and_verify_matches(tmp_path):
    user_dir = _sample(tmp_path)
    migration_day = date(2026, 9, 9)
    with SessionLocal() as db:
        first = run_json_migration(
            db, tmp_path, mode="import", migration_date=migration_day
        )
        second = run_json_migration(
            db, tmp_path, mode="import", migration_date=migration_day
        )
        verified = run_json_migration(
            db, tmp_path, mode="verify", migration_date=migration_day
        )
        user = db.scalar(
            select(User).where(User.legacy_user_key == user_dir.name)
        )
        assert user is not None
        assert db.scalar(
            select(func.count()).select_from(DailyStudyRecord).where(
                DailyStudyRecord.user_id == user.id
            )
        ) == 1
        assert db.scalar(
            select(func.count()).select_from(StudySession).where(
                StudySession.user_id == user.id
            )
        ) == 1
        assert db.scalar(
            select(func.count()).select_from(DailyGoal).where(
                DailyGoal.user_id == user.id
            )
        ) == 1
        assert db.scalar(
            select(func.count()).select_from(MigrationRun).where(
                MigrationRun.source_key_hash.is_not(None)
            )
        ) >= 1
    assert first.succeeded == 1
    assert second.skipped == 1
    assert verified.succeeded == 1
    assert verified.conflicts == 0


def test_damaged_json_is_reported_and_preserved(tmp_path):
    user_dir = tmp_path / "damaged"
    user_dir.mkdir()
    source = user_dir / "history.json"
    source.write_text("{broken", encoding="utf-8")
    with SessionLocal() as db:
        report = run_json_migration(db, tmp_path, mode="import")
    assert report.failed == 1
    assert report.damaged_files == 1
    assert source.read_text(encoding="utf-8") == "{broken"
