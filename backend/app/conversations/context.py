"""会话摘要、最近消息和长期记忆的固定预算。"""

from dataclasses import dataclass

from ..agent.contracts import ConversationMessage, LearningMemory


@dataclass(frozen=True)
class ConversationContext:
    summary: str
    recent_messages: list[ConversationMessage]
    memories: list[LearningMemory]


def fit_context(
    *,
    summary: str,
    recent_messages: list[ConversationMessage],
    memories: list[LearningMemory],
    max_bytes: int,
) -> ConversationContext:
    safe_summary = summary[:1200]
    safe_messages = recent_messages[-8:]
    safe_memories = memories[:3]

    def size() -> int:
        value = safe_summary + "".join(
            item.role + item.content for item in safe_messages
        ) + "".join(item.category + item.content for item in safe_memories)
        return len(value.encode("utf-8"))

    while size() > max_bytes and safe_messages:
        safe_messages.pop(0)
    while size() > max_bytes and safe_summary:
        safe_summary = safe_summary[: max(0, len(safe_summary) - 100)]
    while size() > max_bytes and safe_memories:
        safe_memories.pop()
    return ConversationContext(safe_summary, safe_messages, safe_memories)

