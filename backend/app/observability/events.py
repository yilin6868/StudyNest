"""Agent 轨迹事件白名单。"""

from typing import Literal, get_args

EventType = Literal[
    "agent.request.started",
    "safety.input.classified",
    "memory.context.loaded",
    "model.call.completed",
    "tool.permission.evaluated",
    "tool.call.completed",
    "agent.action.issued",
    "agent.action.resolved",
    "tts.call.completed",
    "memory.changed",
    "agent.fallback.used",
    "output_guard.blocked",
    "agent.request.completed",
    "focus.started",
    "focus.halfway_shown",
    "focus.completed",
    "focus.completion_failed",
    "companion.preference_changed",
    "companion.reminder_shown",
    "companion.reminder_dismissed",
    "summary.viewed",
    "data.export.requested",
    "data.export.completed",
    "data.deletion.requested",
    "account.deletion.requested",
]

EVENT_TYPES = frozenset(get_args(EventType))
OUTCOMES = frozenset({"started", "succeeded", "failed", "blocked", "fallback"})
