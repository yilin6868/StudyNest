from uuid import uuid4
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.db.models import AuthSession, InviteCode, User
from app.db.session import SessionLocal
from app.repositories.invites import InviteRepository
from app.services import auth


def _register(db, invite="TESTCODE1"):
    username = f"auth_{uuid4().hex[:12]}"
    return username, auth.register(db, invite, username, "Password123")


def test_register_then_login_and_verify():
    with SessionLocal() as db:
        username, registered = _register(db)
        user = auth.verify(db, registered["token"])
        assert user is not None
        assert user.id == registered["user_id"]
        logged_in = auth.login(db, username.upper(), "Password123")
        assert logged_in["user_id"] == registered["user_id"]


def test_tampered_token_is_rejected():
    with SessionLocal() as db:
        _, result = _register(db)
        assert auth.verify(db, result["token"] + "tampered") is None


def test_logout_revokes_token():
    with SessionLocal() as db:
        _, result = _register(db)
        assert auth.logout(db, result["token"]) is True
        assert auth.verify(db, result["token"]) is None


def test_expired_token_is_rejected():
    with SessionLocal() as db:
        _, result = _register(db)
        session = db.scalar(
            select(AuthSession).where(
                AuthSession.token_hash == auth.token_digest(result["token"])
            )
        )
        assert session is not None
        session.expires_at = auth.utcnow() - timedelta(seconds=1)
        db.commit()
        assert auth.verify(db, result["token"]) is None


def test_wrong_password_uses_generic_error():
    with SessionLocal() as db:
        username, _ = _register(db)
        with pytest.raises(auth.AccountError, match="用户名或密码错误"):
            auth.login(db, username, "WrongPassword9")
        with pytest.raises(auth.AccountError, match="用户名或密码错误"):
            auth.login(db, "missing-user", "WrongPassword9")


def test_duplicate_username_does_not_consume_invite_permanently():
    with SessionLocal() as db:
        username, _ = _register(db)
        with pytest.raises(auth.AccountError) as error:
            auth.register(db, "TESTCODE1", username, "Password123")
        assert error.value.code == "USERNAME_TAKEN"


def test_same_invite_can_create_two_independent_accounts():
    code = f"SHARED-{uuid4().hex}"
    with SessionLocal() as db:
        auth.create_invite(db, code, max_uses=2)
        first = auth.register(db, code, f"first_{uuid4().hex[:8]}", "Password123")
        second = auth.register(db, code, f"second_{uuid4().hex[:8]}", "Password123")
        assert first["user_id"] != second["user_id"]
        with pytest.raises(auth.AccountError) as error:
            auth.register(db, code, f"third_{uuid4().hex[:8]}", "Password123")
        assert error.value.code == "INVALID_INVITE"


def test_database_does_not_store_plaintext_secrets():
    code = f"SECRET-{uuid4().hex}"
    username = f"secure_{uuid4().hex[:8]}"
    password = "PrivatePassword123"
    with SessionLocal() as db:
        auth.create_invite(db, code, max_uses=1)
        account = auth.register(db, code, username, password)
        user = db.scalar(select(User).where(User.id == account["user_id"]))
        invite = db.scalar(
            select(InviteCode).where(InviteCode.code_digest == auth.invite_digest(code))
        )
        session = db.scalar(
            select(AuthSession).where(AuthSession.user_id == account["user_id"])
        )
        assert user is not None and user.password_hash != password
        assert password not in user.password_hash
        assert invite is not None and invite.code_digest != code
        assert session is not None and session.token_hash != account["token"]


def test_disabled_invite_cannot_register():
    code = f"DISABLED-{uuid4().hex}"
    with SessionLocal() as db:
        invite_id = auth.create_invite(db, code, max_uses=2)
        assert InviteRepository(db).disable(invite_id, now=auth.utcnow()) is True
        db.commit()
        with pytest.raises(auth.AccountError) as error:
            auth.register(db, code, f"disabled_{uuid4().hex[:8]}", "Password123")
        assert error.value.code == "INVALID_INVITE"


def test_expired_invite_cannot_register():
    code = f"EXPIRED-{uuid4().hex}"
    with SessionLocal() as db:
        auth.create_invite(
            db, code, max_uses=1, expires_at=auth.utcnow() - timedelta(minutes=1)
        )
        with pytest.raises(auth.AccountError) as error:
            auth.register(db, code, f"expired_{uuid4().hex[:8]}", "Password123")
        assert error.value.code == "INVALID_INVITE"


def test_demo_logins_use_separate_accounts():
    with SessionLocal() as db:
        first = auth.demo_login(db, "TESTCODE1")
        second = auth.demo_login(db, "TESTCODE1")
    assert first["user_id"] != second["user_id"]
    assert first["token"] != second["token"]
