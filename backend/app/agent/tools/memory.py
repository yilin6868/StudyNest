"""只在当前用户明确要求时写入的学习记忆工具。"""

from typing import Literal

from pydantic import BaseModel, Field

from ...memory.contracts import MemoryItem
from ...memory.service import MemoryService
from ..context import ToolExecutionContext
from ..contracts import ContractModel
from ..permissions import PermissionLevel
from ..registry import ToolDefinition


class SaveLearningMemoryInput(ContractModel):
    category: Literal[
        "study_routine", "learning_preference", "companionship_style"
    ]
    content: str = Field(min_length=1, max_length=120)


def save_learning_memory(
    raw: BaseModel, context: ToolExecutionContext
) -> MemoryItem:
    args = SaveLearningMemoryInput.model_validate(raw)
    return MemoryService().save(
        context.db,
        context.user_id,
        args.category,
        args.content,
        source="explicit_chat",
    )


MEMORY_TOOLS = (
    ToolDefinition(
        name="save_learning_memory",
        description=(
            "仅当用户当前消息明确说请记住时，保存一条白名单学习偏好"
        ),
        input_model=SaveLearningMemoryInput,
        output_model=MemoryItem,
        side_effect=True,
        permission=PermissionLevel.EXPLICIT_INTENT,
        timeout_seconds=2,
        handler=save_learning_memory,
    ),
)

