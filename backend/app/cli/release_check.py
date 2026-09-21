"""上线前后端环境检查：只输出配置项名，不回显密钥或连接串。"""

from __future__ import annotations

from collections.abc import Callable

from ..core.config import ConfigError, Settings, settings
from ..db.session import database_ready


def release_errors(
    value: Settings, *, ready_check: Callable[[], bool]
) -> list[str]:
    errors: list[str] = []
    try:
        value.validate()
    except ConfigError as exc:
        errors.append(str(exc))

    if value.app_env != "production":
        errors.append("APP_ENV 必须设为 production")
    if not value.database_url.startswith("postgresql+psycopg://"):
        errors.append("生产 DATABASE_URL 必须使用 postgresql+psycopg")
    if not ready_check():
        errors.append("数据库不可用或 Alembic 版本未升级到 head")
    return list(dict.fromkeys(errors))


def main() -> int:
    errors = release_errors(settings, ready_check=database_ready)
    if errors:
        print("生产发布检查未通过：")
        for error in errors:
            print(f"- {error}")
        return 1
    print("生产发布检查通过：配置、PostgreSQL 和数据库版本均就绪。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
