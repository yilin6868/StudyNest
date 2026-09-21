"""旧 JSON 导入批次记录。"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import MigrationRun


class MigrationRepository:
    def __init__(self, db: Session):
        self.db = db

    def succeeded(self, source_key_hash: str, source_checksum: str) -> bool:
        run = self.db.scalar(
            select(MigrationRun).where(
                MigrationRun.source_key_hash == source_key_hash,
                MigrationRun.source_checksum == source_checksum,
                MigrationRun.status == "succeeded",
            )
        )
        return run is not None

    def record_success(
        self,
        *,
        source_key_hash: str,
        source_checksum: str,
        summary: str,
        now: datetime,
    ) -> None:
        self.db.add(
            MigrationRun(
                source_key_hash=source_key_hash,
                source_checksum=source_checksum,
                status="succeeded",
                summary=summary,
                created_at=now,
                completed_at=now,
            )
        )
