from types import SimpleNamespace

from app.cli.release_check import release_errors


class FakeSettings(SimpleNamespace):
    def validate(self) -> list[str]:
        return []


def test_release_check_accepts_ready_production_postgres():
    value = FakeSettings(
        app_env="production",
        database_url="postgresql+psycopg://example.invalid/study_buddy",
    )
    assert release_errors(value, ready_check=lambda: True) == []


def test_release_check_rejects_development_sqlite_and_pending_migration():
    value = FakeSettings(
        app_env="development",
        database_url="sqlite+pysqlite:///./data/study_buddy.db",
    )
    errors = release_errors(value, ready_check=lambda: False)
    assert "APP_ENV 必须设为 production" in errors
    assert "生产 DATABASE_URL 必须使用 postgresql+psycopg" in errors
    assert "数据库不可用或 Alembic 版本未升级到 head" in errors
