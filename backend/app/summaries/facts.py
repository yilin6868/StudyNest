"""从数据库事实生成每日/每周总结输入。"""
from datetime import date, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..db.models import DailyGoal, DailyStudyRecord, StudySession

def build_facts(db: Session, user_id: str, start: date, end: date) -> dict:
    days = db.scalars(select(DailyStudyRecord).where(DailyStudyRecord.user_id == user_id, DailyStudyRecord.study_date >= start, DailyStudyRecord.study_date <= end)).all()
    goals = db.scalars(select(DailyGoal).where(DailyGoal.user_id == user_id, DailyGoal.goal_date >= start, DailyGoal.goal_date <= end)).all()
    sessions = db.scalars(select(StudySession).where(StudySession.user_id == user_id, StudySession.completed_at >= start, StudySession.completed_at < end + timedelta(days=1), StudySession.status == "completed")).all()
    return {"period": f"{start.isoformat()}/{end.isoformat()}", "study_days": sum(1 for row in days if row.tomato_count > 0), "completed_sessions": len(sessions), "total_minutes": sum(max(0, int(row.minutes)) for row in days), "goals_set": sum(1 for row in goals if row.text.strip()), "data_quality": "complete"}
