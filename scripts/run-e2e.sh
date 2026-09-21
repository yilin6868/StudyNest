#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
E2E_DATA_DIR="$(mktemp -d "${TMPDIR:-/tmp}/study-buddy-e2e.XXXXXX")"
BACKEND_PYTHON="${STUDY_BUDDY_PYTHON:-$PROJECT_ROOT/backend/.venv/bin/python}"

cleanup() {
  rm -rf -- "$E2E_DATA_DIR"
}
trap cleanup EXIT INT TERM

if [[ ! -x "$BACKEND_PYTHON" ]]; then
  echo "缺少可用的后端 Python；请修复 backend/.venv，或设置 STUDY_BUDDY_PYTHON。" >&2
  exit 1
fi

export APP_ENV=test
export APP_TIMEZONE=Asia/Shanghai
export E2E_INVITE_CODE=DEMO123
export AUTH_SECRET=e2e-only-secret-do-not-use
export INVITE_CODE_PEPPER=e2e-only-invite-pepper
export LLM_API_KEY=
export DATA_DIR="$E2E_DATA_DIR"
export DATABASE_URL="sqlite+pysqlite:///$E2E_DATA_DIR/study_buddy.sqlite3"
export E2E_BACKEND_PORT="${E2E_BACKEND_PORT:-8000}"
export E2E_FRONTEND_PORT="${E2E_FRONTEND_PORT:-3000}"
export BACKEND_URL="http://127.0.0.1:$E2E_BACKEND_PORT"
export STUDY_BUDDY_PYTHON="$BACKEND_PYTHON"

cd "$PROJECT_ROOT/backend"
"$BACKEND_PYTHON" -m alembic upgrade head
"$BACKEND_PYTHON" -m app.cli.manage_invites create --code "$E2E_INVITE_CODE" --max-uses 100

cd "$PROJECT_ROOT/frontend"
npm run build:standalone
npm run test:e2e:direct
