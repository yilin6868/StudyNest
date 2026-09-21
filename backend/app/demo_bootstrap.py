"""仅供无持久化演示部署：每个新实例初始化临时数据库和邀请码。"""

from pathlib import Path

from alembic import command
from alembic.config import Config

from .core.config import settings
from .db.session import SessionLocal
from .repositories.invites import InviteRepository
from .services.auth import create_invite, invite_digest


def bootstrap_demo() -> None:
    if settings.app_env != "demo":
        return

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "migrations"))
    command.upgrade(config, "head")

    with SessionLocal() as db:
        if InviteRepository(db).get_by_digest(invite_digest(settings.demo_invite_code)) is None:
            create_invite(db, settings.demo_invite_code, max_uses=None)
