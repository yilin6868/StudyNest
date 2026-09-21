"""学习记录、每日汇总和数据库级幂等结算。"""

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from ..db.models import DailyStudyRecord, StudySession
from ..services.stats import calculate_stats


class StudyRepository:
    def __init__(self, db: Session):
        self.db = db

    def _insert(self, model):
        dialect = self.db.get_bind().dialect.name
        if dialect == "postgresql":
            return postgresql_insert(model)
        if dialect == "sqlite":
            return sqlite_insert(model)
        raise RuntimeError("当前数据库类型不受支持")

    def complete(
        self,
        *,
        user_id: str,
        client_session_id: str,
        minutes: int,
        completed_at: datetime,
        source: str = "app",
    ) -> bool:
        session_stmt = (
            self._insert(StudySession)
            .values(
                user_id=user_id,
                client_session_id=client_session_id,
                started_at=None,
                ended_at=completed_at,
                completed_at=completed_at,
                minutes=minutes,
                status="completed",
                source=source,
                created_at=completed_at,
            )
            .on_conflict_do_nothing(index_elements=["user_id", "client_session_id"])
        )
        created = self.db.execute(session_stmt).rowcount == 1
        if not created:
            return False

        day = completed_at.date()
        daily_stmt = self._insert(DailyStudyRecord).values(
            user_id=user_id,
            study_date=day,
            tomato_count=1,
            minutes=minutes,
            updated_at=completed_at,
        )
        daily_stmt = daily_stmt.on_conflict_do_update(
            index_elements=["user_id", "study_date"],
            set_={
                "tomato_count": DailyStudyRecord.tomato_count + 1,
                "minutes": DailyStudyRecord.minutes + minutes,
                "updated_at": completed_at,
            },
        )
        self.db.execute(daily_stmt)
        return True

    def get_days(self, user_id: str) -> dict[str, dict[str, int]]:
        rows = self.db.scalars(
            select(DailyStudyRecord)
            .where(DailyStudyRecord.user_id == user_id)
            .order_by(DailyStudyRecord.study_date)
        ).all()
        return {
            row.study_date.isoformat(): {
                "tomato": row.tomato_count,
                "minutes": row.minutes,
            }
            for row in rows
        }

    def get_stats(self, user_id: str, *, today: date) -> dict:
        return calculate_stats(self.get_days(user_id), today)

    def get_completed_session(
        self, user_id: str, client_session_id: str
    ) -> StudySession | None:
        return self.db.scalar(
            select(StudySession).where(
                StudySession.user_id == user_id,
                StudySession.client_session_id == client_session_id,
                StudySession.status == "completed",
            )
        )

    def set_imported_day(
        self,
        *,
        user_id: str,
        study_date: date,
        tomato_count: int,
        minutes: int,
        now: datetime,
    ) -> bool:
        stmt = (
            self._insert(DailyStudyRecord)
            .values(
                user_id=user_id,
                study_date=study_date,
                tomato_count=tomato_count,
                minutes=minutes,
                updated_at=now,
            )
            .on_conflict_do_nothing(index_elements=["user_id", "study_date"])
        )
        return self.db.execute(stmt).rowcount == 1

    def add_imported_session(
        self,
        *,
        user_id: str,
        client_session_id: str,
        minutes: int,
        completed_at: datetime,
    ) -> bool:
        stmt = (
            self._insert(StudySession)
            .values(
                user_id=user_id,
                client_session_id=client_session_id,
                started_at=None,
                ended_at=completed_at,
                completed_at=completed_at,
                minutes=minutes,
                status="completed",
                source="legacy_import",
                created_at=completed_at,
            )
            .on_conflict_do_nothing(index_elements=["user_id", "client_session_id"])
        )
        return self.db.execute(stmt).rowcount == 1
