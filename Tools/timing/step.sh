#!/usr/bin/env bash
# tools/timing/step.sh — mark the boundaries of a forge chain step.
#
# Usage :
#   tools/timing/step.sh start --task task-183 --step develop
#   tools/timing/step.sh end   --task task-183 --step develop --status ok
#   tools/timing/step.sh end   --task task-183 --step sonar   --status skipped \
#                              --note "api-mail untouched"
#   tools/timing/step.sh end   --task task-183 --step sonar   --status ok \
#                              --iterations 3
#
# `--status` is one of : ok | skipped | failed | rolled-back
#
# `end` also refreshes the `## Timings` section of the task file (via
# report.sh --sync) so the human sees the cost of the cycle at HAG time
# without running anything. That refresh is best-effort : if python is
# unavailable the ledger is still written and the chain continues.
#
# The instrumentation NEVER fails a step : every path exits 0.

set -u

SELF_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib.sh
. "$SELF_DIR/lib.sh"

action=${1:-}
[ $# -gt 0 ] && shift

task="-"; step="-"; status=""; note=""; iterations=""

while [ $# -gt 0 ]; do
  case "$1" in
    --task)       task=${2:-"-"}; shift 2 ;;
    --step)       step=${2:-"-"}; shift 2 ;;
    --status)     status=${2:-}; shift 2 ;;
    --note)       note=${2:-}; shift 2 ;;
    --iterations) iterations=${2:-}; shift 2 ;;
    *) echo "step.sh: unknown option '$1'" >&2; exit 0 ;;
  esac
done

marker="$(state_dir)/${task}__${step}.start"

case "$action" in
  start)
    mkdir -p "$(state_dir)" 2>/dev/null || true
    now_ms > "$marker" 2>/dev/null || true
    emit_event type=step_start task="$task" step="$step"
    ;;

  end)
    t1=$(now_ms)
    dur=""
    if [ -f "$marker" ]; then
      t0=$(cat "$marker" 2>/dev/null)
      case "$t0" in
        ''|*[!0-9]*) note="${note:+$note; }no usable start marker" ;;
        *) dur=$((t1 - t0)) ;;
      esac
      rm -f "$marker" 2>/dev/null || true
    else
      note="${note:+$note; }no start marker"
    fi

    emit_event \
      type=step \
      task="$task" \
      step="$step" \
      status="${status:-ok}" \
      note="$note" \
      iterations="$iterations" \
      duration_ms="$dur"

    # Refresh the task file's ## Timings section (best-effort).
    if [ "$task" != "-" ]; then
      "$SELF_DIR/report.sh" --task "$task" --sync >/dev/null 2>&1 || true
    fi
    ;;

  *)
    echo "step.sh: usage: step.sh {start|end} --task {id} --step {name} [--status ...]" >&2
    ;;
esac

exit 0
