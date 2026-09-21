"""把数据库和请求状态整理成最小、只读的模型观察上下文。"""

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from ..core.config import settings
from ..db.models import User
from ..repositories.goals import GoalRepository
from ..repositories.preferences import PreferenceRepository
from ..repositories.study import StudyRepository
from .contracts import (
    AgentInput,
    AgentState,
    ConversationMessage,
    FocusState,
    GoalState,
    LearningMemory,
    PreferenceState,
    StudyStatsState,
)
from .errors import AgentContextError


class StateObserver:
    def __init__(self, *, max_bytes: int | None = None) -> None:
        max_bytes = max_bytes or settings.agent_context_max_bytes
        if max_bytes < 512:
            raise ValueError("观察上下文上限不能小于 512 字节")
        self.max_bytes = max_bytes

    def build(
        self,
        db: Session,
        user: User,
        *,
        message: str,
        focus_state: FocusState | dict | None = None,
        conversation_summary: str = "",
        recent_messages: list[ConversationMessage] | None = None,
        memories: list[LearningMemory] | None = None,
    ) -> AgentInput:
        if not user.id or user.status != "active":
            raise AgentContextError("当前用户不能构造 Agent 上下文")
        try:
            zone = ZoneInfo(user.timezone)
        except ZoneInfoNotFoundError:
            zone = ZoneInfo(settings.app_timezone)
        today = datetime.now(zone).date()

        focus = FocusState.model_validate(focus_state or {})
        raw_stats = StudyRepository(db).get_stats(user.id, today=today)
        raw_preferences = PreferenceRepository(db).get(user.id)
        result = AgentInput(
            message=message,
            conversation_summary=conversation_summary,
            recent_messages=recent_messages or [],
            memories=memories or [],
            state=AgentState(
                goal=GoalState(
                    date=today,
                    text=GoalRepository(db).get(user.id, today),
                ),
                focus=focus,
                stats=StudyStatsState(
                    today_tomato=raw_stats["tomato"],
                    today_minutes=raw_stats["minutes"],
                    streak=raw_stats["streak"],
                    week_study_days=len(raw_stats["weekDays"]),
                ),
                preferences=PreferenceState(
                    buddy_gender=raw_preferences["buddy_gender"],
                    voice_enabled=raw_preferences["voice_enabled"],
                ),
            ),
        )
        size = len(result.model_dump_json(by_alias=True).encode("utf-8"))
        if size > self.max_bytes:
            raise AgentContextError("Agent 上下文超过安全长度")
        return result
