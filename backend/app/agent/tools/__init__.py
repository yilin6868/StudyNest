"""白名单内部学习工具。"""

from ..registry import AuditSink, ToolRegistry
from .focus import FOCUS_TOOLS
from .goals import GOAL_TOOLS
from .memory import MEMORY_TOOLS
from .preferences import PREFERENCE_TOOLS
from .stats import STATS_TOOLS


def build_default_registry(*, audit_sink: AuditSink | None = None) -> ToolRegistry:
    registry = ToolRegistry(audit_sink=audit_sink)
    for definition in (
        *GOAL_TOOLS,
        *FOCUS_TOOLS,
        *STATS_TOOLS,
        *PREFERENCE_TOOLS,
        *MEMORY_TOOLS,
    ):
        registry.register(definition)
    return registry


__all__ = ["build_default_registry"]
