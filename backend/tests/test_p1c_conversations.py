from uuid import uuid4

from app.db.session import SessionLocal
from app.services import auth


def _register(client, code: str) -> dict[str, str]:
    result = client.post(
        "/api/v1/auth/register",
        json={
            "inviteCode": code,
            "username": f"conversation_{uuid4().hex[:12]}",
            "password": "Password123",
        },
    )
    assert result.status_code == 200
    return {"Authorization": "Bearer " + result.json()["token"]}


def test_chat_creates_persistent_session_and_restores_messages(client, auth_headers):
    first = client.post(
        "/api/v1/chat",
        json={"protocolVersion": "1.2", "message": "我今天想复习英语"},
        headers=auth_headers,
    )
    assert first.status_code == 200
    body = first.json()
    assert body["protocolVersion"] == "1.2"
    assert body["responseMode"] == "normal"
    assert body["sessionId"]

    second = client.post(
        "/api/v1/chat",
        json={
            "protocolVersion": "1.2",
            "sessionId": body["sessionId"],
            "message": "那我先做哪一步？",
        },
        headers=auth_headers,
    )
    assert second.status_code == 200
    restored = client.get(
        f"/api/v1/chat/sessions/{body['sessionId']}/messages",
        headers=auth_headers,
    )
    assert restored.status_code == 200
    messages = restored.json()["messages"]
    assert [item["role"] for item in messages] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert all("confirmationToken" not in item["content"] for item in messages)


def test_conversation_is_private_and_delete_removes_it(client, auth_headers):
    created = client.post(
        "/api/v1/chat/sessions", headers=auth_headers
    ).json()["sessionId"]
    with SessionLocal() as db:
        code = f"CONVERSATION-{uuid4().hex}"
        auth.create_invite(db, code, max_uses=1)
    other_headers = _register(client, code)

    assert (
        client.get(
            f"/api/v1/chat/sessions/{created}/messages", headers=other_headers
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/api/v1/chat/sessions/{created}", headers=other_headers
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/api/v1/chat/sessions/{created}", headers=auth_headers
        ).status_code
        == 204
    )
    assert (
        client.get(
            f"/api/v1/chat/sessions/{created}/messages", headers=auth_headers
        ).status_code
        == 404
    )


def test_unknown_or_cross_user_session_cannot_continue(client, auth_headers):
    response = client.post(
        "/api/v1/chat",
        json={
            "protocolVersion": "1.2",
            "sessionId": str(uuid4()),
            "message": "继续",
        },
        headers=auth_headers,
    )
    assert response.status_code == 404

