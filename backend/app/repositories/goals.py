"""每日目标数据访问。"""

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import DailyGoal


class GoalRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id: str, goal_date: date) -> str:
        goal = self.db.scalar(
            select(DailyGoal).where(
                DailyGoal.user_id == user_id,
                DailyGoal.goal_date == goal_date,
            )
        )
        return goal.text if goal else ""

    def set(
        self,
        user_id: str,
        goal_date: date,
        text: str,
        *,
        now: datetime,
        source: str = "app",
    ) -> str:
        goal = self.db.scalar(
            select(DailyGoal).where(
                DailyGoal.user_id == user_id,
                DailyGoal.goal_date == goal_date,
            )
        )
        if goal is None:
            self.db.add(
                DailyGoal(
                    user_id=user_id,
                    goal_date=goal_date,
                    text=text,
                    source=source,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            goal.text = text
            goal.source = source
            goal.updated_at = now
        return text
