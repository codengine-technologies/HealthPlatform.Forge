#!/usr/bin/env bash
# tools/timing/report.sh — thin wrapper around report.py.
#
#   tools/timing/report.sh --task task-183            # cost of one cycle
#   tools/timing/report.sh --task task-183 --sync     # write ## Timings in the task file
#   tools/timing/report.sh --last 10                  # last 10 cycles, one line each
#   tools/timing/report.sh --by-kind                  # how many builds/tests per task, and their cost
#   tools/timing/report.sh --by-kind --since 2026-09-01
#
# Picks the first python that actually runs — on Windows `python3` is often the
# Microsoft Store stub, which resolves but exits non-zero without executing
# (same trap as .claude/hooks/verify-before-push.sh).

set -u

SELF_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

PY=""
for candidate in python python3 py; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "import sys" >/dev/null 2>&1; then
    PY="$candidate"
    break
  fi
done

if [ -z "$PY" ]; then
  echo "report.sh: no usable python found (python/python3/py) — the ledger is intact," >&2
  echo "           only this report is unavailable: metrics/timings.jsonl" >&2
  exit 1
fi

exec "$PY" "$SELF_DIR/report.py" "$@"
