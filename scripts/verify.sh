#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

if [[ ! -x "$PROJECT_ROOT/backend/.venv/bin/python" ]]; then
  echo "缺少 backend/.venv，请先按 README 安装后端依赖。" >&2
  exit 1
fi

if [[ ! -d "$PROJECT_ROOT/frontend/node_modules" ]]; then
  echo "缺少 frontend/node_modules，请先运行 npm ci。" >&2
  exit 1
fi

echo "[1/4] 后端测试"
cd "$PROJECT_ROOT/backend"
.venv/bin/python -m pytest -q

echo "[2/4] 前端代码检查"
cd "$PROJECT_ROOT/frontend"
npm run lint

echo "[3/4] 前端生产构建"
npm run build

echo "[4/4] 浏览器端到端测试"
"$PROJECT_ROOT/scripts/run-e2e.sh"

echo "全部验证通过。"
