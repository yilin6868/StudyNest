"""会话列表与消息恢复协议。"""

from datetime import datetime
from typing import Literal

from pydantic import Field

from ..agent.contracts import ContractModel


class ConversationItem(ContractModel):
    session_id: str
    title: str | None = None
    status: Literal["active", "archived"]
    updated_at: datetime


class ConversationList(ContractModel):
    sessions: list[ConversationItem] = Field(default_factory=list, max_length=20)


class ConversationCreateResponse(ContractModel):
    session_id: str


class ConversationMessageItem(ContractModel):
    role: Literal["user", "assistant", "safety_marker"]
    content: str = Field(min_length=1, max_length=500)
    created_at: datetime


class ConversationMessages(ContractModel):
    session_id: str
    messages: list[ConversationMessageItem] = Field(default_factory=list, max_length=50)

