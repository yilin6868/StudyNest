import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app
from app.db.session import SessionLocal
from app.agent.confirmations import ConfirmationService
from app.agent.contracts import PendingStartFocusAction
from app.services import chat as chat_service
from app.services import auth

client = TestClient(app)


@pytest.fixture(autouse=True)
def no_real_key(monkeypatch):
    # 确保 API 测试不触发真实模型调用
    monkeypatch.setattr(chat_service.settings, "llm_api_key", "")


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "service": "studynest-api"}


def test_ready_checks_database_revision():
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "ready", "database": True}


def test_login_success():
    username = f"api_{uuid4().hex[:12]}"
    registered = client.post(
        "/api/v1/auth/register",
        json={"inviteCode": "TESTCODE1", "username": username, "password": "Password123"},
    )
    assert registered.status_code == 200
    r = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "Password123"},
    )
    assert r.status_code == 200
    assert r.json()["token"]
    assert r.json()["user_id"]


def test_login_invalid_credentials_rejected():
    r = client.post(
        "/api/v1/auth/login",
        json={"username": "missing", "password": "WrongPassword9"},
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_register_invalid_invite_rejected():
    r = client.post(
        "/api/v1/auth/register",
        json={"inviteCode": "WRONG", "username": "new_user", "password": "Password123"},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_INVITE"


def test_legacy_claim_is_closed_by_default():
    r = client.post(
        "/api/v1/auth/legacy-claim",
        json={
            "legacyToken": "old-token",
            "username": "legacy_user",
            "password": "Password123",
        },
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "LEGACY_CLAIM_DISABLED"


def test_session_returns_authenticated_user(auth_headers):
    r = client.get("/api/v1/auth/session", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["authenticated"] is True
    assert r.json()["userId"]


def test_logout_revokes_current_token(auth_headers):
    assert client.post("/api/v1/auth/logout", headers=auth_headers).status_code == 204
    r = client.get("/api/v1/auth/session", headers=auth_headers)
    assert r.status_code == 401


def test_requires_auth():
    r = client.get("/api/v1/stats")
    assert r.status_code == 401


def test_agent_confirmation_and_summary_require_auth():
    confirm = client.post(
        "/api/v1/agent/actions/resolve",
        json={
            "protocolVersion": "1.1",
            "confirmationToken": "x" * 32,
            "decision": "confirm",
        },
    )
    summary = client.post(
        "/api/v1/agent/focus-summary",
        json={"sessionId": str(uuid4())},
    )
    assert confirm.status_code == 401
    assert summary.status_code == 401


def test_agent_confirmation_endpoint_returns_only_stored_action(auth_headers):
    session = client.get("/api/v1/auth/session", headers=auth_headers).json()
    with SessionLocal() as db:
        issued = ConfirmationService().issue(
            db,
            user_id=session["userId"],
            request_id=f"req_{uuid4().hex}",
            action=PendingStartFocusAction(duration_minutes=35),
        )
        db.commit()
        token = issued.confirmation_token
    result = client.post(
        "/api/v1/agent/actions/resolve",
        json={
            "protocolVersion": "1.1",
            "confirmationToken": token,
            "decision": "confirm",
        },
        headers=auth_headers,
    )
    assert result.status_code == 200
    assert result.json()["action"] == {
        "type": "start_focus",
        "durationMinutes": 35,
    }
    repeated = client.post(
        "/api/v1/agent/actions/resolve",
        json={
            "protocolVersion": "1.1",
            "confirmationToken": token,
            "decision": "confirm",
        },
        headers=auth_headers,
    )
    assert repeated.status_code == 409


def test_focus_summary_reads_real_completed_session(auth_headers):
    session_id = str(uuid4())
    completed = client.post(
        "/api/v1/stats/complete",
        json={"sessionId": session_id, "minutes": 17},
        headers=auth_headers,
    )
    assert completed.status_code == 200
    summary = client.post(
        "/api/v1/agent/focus-summary",
        json={"sessionId": session_id},
        headers=auth_headers,
    )
    assert summary.status_code == 200
    assert summary.json()["source"] == "local"
    assert "17" in summary.json()["reply"]
    missing = client.post(
        "/api/v1/agent/focus-summary",
        json={"sessionId": str(uuid4())},
        headers=auth_headers,
    )
    assert missing.status_code == 404


def test_get_stats(auth_headers):
    r = client.get("/api/v1/stats", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["tomato"] >= 0
    assert "weekDays" in data


def test_complete_tomato(auth_headers):
    r = client.post(
        "/api/v1/stats/complete",
        json={"sessionId": str(uuid4()), "minutes": 25},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["tomato"] >= 1


def test_complete_tomato_is_idempotent(auth_headers):
    before = client.get("/api/v1/stats", headers=auth_headers).json()
    body = {"sessionId": str(uuid4()), "minutes": 25}
    first = client.post("/api/v1/stats/complete", json=body, headers=auth_headers)
    second = client.post("/api/v1/stats/complete", json=body, headers=auth_headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert second.json()["tomato"] == before["tomato"] + 1


def test_complete_requires_valid_session_id(auth_headers):
    r = client.post(
        "/api/v1/stats/complete",
        json={"sessionId": "not-a-uuid", "minutes": 25},
        headers=auth_headers,
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_goal_roundtrip(auth_headers):
    r = client.put("/api/v1/goal", json={"text": "背 50 个单词"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["text"] == "背 50 个单词"
    r2 = client.get("/api/v1/goal", headers=auth_headers)
    assert r2.json()["text"] == "背 50 个单词"


def test_goal_too_long_rejected(auth_headers):
    r = client.put("/api/v1/goal", json={"text": "x" * 61}, headers=auth_headers)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_chat_without_key_returns_local(auth_headers):
    r = client.post("/api/v1/chat", json={"message": "求鼓励"}, headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["source"] == "local"
    assert data["reply"]


def test_chat_empty_message_rejected(auth_headers):
    r = client.post("/api/v1/chat", json={"message": ""}, headers=auth_headers)
    assert r.status_code == 422


def test_encourage_scene(auth_headers):
    r = client.post("/api/v1/encourage", json={"scene": "celebrate"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["reply"]


def test_encourage_invalid_scene_rejected(auth_headers):
    r = client.post("/api/v1/encourage", json={"scene": "bad"}, headers=auth_headers)
    assert r.status_code == 422


def test_data_isolation_between_users():
    """不同用户的数据隔离：用户 A 的番茄数不影响用户 B。"""
    shared_session_id = str(uuid4())
    shared_invite = f"SHARED-{uuid4().hex}"
    with SessionLocal() as db:
        auth.create_invite(db, shared_invite, max_uses=2)
    user_a = client.post(
        "/api/v1/auth/register",
        json={
            "inviteCode": shared_invite,
            "username": f"shared_a_{uuid4().hex[:8]}",
            "password": "Password123",
        },
    )
    user_b = client.post(
        "/api/v1/auth/register",
        json={
            "inviteCode": shared_invite,
            "username": f"user_b_{uuid4().hex[:10]}",
            "password": "Password123",
        },
    )
    assert user_a.status_code == user_b.status_code == 200
    headers_a = {"Authorization": "Bearer " + user_a.json()["token"]}
    token_b = user_b.json()["token"]
    headers_b = {"Authorization": "Bearer " + token_b}
    client.post(
        "/api/v1/stats/complete",
        json={"sessionId": shared_session_id, "minutes": 25},
        headers=headers_a,
    )
    complete_b = client.post(
        "/api/v1/stats/complete",
        json={"sessionId": shared_session_id, "minutes": 25},
        headers=headers_b,
    )
    assert complete_b.status_code == 200
    stats_a = client.get("/api/v1/stats", headers=headers_a).json()
    stats_b = client.get("/api/v1/stats", headers=headers_b).json()
    assert stats_a["tomato"] == 1
    assert stats_b["tomato"] == 1
