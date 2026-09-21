"""结构化事件的去敏和日志注入防护。"""

from __future__ import annotations

import hashlib
import hmac
import re

_CONTROL = re.compile(r"[\x00-\x1f\x7f]+")
_SECRET_KEYS = re.compile(r"token|secret|password|invite|api.?key|message|reply|content", re.I)


def sanitize_scalar(value: object) -> str | int | float | bool | None:
    if value is None or isinstance(value, (int, float, bool)):
        return value
    return _CONTROL.sub(" ", str(value))[:120]


def sanitize_payload(payload: dict[str, object]) -> dict[str, object]:
    return {
        key: sanitize_scalar(value)
        for key, value in payload.items()
        if not _SECRET_KEYS.search(key)
    }


def pseudonymize(user_id: str, secret: str) -> str:
    return hmac.new(secret.encode(), user_id.encode(), hashlib.sha256).hexdigest()[:16]

