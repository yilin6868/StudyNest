"""不发送给模型的可信工具执行上下文。"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy.orm import Session

from .contracts import FocusState


class CallSource(StrEnum):
    AGENT = "agent"
    FRONTEND = "frontend"
    SYSTEM = "system"


@dataclass(frozen=True)
class VerifiedFocusCompletion:
    session_id: UUID
    minutes: int


@dataclass(frozen=True)
class ConfirmationEvidence:
    """P1-B 可使用的服务端确认凭证载荷；P1-A 只定义可信结构。"""

    user_id: str
    request_id: str
    action_type: str
    arguments_digest: str
    token_digest: str
    nonce: str
    expires_at: datetime


def canonical_arguments(arguments: dict) -> str:
    """生成稳定参数文本，供意图和确认记录做防篡改绑定。"""
    return json.dumps(arguments, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_arguments(arguments: dict) -> str:
    return hashlib.sha256(canonical_arguments(arguments).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class IntentEvidence:
    """只由服务端根据用户原话生成，模型无法自行声明。"""

    user_id: str
    request_id: str
    tool_name: str
    arguments_digest: str
    expires_at: datetime


@dataclass
class ToolExecutionContext:
    user_id: str
    request_id: str
    source: CallSource
    db: Session
    timezone_name: str = "Asia/Shanghai"
    intent_evidence: dict[str, IntentEvidence] = field(default_factory=dict)
    focus_state: FocusState = field(default_factory=FocusState)
    confirmation_evidence: ConfirmationEvidence | None = None
    verified_focus_completion: VerifiedFocusCompletion | None = None
    tool_call_count: int = 0
    executed_side_effects: set[str] = field(default_factory=set)
