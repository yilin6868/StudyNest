import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def fake_synth(monkeypatch):
    async def _fake(text, gender=None):
        return b"ID3fake-mp3"
    monkeypatch.setattr(routes, "synthesize", _fake)


def test_tts_returns_audio(auth_headers):
    r = client.post("/api/v1/tts", json={"text": "你好呀", "gender": "female"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/mpeg"
    assert r.content == b"ID3fake-mp3"


def test_tts_empty_text_rejected(auth_headers):
    r = client.post("/api/v1/tts", json={"text": ""}, headers=auth_headers)
    assert r.status_code == 422


def test_tts_invalid_gender_rejected(auth_headers):
    r = client.post("/api/v1/tts", json={"text": "你好", "gender": "xxx"}, headers=auth_headers)
    assert r.status_code == 422


def test_tts_failure_returns_204(auth_headers, monkeypatch):
    async def _boom(text, gender=None):
        raise RuntimeError("boom")
    monkeypatch.setattr(routes, "synthesize", _boom)
    r = client.post("/api/v1/tts", json={"text": "你好"}, headers=auth_headers)
    assert r.status_code == 204
