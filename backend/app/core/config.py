"""应用配置：从环境变量或 ``backend/.env`` 读取并在启动时校验。"""

from __future__ import annotations

import os
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv

_BASE_DIR = Path(__file__).resolve().parents[2]
_ALLOWED_ENVIRONMENTS = {"development", "test", "demo", "production"}
_INSECURE_AUTH_SECRETS = {"", "dev-secret-change-me", "change-me", "test-secret"}

load_dotenv(_BASE_DIR / ".env")


class ConfigError(ValueError):
    """配置不完整或格式错误。"""


def _get(key: str, default: str = "") -> str:
    return (os.getenv(key) or default).strip()


def _get_float(key: str, default: float, *, minimum: float, maximum: float) -> float:
    raw = _get(key, str(default))
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(f"{key} 必须是数字") from exc
    if not minimum <= value <= maximum:
        raise ConfigError(f"{key} 必须在 {minimum} 到 {maximum} 之间")
    return value


def _get_int(key: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = _get(key, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{key} 必须是整数") from exc
    if not minimum <= value <= maximum:
        raise ConfigError(f"{key} 必须在 {minimum} 到 {maximum} 之间")
    return value


class Settings:
    """一次性读取当前进程配置，便于启动校验和单元测试。"""

    def __init__(self) -> None:
        # veFaaS 会自行注入 APP_ENV；应用专用变量必须优先于平台值。
        self.app_env = _get("STUDYNEST_APP_ENV", _get("APP_ENV", "development")).lower()
        self.app_timezone = _get("APP_TIMEZONE", "Asia/Shanghai")

        self.llm_base_url = _get(
            "LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"
        )
        self.llm_api_key = _get("LLM_API_KEY", "")
        self.llm_model = _get("LLM_MODEL", "glm-4-flash")
        self.llm_temperature = _get_float(
            "LLM_TEMPERATURE", 0.8, minimum=0.0, maximum=2.0
        )
        self.llm_max_tokens = _get_int(
            "LLM_MAX_TOKENS", 300, minimum=1, maximum=32768
        )
        self.agent_max_model_turns = _get_int(
            "AGENT_MAX_MODEL_TURNS", 4, minimum=1, maximum=6
        )
        self.agent_max_tool_calls = _get_int(
            "AGENT_MAX_TOOL_CALLS", 3, minimum=0, maximum=5
        )
        self.agent_model_timeout_seconds = _get_float(
            "AGENT_MODEL_TIMEOUT_SECONDS", 10.0, minimum=3.0, maximum=20.0
        )
        self.agent_total_timeout_seconds = _get_float(
            "AGENT_TOTAL_TIMEOUT_SECONDS", 25.0, minimum=5.0, maximum=60.0
        )
        self.agent_action_ttl_seconds = _get_int(
            "AGENT_ACTION_TTL_SECONDS", 300, minimum=30, maximum=900
        )
        self.chat_recent_message_limit = _get_int(
            "CHAT_RECENT_MESSAGE_LIMIT", 8, minimum=2, maximum=20
        )
        self.chat_page_message_limit = _get_int(
            "CHAT_PAGE_MESSAGE_LIMIT", 50, minimum=10, maximum=100
        )
        self.chat_session_list_limit = _get_int(
            "CHAT_SESSION_LIST_LIMIT", 20, minimum=5, maximum=50
        )
        self.chat_summary_trigger_count = _get_int(
            "CHAT_SUMMARY_TRIGGER_COUNT", 20, minimum=10, maximum=100
        )
        self.chat_summary_trigger_chars = _get_int(
            "CHAT_SUMMARY_TRIGGER_CHARS", 4000, minimum=1000, maximum=20000
        )
        self.chat_summary_max_chars = _get_int(
            "CHAT_SUMMARY_MAX_CHARS", 1200, minimum=200, maximum=2000
        )
        self.agent_context_max_bytes = _get_int(
            "AGENT_CONTEXT_MAX_BYTES", 16384, minimum=4096, maximum=65536
        )
        self.user_memory_max_chars = _get_int(
            "USER_MEMORY_MAX_CHARS", 120, minimum=40, maximum=120
        )
        self.agent_trace_max_events = _get_int(
            "AGENT_TRACE_MAX_EVENTS", 50, minimum=10, maximum=100
        )
        self.agent_event_retention_days = _get_int(
            "AGENT_EVENT_RETENTION_DAYS", 30, minimum=1, maximum=365
        )
        self.chat_retention_days = _get_int(
            "CHAT_RETENTION_DAYS", 30, minimum=1, maximum=365
        )
        self.log_pseudonym_secret = _get(
            "LOG_PSEUDONYM_SECRET", "dev-log-pseudonym-change-me"
        )

        data_dir = Path(_get("DATA_DIR", "./data"))
        self.data_dir = (
            data_dir if data_dir.is_absolute() else (_BASE_DIR / data_dir).resolve()
        )

        self.auth_secret = _get("AUTH_SECRET", "dev-secret-change-me")
        self.invite_code_pepper = _get(
            "INVITE_CODE_PEPPER", "dev-invite-pepper-change-me"
        )
        self.demo_invite_code = _get("DEMO_INVITE_CODE")
        self.auth_token_ttl_seconds = _get_int(
            "AUTH_TOKEN_TTL_SECONDS",
            30 * 24 * 3600,
            minimum=300,
            maximum=31536000,
        )
        self.allow_legacy_tokens = _get("ALLOW_LEGACY_TOKENS", "false").lower() in {
            "1",
            "true",
            "yes",
        }
        self.storage_backend = _get("STORAGE_BACKEND", "database").lower()
        default_database = f"sqlite+pysqlite:///{self.data_dir / 'study_buddy.db'}"
        self.database_url = _get("DATABASE_URL", default_database)
        self.database_pool_size = _get_int(
            "DATABASE_POOL_SIZE", 5, minimum=1, maximum=50
        )
        self.database_pool_timeout = _get_int(
            "DATABASE_POOL_TIMEOUT", 10, minimum=1, maximum=120
        )

    def validate(self) -> list[str]:
        """校验启动条件，并返回不含敏感值的开发环境提醒。"""
        if self.app_env not in _ALLOWED_ENVIRONMENTS:
            raise ConfigError(
                f"APP_ENV={self.app_env!r} 无效；只能是 development、test、demo 或 production"
            )

        try:
            ZoneInfo(self.app_timezone)
        except ZoneInfoNotFoundError as exc:
            raise ConfigError("APP_TIMEZONE 不是有效时区") from exc

        warnings: list[str] = []
        if self.storage_backend not in {"database", "json", "compare"}:
            raise ConfigError("STORAGE_BACKEND 只能是 database、json 或 compare")

        if not self.database_url:
            raise ConfigError("必须配置 DATABASE_URL")
        if self.app_env == "production" and self.database_url.startswith("sqlite"):
            raise ConfigError("生产环境不能使用 SQLite")
        if self.app_env == "demo":
            if not self.database_url.startswith("sqlite"):
                raise ConfigError("演示环境必须使用临时 SQLite")
            if len(self.demo_invite_code) < 6:
                raise ConfigError("演示环境必须配置至少 6 位的 DEMO_INVITE_CODE")

        if self.auth_secret in _INSECURE_AUTH_SECRETS:
            if self.app_env in {"demo", "production"}:
                raise ConfigError("演示或生产环境必须配置安全的 AUTH_SECRET")
            warnings.append("当前 AUTH_SECRET 仅适合本地开发或自动测试")

        if self.invite_code_pepper in {"", "dev-invite-pepper-change-me", "change-me"}:
            if self.app_env in {"demo", "production"}:
                raise ConfigError("演示或生产环境必须配置安全的邀请码摘要密钥")
            warnings.append("当前邀请码摘要密钥仅适合本地开发或自动测试")

        if self.log_pseudonym_secret in {
            "",
            "dev-log-pseudonym-change-me",
            "change-me",
        }:
            if self.app_env in {"demo", "production"}:
                raise ConfigError("演示或生产环境必须配置独立的日志匿名密钥")
            warnings.append("当前日志匿名密钥仅适合本地开发或自动测试")

        return warnings


settings = Settings()
