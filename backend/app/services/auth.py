"""账号注册、登录、会话吊销和可控的旧令牌兼容。"""

import base64
import hashlib
import hmac
import secrets
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from pwdlib import PasswordHash
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..core.config import settings
from ..db.models import User
from ..repositories.auth_sessions import AuthSessionRepository
from ..repositories.invites import InviteRepository
from ..repositories.users import UserRepository

password_hash = PasswordHash.recommended()
_DUMMY_HASH = password_hash.hash("not-a-real-password-123")


@dataclass
class AccountError(Exception):
    code: str
    message: str

    def __str__(self) -> str:
        return self.message


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_username(username: str) -> str:
    return unicodedata.normalize("NFKC", username or "").strip().casefold()


def validate_username(username: str) -> tuple[str, str]:
    display = unicodedata.normalize("NFKC", username or "").strip()
    normalized = display.casefold()
    if not 3 <= len(display) <= 32:
        raise AccountError("INVALID_USERNAME", "用户名需要 3 到 32 个字符")
    if not all(ch.isalnum() or ch in "_-." for ch in display):
        raise AccountError("INVALID_USERNAME", "用户名只能包含文字、数字、下划线、短横线或点")
    return display, normalized


def validate_password(password: str) -> None:
    if not 8 <= len(password or "") <= 128:
        raise AccountError("INVALID_PASSWORD", "密码需要 8 到 128 个字符")
    if not any(ch.isalpha() for ch in password) or not any(
        ch.isdigit() for ch in password
    ):
        raise AccountError("INVALID_PASSWORD", "密码必须同时包含字母和数字")


def invite_digest(code: str) -> str:
    return hmac.new(
        settings.invite_code_pepper.encode("utf-8"),
        (code or "").strip().encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _issue_session(db: Session, user_id: str, *, now: datetime) -> str:
    token = secrets.token_urlsafe(32)
    AuthSessionRepository(db).create(
        session_id=str(uuid4()),
        user_id=user_id,
        token_hash=token_digest(token),
        expires_at=now + timedelta(seconds=settings.auth_token_ttl_seconds),
        now=now,
    )
    return token


def create_invite(
    db: Session,
    code: str,
    *,
    max_uses: int | None = 1,
    expires_at: datetime | None = None,
) -> str:
    code = (code or "").strip()
    if len(code) < 6:
        raise AccountError("INVALID_INVITE", "邀请码至少需要 6 个字符")
    if max_uses is not None and max_uses < 1:
        raise AccountError("INVALID_INVITE", "可使用次数必须大于 0")
    invite_id = str(uuid4())
    try:
        InviteRepository(db).create(
            invite_id=invite_id,
            digest=invite_digest(code),
            max_uses=max_uses,
            expires_at=expires_at,
            now=utcnow(),
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AccountError("INVITE_EXISTS", "邀请码已存在") from exc
    return invite_id


def register(db: Session, invite_code: str, username: str, password: str) -> dict:
    display, normalized = validate_username(username)
    validate_password(password)
    now = utcnow()
    invites = InviteRepository(db)
    invite = invites.get_by_digest(invite_digest(invite_code))
    if invite is None or not invites.consume(invite.id, now=now):
        db.rollback()
        raise AccountError("INVALID_INVITE", "邀请码无效、已过期或已用完")

    user_id = str(uuid4())
    try:
        UserRepository(db).create(
            user_id=user_id,
            username=display,
            username_normalized=normalized,
            password_hash=password_hash.hash(password),
            timezone_name=settings.app_timezone,
            status="active",
            now=now,
        )
        invites.add_redemption(
            redemption_id=str(uuid4()),
            invite_id=invite.id,
            user_id=user_id,
            now=now,
        )
        token = _issue_session(db, user_id, now=now)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AccountError("USERNAME_TAKEN", "用户名已被使用") from exc
    return {"token": token, "user_id": user_id}


def demo_login(db: Session, invite_code: str) -> dict:
    """验证体验邀请码，并为本次进入创建独立的临时账号。"""
    now = utcnow()
    invite = InviteRepository(db).get_by_digest(invite_digest(invite_code))
    if invite is None or invite.disabled_at is not None or (invite.expires_at and invite.expires_at < now):
        raise AccountError("INVALID_INVITE", "体验邀请码无效或已过期")
    username = f"体验用户-{uuid4().hex[:10]}"
    normalized = normalize_username(username)
    user_id = str(uuid4())
    UserRepository(db).create(
        user_id=user_id,
        username=username,
        username_normalized=normalized,
        password_hash=password_hash.hash(secrets.token_urlsafe(24)),
        timezone_name=settings.app_timezone,
        status="active",
        now=now,
    )
    token = _issue_session(db, user_id, now=now)
    db.commit()
    return {"token": token, "user_id": user_id}


def login(db: Session, username: str, password: str) -> dict:
    normalized = normalize_username(username)
    user = UserRepository(db).get_by_username(normalized)
    stored_hash = user.password_hash if user and user.password_hash else _DUMMY_HASH
    try:
        password_ok = password_hash.verify(password or "", stored_hash)
    except Exception:  # noqa: BLE001 —— 损坏的历史哈希也按登录失败处理
        password_ok = False
    if not user or user.status != "active" or not password_ok:
        db.rollback()
        raise AccountError("INVALID_CREDENTIALS", "用户名或密码错误")

    token = _issue_session(db, user.id, now=utcnow())
    db.commit()
    return {"token": token, "user_id": user.id}


def verify(db: Session, token: str) -> User | None:
    if not token:
        return None
    return AuthSessionRepository(db).active_user(token_digest(token), now=utcnow())


def logout(db: Session, token: str) -> bool:
    revoked = AuthSessionRepository(db).revoke(token_digest(token), now=utcnow())
    db.commit()
    return revoked


def claim_legacy_account(
    db: Session, legacy_token: str, username: str, password: str
) -> dict:
    if not settings.allow_legacy_tokens:
        raise AccountError("LEGACY_CLAIM_DISABLED", "旧账号认领功能当前未开启")
    legacy_key = verify_legacy_token(legacy_token)
    if not legacy_key:
        raise AccountError("INVALID_LEGACY_TOKEN", "旧登录凭证无效或已过期")
    display, normalized = validate_username(username)
    validate_password(password)
    user = UserRepository(db).get_by_legacy_key(legacy_key)
    if not user or user.status != "legacy_unclaimed":
        raise AccountError("LEGACY_ACCOUNT_NOT_FOUND", "没有可认领的旧账号")
    user.username = display
    user.username_normalized = normalized
    user.password_hash = password_hash.hash(password)
    user.status = "active"
    user.updated_at = utcnow()
    try:
        token = _issue_session(db, user.id, now=user.updated_at)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AccountError("USERNAME_TAKEN", "用户名已被使用") from exc
    return {"token": token, "user_id": user.id}


def _sign(payload: str) -> str:
    return hmac.new(
        settings.auth_secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()


def verify_legacy_token(token: str) -> str | None:
    """仅用于显式开启的迁移窗口，验证旧版签名 token。"""
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
