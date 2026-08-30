import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import chat as chat_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def no_real_key(monkeypatch):
    # 确保 API 测试不触发真实模型调用
    monkeypatch.setattr(chat_service.settings, "llm_api_key", "")


def test_static_index_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "自习室" in r.text


def test_login_success():
    r = client.post("/api/v1/auth/login", json={"code": "TESTCODE1"})
    assert r.status_code == 200
    assert r.json()["token"]
    assert r.json()["user_id"]


def test_login_invalid_code_rejected():
    r = client.post("/api/v1/auth/login", json={"code": "WRONG"})
    assert r.status_code == 401


def test_requires_auth():
    r = client.get("/api/v1/stats")
    assert r.status_code == 401


def test_get_stats(auth_headers):
    r = client.get("/api/v1/stats", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["tomato"] >= 0
    assert "weekDays" in data


def test_complete_tomato(auth_headers):
    r = client.post("/api/v1/stats/complete", json={"minutes": 25}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["tomato"] >= 1


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


def test_data_isolation_between_users(auth_headers):
    """不同用户的数据隔离：用户 A 的番茄数不影响用户 B。"""
    # 用户 A 完成一个番茄
    client.post("/api/v1/stats/complete", json={"minutes": 25}, headers=auth_headers)
    # 用户 B 登录
    r = client.post("/api/v1/auth/login", json={"code": "TESTCODE2"})
    token_b = r.json()["token"]
    headers_b = {"Authorization": "Bearer " + token_b}
    stats_b = client.get("/api/v1/stats", headers=headers_b).json()
    assert stats_b["tomato"] == 0
