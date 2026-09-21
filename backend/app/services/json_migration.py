"""旧 JSON 数据扫描、演练、导入和核对；永不修改源文件。"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..core.config import settings
from ..db.models import DailyGoal, DailyStudyRecord, StudySession
from ..repositories.goals import GoalRepository
from ..repositories.migrations import MigrationRepository
from ..repositories.study import StudyRepository
from ..repositories.users import UserRepository


class MigrationError(ValueError):
    pass


class MigrationConflict(MigrationError):
    pass


@dataclass
class MigrationReport:
    mode: str
    batch_id: str = field(default_factory=lambda: str(uuid4()))
    source_checksums: list[str] = field(default_factory=list)
    users: int = 0
    succeeded: int = 0
    skipped: int = 0
    failed: int = 0
    daily_records: int = 0
    tomatoes: int = 0
    minutes: int = 0
    sessions: int = 0
    goals: int = 0
    conflicts: int = 0
    damaged_files: int = 0
    unknown_files: int = 0
    stats_mismatches: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def _read_object(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MigrationError("存在无法读取的 JSON 文件") from exc
    if not isinstance(value, dict):
        raise MigrationError("JSON 顶层必须是对象")
    return value


def _sources(data_dir: Path) -> list[Path]:
    paths = {p.parent for p in data_dir.rglob("history.json")}
    paths.update(p.parent for p in data_dir.rglob("goal.json"))
    paths.update(p.parent for p in data_dir.rglob("stats.json"))
    return sorted(paths)


def _source_identity(data_dir: Path, directory: Path) -> tuple[str, str]:
    relative = directory.relative_to(data_dir).as_posix() or "."
    source_hash = hashlib.sha256(relative.encode()).hexdigest()
    digest = hashlib.sha256()
    for name in ("history.json", "goal.json", "stats.json"):
        path = directory / name
        if path.exists():
            digest.update(name.encode())
            digest.update(path.read_bytes())
    return source_hash, digest.hexdigest()


def _parse(directory: Path) -> dict:
    result = {"days": {}, "sessions": {}, "goal": "", "stats_mismatch": False}
    history_path = directory / "history.json"
    if history_path.exists():
        history = _read_object(history_path)
        version = history.get("schemaVersion", 1)
        if version not in {1, 2}:
            raise MigrationError("不支持的 history schemaVersion")
        days = history.get("days", {})
        sessions = history.get("completedSessions", {})
        if not isinstance(days, dict) or not isinstance(sessions, dict):
            raise MigrationError("history 字段结构错误")
        for raw_date, raw_day in days.items():
            if not isinstance(raw_day, dict):
                raise MigrationError("history 每日记录结构错误")
            try:
                parsed_date = date.fromisoformat(raw_date)
                tomatoes = int(raw_day.get("tomato", 0))
                minutes = int(raw_day.get("minutes", 0))
            except (TypeError, ValueError) as exc:
                raise MigrationError("history 含非法日期或数字") from exc
            if parsed_date > date.today() or tomatoes < 0 or minutes < 0:
                raise MigrationError("history 含未来日期或负数")
            result["days"][parsed_date] = (tomatoes, minutes)
        for session_id, raw_session in sessions.items():
            if not isinstance(raw_session, dict):
                raise MigrationError("completedSessions 结构错误")
            try:
                completed_at = datetime.fromisoformat(raw_session["completedAt"])
                minutes = int(raw_session["minutes"])
            except (KeyError, TypeError, ValueError) as exc:
                raise MigrationError("completedSessions 含非法记录") from exc
            if minutes < 0:
                raise MigrationError("completedSessions 含负数")
            if completed_at.tzinfo is None:
                completed_at = completed_at.replace(tzinfo=timezone.utc)
            result["sessions"][str(session_id)] = (minutes, completed_at)

    goal_path = directory / "goal.json"
    if goal_path.exists():
        goal = _read_object(goal_path).get("text", "")
        if not isinstance(goal, str):
            raise MigrationError("goal.text 必须是文字")
        result["goal"] = goal.strip()[:60]

    stats_path = directory / "stats.json"
    if stats_path.exists():
        stats = _read_object(stats_path)
        try:
            stats_date = date.fromisoformat(str(stats.get("date", "")))
            stats_tomatoes = int(stats.get("tomato", 0))
            stats_minutes = int(stats.get("minutes", 0))
        except (TypeError, ValueError):
            result["stats_mismatch"] = True
        else:
            result["stats_mismatch"] = result["days"].get(stats_date) != (
                stats_tomatoes,
                stats_minutes,
            )
    return result


def _add_totals(report: MigrationReport, parsed: dict) -> None:
    report.daily_records += len(parsed["days"])
    report.tomatoes += sum(item[0] for item in parsed["days"].values())
    report.minutes += sum(item[1] for item in parsed["days"].values())
    report.sessions += len(parsed["sessions"])
    report.goals += int(bool(parsed["goal"]))
    report.stats_mismatches += int(parsed["stats_mismatch"])


def _legacy_key(data_dir: Path, directory: Path) -> str:
    return directory.relative_to(data_dir).as_posix() or "."


def _check_conflicts(
    db: Session,
    user_id: str,
    parsed: dict,
    goal_date: date,
    *,
    require_present: bool = False,
) -> int:
    conflicts = 0
    for day, (tomatoes, minutes) in parsed["days"].items():
        existing = db.scalar(
            select(DailyStudyRecord).where(
                DailyStudyRecord.user_id == user_id,
                DailyStudyRecord.study_date == day,
            )
        )
        if (require_present and not existing) or (
            existing and (existing.tomato_count, existing.minutes) != (tomatoes, minutes)
        ):
            conflicts += 1
    for session_id, (minutes, completed_at) in parsed["sessions"].items():
        existing_session = db.scalar(
            select(StudySession).where(
                StudySession.user_id == user_id,
                StudySession.client_session_id == session_id,
            )
        )
        stored_completed_at = existing_session.completed_at if existing_session else None
        if stored_completed_at and stored_completed_at.tzinfo is None:
            stored_completed_at = stored_completed_at.replace(tzinfo=completed_at.tzinfo)
        if (require_present and not existing_session) or (
            existing_session
            and (
                existing_session.minutes != minutes
                or stored_completed_at != completed_at
            )
        ):
            conflicts += 1
    if parsed["goal"]:
        existing_goal = db.scalar(
            select(DailyGoal).where(
                DailyGoal.user_id == user_id, DailyGoal.goal_date == goal_date
            )
        )
        if (require_present and not existing_goal) or (
            existing_goal and existing_goal.text != parsed["goal"]
        ):
            conflicts += 1
    return conflicts


def run_json_migration(
    db: Session,
    data_dir: Path,
    *,
    mode: str = "dry-run",
    migration_date: date | None = None,
) -> MigrationReport:
    if mode not in {"scan", "dry-run", "import", "verify"}:
        raise ValueError("mode 必须是 scan、dry-run、import 或 verify")
    data_dir = data_dir.resolve()
    report = MigrationReport(mode=mode)
    directories = _sources(data_dir) if data_dir.exists() else []
    report.users = len(directories)
    if data_dir.exists():
        report.unknown_files = sum(
            1
            for path in data_dir.rglob("*.json")
            if path.name not in {"history.json", "goal.json", "stats.json"}
        )
    goal_date = migration_date or date.today()

    for directory in directories:
        try:
            source_hash, checksum = _source_identity(data_dir, directory)
            report.source_checksums.append(checksum)
            parsed = _parse(directory)
            _add_totals(report, parsed)
            if mode in {"scan", "dry-run"}:
                report.succeeded += 1
                continue

            migrations = MigrationRepository(db)
            legacy_key = _legacy_key(data_dir, directory)
            user = UserRepository(db).get_by_legacy_key(legacy_key)

            if mode == "verify":
                if not user:
                    report.conflicts += 1
                    report.failed += 1
                    continue
                conflicts = _check_conflicts(
                    db, user.id, parsed, goal_date, require_present=True
                )
                report.conflicts += conflicts
                report.failed += int(conflicts > 0)
                report.succeeded += int(conflicts == 0)
                continue

            if migrations.succeeded(source_hash, checksum):
                report.skipped += 1
                continue

            now = datetime.now(timezone.utc)
            if not user:
                user = UserRepository(db).create(
                    user_id=str(uuid4()),
                    username=None,
                    username_normalized=None,
                    password_hash=None,
                    timezone_name=settings.app_timezone,
                    status="legacy_unclaimed",
                    legacy_user_key=legacy_key,
                    now=now,
                )
                db.flush()
            conflicts = _check_conflicts(db, user.id, parsed, goal_date)
            if conflicts:
                report.conflicts += conflicts
                raise MigrationConflict("目标数据库存在不一致记录")
            study = StudyRepository(db)
            for day, (tomatoes, minutes) in parsed["days"].items():
                study.set_imported_day(
                    user_id=user.id,
                    study_date=day,
                    tomato_count=tomatoes,
                    minutes=minutes,
                    now=now,
                )
            for session_id, (minutes, completed_at) in parsed["sessions"].items():
                study.add_imported_session(
                    user_id=user.id,
                    client_session_id=session_id,
                    minutes=minutes,
                    completed_at=completed_at,
                )
            if parsed["goal"]:
                GoalRepository(db).set(
                    user.id,
                    goal_date,
                    parsed["goal"],
                    now=now,
                    source="legacy_import",
                )
            migrations.record_success(
                source_key_hash=source_hash,
                source_checksum=checksum,
                summary=json.dumps(
                    {
                        "days": len(parsed["days"]),
                        "sessions": len(parsed["sessions"]),
                        "goal": bool(parsed["goal"]),
                    },
                    ensure_ascii=False,
                ),
                now=now,
            )
            db.commit()
            report.succeeded += 1
        except MigrationConflict:
            db.rollback()
            report.failed += 1
        except (MigrationError, OSError, SQLAlchemyError):
            db.rollback()
            report.failed += 1
            report.damaged_files += 1
    return report
