"""邀请码登录：邀请码换 token，token 签名验证，数据按用户隔离。

- 邀请码列表来自环境变量 INVITE_CODES（逗号分隔）。
- 每个邀请码映射到一个稳定的 user_id（邀请码的 sha256 前 16 位）。
- token 为「user_id.过期时间」+ HMAC 签名，短期有效。
"""
import base64
import hashlib
import hmac
import time

from ..core.config import settings

TOKEN_TTL = 30 * 24 * 3600  # 30 天


def _user_id(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()[:16]


def _sign(payload: str) -> str:
    return hmac.new(
        settings.auth_secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def _valid_codes() -> list[str]:
    return [c.strip() for c in settings.invite_codes.split(",") if c.strip()]


def login(code: str) -> dict | None:
    """验证邀请码，返回 {token, user_id}；无效返回 None。"""
    code = (code or "").strip()
    if not code or code not in _valid_codes():
        return None
    uid = _user_id(code)
    exp = int(time.time()) + TOKEN_TTL
    payload = f"{uid}.{exp}"
    raw = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("utf-8").rstrip("=")
    token = f"{raw}.{_sign(payload)}"
    return {"token": token, "user_id": uid}


def verify(token: str) -> str | None:
    """验证 token，返回 user_id；无效/过期返回 None。"""
    try:
        raw, sig = token.rsplit(".", 1)
        payload = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode("utf-8")
        if not hmac.compare_digest(_sign(payload), sig):
            return None
        uid, exp = payload.split(".", 1)
        if int(exp) < time.time():
            return None
        return uid
    except Exception:  # noqa: BLE001 —— 任何解析失败都视为无效
        return None
