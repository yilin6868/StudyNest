#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PYTHON_BIN="${STUDY_BUDDY_PYTHON:-$PROJECT_ROOT/backend/.venv/bin/python}"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "缺少可用的 Python；请修复 backend/.venv 或设置 STUDY_BUDDY_PYTHON。" >&2
  exit 1
fi

if [[ -n "$(git -C "$PROJECT_ROOT" status --porcelain)" ]]; then
  echo "工作区不干净；发布前必须先提交并留下可回滚版本。" >&2
  exit 1
fi

git -C "$PROJECT_ROOT" diff --check

cd "$PROJECT_ROOT/backend"
"$PYTHON_BIN" -m pytest -q

cd "$PROJECT_ROOT/frontend"
npm run lint
npm run build:standalone

test -f .next/standalone/server.js
test -d .next/standalone/.next/static
test -f .next/standalone/public/assets/buddy-male.jpg
test -f .next/standalone/public/assets/buddy-female.jpg

for pattern in 'node_modules/' '.next/' '.env' '.env.*'; do
  grep -Fqx "$pattern" .vefaasignore
done
for pattern in '.venv/' 'data/' '.env' '.vefaas/'; do
  grep -Fqx "$pattern" "$PROJECT_ROOT/backend/.vefaasignore"
done

echo "本地发布前检查全部通过。"
