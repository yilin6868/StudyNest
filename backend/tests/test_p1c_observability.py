import json

from app.observability.recorder import TraceRecorder
from app.observability.sanitizer import pseudonymize, sanitize_payload
from app.repositories.agent_events import AgentEventRepository


def test_trace_payload_removes_content_and_control_characters(db_session, user_factory):
    user = user_factory()
    recorder = TraceRecorder("req_sanitized", user.id)
    recorder.record(
        "agent.request.started",
        outcome="started",
        message="不能保存的原文",
        token="secret-token",
        reasonCode="safe\nline",
    )
    recorder.flush(db_session)
    event = AgentEventRepository(db_session).by_request("req_sanitized")[0]
    payload = json.loads(event.payload)
    assert "message" not in payload
    assert "token" not in payload
    assert payload["reasonCode"] == "safe line"


def test_pseudonym_is_stable_and_does_not_reveal_user_id():
    first = pseudonymize("user-123", "independent-secret")
    assert first == pseudonymize("user-123", "independent-secret")
    assert first != pseudonymize("user-456", "independent-secret")
    assert "user-123" not in first


def test_sanitizer_only_keeps_safe_scalar_metadata():
    result = sanitize_payload(
        {"toolName": "get_stats", "content": "private", "count": 2}
    )
    assert result == {"toolName": "get_stats", "count": 2}
