"""配置解析和生产启动底线测试。"""

import pytest

from app.core.config import ConfigError, Settings


def _valid_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("APP_TIMEZONE", "Asia/Shanghai")
    monkeypatch.setenv("INVITE_CODES", "TESTCODE")
    monkeypatch.setenv("AUTH_SECRET", "test-secret")
    monkeypatch.setenv("INVITE_CODE_PEPPER", "test-invite-pepper")
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:////tmp/study-buddy-test.sqlite3")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.8")
    monkeypatch.setenv("LLM_MAX_TOKENS", "300")
    monkeypatch.setenv("LOG_PSEUDONYM_SECRET", "test-log-pseudonym-secret")


def test_valid_test_configuration(monkeypatch):
    _valid_environment(monkeypatch)
    assert Settings().validate() == ["当前 AUTH_SECRET 仅适合本地开发或自动测试"]


def test_invalid_temperature_is_rejected(monkeypatch):
    _valid_environment(monkeypatch)
    monkeypatch.setenv("LLM_TEMPERATURE", "not-a-number")
    with pytest.raises(ConfigError, match="LLM_TEMPERATURE 必须是数字"):
        Settings()


def test_invalid_timezone_is_rejected(monkeypatch):
    _valid_environment(monkeypatch)
    monkeypatch.setenv("APP_TIMEZONE", "Mars/Olympus")
    with pytest.raises(ConfigError, match="APP_TIMEZONE 不是有效时区"):
        Settings().validate()


def test_production_rejects_default_secret(monkeypatch):
    _valid_environment(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost/db")
    monkeypatch.setenv("AUTH_SECRET", "dev-secret-change-me")
    with pytest.raises(ConfigError, match="生产环境必须配置安全的 AUTH_SECRET"):
        Settings().validate()


def test_invite_codes_environment_is_no_longer_required(monkeypatch):
    _valid_environment(monkeypatch)
    monkeypatch.setenv("INVITE_CODES", "")
    assert Settings().validate() == ["当前 AUTH_SECRET 仅适合本地开发或自动测试"]


def test_production_rejects_sqlite(monkeypatch):
    _valid_environment(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_SECRET", "production-secret-long-enough")
    monkeypatch.setenv("INVITE_CODE_PEPPER", "production-invite-pepper")
    with pytest.raises(ConfigError, match="生产环境不能使用 SQLite"):
        Settings().validate()


def test_demo_requires_invite_and_strong_secrets(monkeypatch):
    _valid_environment(monkeypatch)
    monkeypatch.setenv("APP_ENV", "demo")
    monkeypatch.delenv("DEMO_INVITE_CODE", raising=False)
    with pytest.raises(ConfigError, match="DEMO_INVITE_CODE"):
        Settings().validate()

    monkeypatch.setenv("DEMO_INVITE_CODE", "TESTCODE1")
    with pytest.raises(ConfigError, match="AUTH_SECRET"):
        Settings().validate()

    monkeypatch.setenv("AUTH_SECRET", "a-long-random-demo-secret")
    assert Settings().validate() == []


def test_app_environment_prefers_project_specific_setting(monkeypatch):
    _valid_environment(monkeypatch)
    monkeypatch.setenv("APP_ENV", "volcengine_cnbeijingprod_new")
    monkeypatch.setenv("STUDYNEST_APP_ENV", "demo")
    monkeypatch.setenv("DEMO_INVITE_CODE", "TESTCODE1")
    monkeypatch.setenv("AUTH_SECRET", "a-long-random-demo-secret")
    assert Settings().app_env == "demo"
    assert Settings().validate() == []
