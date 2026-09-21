from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.core.config import settings


def test_p1c_migration_upgrade_downgrade_and_upgrade(tmp_path, monkeypatch):
    backend_root = Path(__file__).resolve().parents[1]
    database_url = f"sqlite+pysqlite:///{tmp_path / 'migration.sqlite3'}"
    monkeypatch.setattr(settings, "database_url", database_url)
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "migrations"))

    command.upgrade(config, "20260909_0003")
    engine = create_engine(database_url)
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "20260909_0003"
    schema = inspect(engine)
    assert "user_memories" in schema.get_table_names()
    assert {item["name"] for item in schema.get_columns("chat_sessions")} >= {
        "summary",
        "updated_at",
        "status",
    }

    command.downgrade(config, "20260909_0002")
    schema = inspect(engine)
    assert "user_memories" not in schema.get_table_names()
    assert "agent_action_confirmations" in schema.get_table_names()
    assert "summary" not in {item["name"] for item in schema.get_columns("chat_sessions")}

    command.upgrade(config, "20260909_0003")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "20260909_0003"
    engine.dispose()
