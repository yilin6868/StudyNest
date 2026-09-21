"""邀请码管理 CLI；历史邀请码只保存摘要，不提供反查。"""

import argparse
import secrets
from datetime import datetime

from sqlalchemy import func, select

from ..db.models import InviteCode
from ..db.session import SessionLocal
from ..repositories.invites import InviteRepository
from ..services.auth import AccountError, create_invite, utcnow


def _expires_at(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("--expires-at 必须包含时区，例如 2026-12-31T23:59:59+08:00")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description="管理注册邀请码")
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create", help="创建邀请码")
    create.add_argument("--code", help="自定义邀请码；省略时安全随机生成")
    create.add_argument("--max-uses", type=int, default=1)
    create.add_argument("--expires-at", help="ISO 8601 过期时间")

    disable = commands.add_parser("disable", help="按 ID 停用邀请码")
    disable.add_argument("invite_id")
    commands.add_parser("summary", help="只显示数量汇总，不显示明文")
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.command == "create":
            code = args.code or secrets.token_urlsafe(9)
            try:
                invite_id = create_invite(
                    db,
                    code,
                    max_uses=args.max_uses,
                    expires_at=_expires_at(args.expires_at),
                )
            except (AccountError, ValueError) as exc:
                parser.error(str(exc))
            print(f"邀请码 ID: {invite_id}")
            print(f"邀请码（只显示这一次）: {code}")
            return 0

        if args.command == "disable":
            changed = InviteRepository(db).disable(args.invite_id, now=utcnow())
            db.commit()
            print("已停用" if changed else "未找到或已经停用")
            return 0 if changed else 1

        total = db.scalar(select(func.count()).select_from(InviteCode)) or 0
        active = (
            db.scalar(
                select(func.count())
                .select_from(InviteCode)
                .where(InviteCode.disabled_at.is_(None))
            )
            or 0
        )
        print(f"邀请码总数: {total}；未停用: {active}；已停用: {total - active}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
