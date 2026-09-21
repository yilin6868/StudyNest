"""按 requestId 查看脱敏 Agent 轨迹。"""

import argparse
import json
import re

from ..core.config import settings
from ..db.session import SessionLocal
from ..observability.sanitizer import pseudonymize
from ..repositories.agent_events import AgentEventRepository

_REQUEST_ID = re.compile(r"^req_[A-Za-z0-9_-]{4,60}$")


def main() -> int:
    parser = argparse.ArgumentParser(description="查看单次 Agent 脱敏轨迹")
    parser.add_argument("--request-id", required=True)
    args = parser.parse_args()
    if not _REQUEST_ID.fullmatch(args.request_id):
        parser.error("requestId 格式不合法")
    with SessionLocal() as db:
        events = AgentEventRepository(db).by_request(args.request_id)
    if not events:
        print(json.dumps({"found": False, "requestId": args.request_id}))
        return 1
    for item in events:
        print(
            json.dumps(
                {
                    "sequence": item.sequence,
                    "requestId": item.request_id,
                    "user": pseudonymize(
                        item.user_id or "deleted", settings.log_pseudonym_secret
                    ),
                    "eventType": item.event_type,
                    "outcome": item.outcome,
                    "durationMs": item.duration_ms,
                    "payload": json.loads(item.payload or "{}"),
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

