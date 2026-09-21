"""长期学习记忆的公开协议。"""

from datetime import datetime
from typing import Literal

from pydantic import Field

from ..agent.contracts import ContractModel

MemoryCategory = Literal[
    "study_routine", "learning_preference", "companionship_style"
]


class MemoryBody(ContractModel):
    content: str = Field(min_length=1, max_length=120)


class MemoryItem(ContractModel):
    category: MemoryCategory
    content: str = Field(min_length=1, max_length=120)
    updated_at: datetime


class MemoryList(ContractModel):
    memories: list[MemoryItem] = Field(default_factory=list, max_length=3)

