"""脱敏 Agent 事件写入与查询。"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..db.models import AgentEvent


class AgentEventRepository:
    def __init__(self, db: Session):
        self.db = db

    def add_many(self, events: list[dict]) -> None:
        self.db.add_all([AgentEvent(**item) for item in events])

    def by_request(self, request_id: str) -> list[AgentEvent]:
        return list(
            self.db.scalars(
                select(AgentEvent)
                .where(AgentEvent.request_id == request_id)
                .order_by(AgentEvent.sequence.asc())
            )
        )

    def since(self, hours: int) -> list[AgentEvent]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return list(
            self.db.scalars(
                select(AgentEvent).where(AgentEvent.created_at >= cutoff)
            )
        )

    def delete_before(self, cutoff: datetime) -> int:
        result = self.db.execute(delete(AgentEvent).where(AgentEvent.created_at < cutoff))
        return int(result.rowcount or 0)

