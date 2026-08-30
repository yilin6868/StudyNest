import pytest

from app.services import chat as chat_service
from app.services.phrases import PHRASES


class _FakeClient:
    """模拟 httpx.AsyncClient，post 返回固定响应。"""
    def __init__(self, status_code, content):
        self._status = status_code
        self._content = content
        self.calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, *args, **kwargs):
        self.calls += 1
        return _FakeResp(self._status, self._content)


class _FakeResp:
    def __init__(self, status_code, content):
        self.status_code = status_code
        self._content = content

    def json(self):
        return self._content


@pytest.mark.asyncio
async def test_no_key_returns_local(monkeypatch):
    monkeypatch.setattr(chat_service.settings, "llm_api_key", "")
    reply, source = await chat_service.chat("求鼓励")
    assert source == "local"
    assert reply in PHRASES["encourage"]


@pytest.mark.asyncio
async def test_http_error_falls_back(monkeypatch):
    monkeypatch.setattr(chat_service.settings, "llm_api_key", "sk-test")
    fake = _FakeClient(500, {"error": "boom"})
    monkeypatch.setattr(chat_service.httpx, "AsyncClient", lambda *a, **k: fake)
    reply, source = await chat_service.chat("求鼓励")
    assert source == "local"
    assert reply in PHRASES["encourage"]


@pytest.mark.asyncio
async def test_empty_content_falls_back_after_retry(monkeypatch):
    monkeypatch.setattr(chat_service.settings, "llm_api_key", "sk-test")
    fake = _FakeClient(200, {"choices": [{"message": {"content": ""}}]})
    monkeypatch.setattr(chat_service.httpx, "AsyncClient", lambda *a, **k: fake)
    reply, source = await chat_service.chat("你好")
    assert source == "local"
    assert fake.calls == chat_service.MAX_ATTEMPTS  # 有限重试


@pytest.mark.asyncio
async def test_model_success(monkeypatch):
    monkeypatch.setattr(chat_service.settings, "llm_api_key", "sk-test")
    fake = _FakeClient(200, {"choices": [{"message": {"content": "你好呀！加油 🦉"}}]})
    monkeypatch.setattr(chat_service.httpx, "AsyncClient", lambda *a, **k: fake)
    reply, source = await chat_service.chat("你好")
    assert source == "llm"
    assert reply == "你好呀！加油 🦉"


@pytest.mark.asyncio
async def test_client_construction_error_falls_back(monkeypatch):
    """客户端构造阶段就抛错（如无 Key）也必须在最外层兜底。"""
    monkeypatch.setattr(chat_service.settings, "llm_api_key", "sk-test")

    class _Boom:
        def __init__(self, *a, **k):
            raise RuntimeError("boom")

    monkeypatch.setattr(chat_service.httpx, "AsyncClient", _Boom)
    reply, source = await chat_service.chat("求鼓励")
    assert source == "local"
    assert reply in PHRASES["encourage"]
