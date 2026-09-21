"""在内存中收集、批量写入的脱敏 Agent 轨迹。"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..repositories.agent_events import AgentEventRepository
from .events import EVENT_TYPES, OUTCOMES
from .sanitizer import sanitize_payload

logger = logging.getLogger(__name__)


class TraceRecorder:
    def __init__(self, request_id: str, user_id: str, *, max_events: int = 50):
        self.request_id = request_id
        self.user_id = user_id
        self.max_events = max_events
        self._events: list[dict] = []
        self.truncated = False

    def record(
        self,
        event_type: str,
        *,
        outcome: str,
        duration_ms: int | None = None,
        **payload: object,
    ) -> None:
        if event_type not in EVENT_TYPES or outcome not in OUTCOMES:
            raise ValueError("Agent 事件类型或结果不在白名单")
        if len(self._events) >= self.max_events:
            self.truncated = True
            if self._events:
                current = json.loads(self._events[-1]["payload"])
                current["traceTruncated"] = True
                self._events[-1]["payload"] = json.dumps(
                    current, ensure_ascii=False, separators=(",", ":")
                )
            return
        clean = sanitize_payload(payload)
        self._events.append(
            {
                "user_id": self.user_id,
                "request_id": self.request_id,
                "event_type": event_type,
                "payload": json.dumps(clean, ensure_ascii=False, separators=(",", ":")),
                "sequence": len(self._events) + 1,
                "outcome": outcome,
                "duration_ms": duration_ms,
                "schema_version": 1,
                "created_at": datetime.now(timezone.utc),
            }
        )

    def flush(self, db: Session) -> None:
        if not self._events:
            return
        try:
            AgentEventRepository(db).add_many(self._events)
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
            logger.warning("agent_trace_write_failed request_id=%s", self.request_id)
