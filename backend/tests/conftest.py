"""pytest 全局配置：API 测试使用独立临时数据目录 + 测试邀请码。"""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="sb_test_"))
os.environ.setdefault("INVITE_CODES", "TESTCODE1,TESTCODE2")
os.environ.setdefault("AUTH_SECRET", "test-secret")

from app.main import app  # noqa: E402


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    c = TestClient(app)
    r = c.post("/api/v1/auth/login", json={"code": "TESTCODE1"})
    assert r.status_code == 200
    return {"Authorization": "Bearer " + r.json()["token"]}
