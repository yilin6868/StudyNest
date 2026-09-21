"""从当前用户原话提取最小、可验证的写操作意图。"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from .context import IntentEvidence, digest_arguments


class IntentResolver:
    def __init__(self, *, ttl_seconds: int = 60) -> None:
        self.ttl_seconds = ttl_seconds

    def resolve(
        self,
        message: str,
        *,
        user_id: str,
        request_id: str,
        now: datetime | None = None,
    ) -> dict[str, IntentEvidence]:
        now = now or datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self.ttl_seconds)
        normalized = message.strip()
        candidates: dict[str, dict] = {}

        goal = self._goal_arguments(normalized)
        if goal is not None:
            candidates["set_today_goal"] = goal

        if re.fullmatch(r"(?:请|帮我|给我)?(?:暂停|先暂停|暂停一下)(?:专注|计时)?[。！! ]*", normalized):
            candidates["request_pause_focus"] = {}

        preference = self._preference_arguments(normalized)
        if preference is not None:
            candidates["update_preference"] = preference

        memory = self._memory_arguments(normalized)
        if memory is not None:
            candidates["save_learning_memory"] = memory

        return {
            name: IntentEvidence(
                user_id=user_id,
                request_id=request_id,
                tool_name=name,
                arguments_digest=digest_arguments(arguments),
                expires_at=expires_at,
            )
            for name, arguments in candidates.items()
        }

    @staticmethod
    def _goal_arguments(message: str) -> dict | None:
        patterns = (
            r"^(?:请|帮我|给我)?(?:把)?(?:今天|今日)?(?:的)?目标(?:设置|设|改|修改)为[：:\s]*(.+?)[。！!]*$",
            r"^(?:请|帮我|给我)?(?:设置|设定|修改)(?:今天|今日)?(?:的)?目标[：:\s]*(.+?)[。！!]*$",
        )
        for pattern in patterns:
            match = re.fullmatch(pattern, message)
            if match:
                text = match.group(1).strip()
                if 1 <= len(text) <= 60:
                    return {"text": text}
        return None

    @staticmethod
    def _preference_arguments(message: str) -> dict | None:
        values: dict = {}
        if re.search(r"(?:把|将|改成|设置为).*(?:女声|女生|女性)", message):
            values["buddyGender"] = "female"
        elif re.search(r"(?:把|将|改成|设置为).*(?:男声|男生|男性)", message):
            values["buddyGender"] = "male"
        if re.search(r"(?:开启|打开|启用).*(?:语音|声音)", message):
            values["voiceEnabled"] = True
        elif re.search(r"(?:关闭|停用).*(?:语音|声音)", message):
            values["voiceEnabled"] = False
        return values or None

    @staticmethod
    def _memory_arguments(message: str) -> dict | None:
        match = re.fullmatch(
            r"^(?:请|帮我|你)?(?:帮我)?记住[：:\s]*(.+?)[。！!]*$", message
        )
        if not match:
            return None
        content = match.group(1).strip()
        if not 1 <= len(content) <= 120:
            return None
        if re.search(r"鼓励|陪伴|少说|多说|语气|安静", content):
            category = "companionship_style"
        elif re.search(r"喜欢|偏好|分钟|一轮|方式|节奏", content):
            category = "learning_preference"
        else:
            category = "study_routine"
        return {"category": category, "content": content}
