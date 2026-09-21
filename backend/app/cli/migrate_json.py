"""旧 JSON 迁移 CLI；默认 dry-run，不修改数据库或源文件。"""

import argparse
import json
from pathlib import Path

from ..core.config import settings
from ..db.session import SessionLocal
from ..services.json_migration import run_json_migration


def main() -> int:
    parser = argparse.ArgumentParser(description="扫描、演练、导入或核对旧 JSON")
    parser.add_argument(
        "mode",
        nargs="?",
        default="dry-run",
        choices=["scan", "dry-run", "import", "verify"],
    )
    parser.add_argument("--data-dir", type=Path, default=settings.data_dir)
    parser.add_argument(
        "--backup-confirmed",
        action="store_true",
        help="确认已经完成可恢复备份；import 模式必填",
    )
    args = parser.parse_args()
    if args.mode == "import" and not args.backup_confirmed:
        parser.error("import 前必须完成备份并提供 --backup-confirmed")
    with SessionLocal() as db:
        report = run_json_migration(db, args.data_dir, mode=args.mode)
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
