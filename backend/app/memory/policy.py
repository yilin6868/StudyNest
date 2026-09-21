"""长期记忆白名单和敏感内容拒绝。"""

from __future__ import annotations

import re

ALLOWED_CATEGORIES = frozenset(
    {"study_routine", "learning_preference", "companionship_style"}
)

_SENSITIVE_PATTERNS = (
    re.compile(r"自杀|自残|自伤|不想活|结束生命"),
    re.compile(r"抑郁症|诊断|用药|药物|病史|住院"),
    re.compile(r"密码|token|api\s*key|邀请码|银行卡|身份证", re.I),
    re.compile(r"手机号|微信号|邮箱|详细地址|家庭住址"),
    re.compile(r"收入|债务|宗教|政治|性取向"),
)
_TEMPORARY_EMOTION = re.compile(r"今天.*(?:累|焦虑|难过|生气|崩溃)|现在.*(?:累|焦虑|难过|生气)")


class MemoryPolicyError(ValueError):
    pass


def validate_memory(category: str, content: str) -> str:
    normalized = " ".join(content.strip().split())
    if category not in ALLOWED_CATEGORIES:
        raise MemoryPolicyError("只能保存学习习惯、学习偏好或陪伴风格")
    if not 1 <= len(normalized) <= 120:
        raise MemoryPolicyError("记忆内容需要在 1 到 120 个字之间")
    if _TEMPORARY_EMOTION.search(normalized) or any(
        pattern.search(normalized) for pattern in _SENSITIVE_PATTERNS
    ):
        raise MemoryPolicyError("这类内容不会保存为长期记忆")
    return normalized

