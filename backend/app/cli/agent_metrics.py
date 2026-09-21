"""汇总近期脱敏 Agent 事件。"""

import argparse
import json

from ..db.session import SessionLocal
from ..observability.metrics import summarize_events
from ..repositories.agent_events import AgentEventRepository


def main() -> int:
    parser = argparse.ArgumentParser(description="汇总 Agent 脱敏指标")
    parser.add_argument("--hours", type=int, default=24, choices=range(1, 24 * 31 + 1))
    args = parser.parse_args()
    with SessionLocal() as db:
        events = AgentEventRepository(db).since(args.hours)
    print(json.dumps(summarize_events(events), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
