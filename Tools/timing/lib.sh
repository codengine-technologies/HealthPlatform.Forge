#!/usr/bin/env bash
# tools/timing/lib.sh — shared helpers for the forge timing instrumentation.
#
# Sourced by measure.sh and step.sh. **Pure bash + coreutils on purpose** : the
# hot path (every build, every test run) must never depend on python, node, or
# anything that can be missing on a workstation. Only report.sh uses python.
#
# Ledger : metrics/timings.jsonl — one JSON object per line, append-only.
# State  : metrics/.state/       — step start markers (gitignored).

# ---------------------------------------------------------------- forge root
# Agents cd into repo subdirs (Api/Mail, Client/Mobile, ...), so we walk up
# from PWD looking for the control plane (CLAUDE.md + tasks/). Falls back to
# the directory two levels above this script.
forge_root() {
  if [ -n "${FORGE_ROOT:-}" ] && [ -d "$FORGE_ROOT/tasks" ]; then
    printf '%s' "$FORGE_ROOT"
    return 0
  fi
  local d p
  d=$(pwd -P 2>/dev/null || pwd)
  while :; do
    if [ -f "$d/CLAUDE.md" ] && [ -d "$d/tasks" ]; then
      printf '%s' "$d"
      return 0
    fi
    p=$(dirname "$d")
    [ "$p" = "$d" ] && break
    d=$p
  done
  d=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)
  if [ -n "$d" ] && [ -f "$d/CLAUDE.md" ]; then
    printf '%s' "$d"
    return 0
  fi
  return 1
}

# ------------------------------------------------------------------ clocks
# Milliseconds since epoch. GNU date (%3N) is present in Git Bash ; if a
# stripped-down date ever lands here, degrade to second precision instead of
# emitting garbage.
now_ms() {
  local t
  t=$(date +%s%3N 2>/dev/null)
  case "$t" in
    *[!0-9]*|'') printf '%s000' "$(date +%s)" ;;
    *) printf '%s' "$t" ;;
  esac
}

now_iso() { date -Iseconds 2>/dev/null || date +%Y-%m-%dT%H:%M:%S%z; }

# --------------------------------------------------------------- ledger IO
ledger_dir()  { printf '%s/metrics' "$(forge_root)"; }
ledger_path() { printf '%s/timings.jsonl' "$(ledger_dir)"; }
state_dir()   { printf '%s/.state' "$(ledger_dir)"; }

# ------------------------------------------------------------------ run id
# Groups every event of one `/forge` run. Env vars do NOT survive between the
# agent's Bash calls, so the run id lives in a file : `/forge` writes it at the
# start of a run and removes it at the end.
#
#   mkdir -p metrics/.state && echo "forge-20260831-183-190" > metrics/.state/run_id
#   rm -f metrics/.state/run_id
#
# A single `/develop` outside a run simply reports "-".
run_id() {
  local f v
  if [ -n "${FORGE_RUN_ID:-}" ]; then
    printf '%s' "$FORGE_RUN_ID"
    return 0
  fi
  f="$(state_dir)/run_id"
  if [ -f "$f" ]; then
    # Strip CR too : the file may have been written with Windows line endings.
    v=$(head -1 "$f" 2>/dev/null | tr -d '\r\n')
    if [ -n "$v" ]; then
      printf '%s' "$v"
      return 0
    fi
  fi
  printf '%s' '-'
}


# Minimal JSON string escaping : backslash, quote, tab, and any newline
# collapsed to a space. Our values are agent-supplied labels and repo keys —
# controlled enough that this is sufficient, and it keeps the ledger parseable
# by report.py without surprises.
json_escape() {
  printf '%s' "$1" \
    | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e 's/\t/ /g' \
    | tr '\n\r' '  '
}

# Keys written as JSON numbers rather than strings.
_is_numeric_key() {
  case "$1" in
    duration_ms|exit_code|iterations|files|count) return 0 ;;
    *) return 1 ;;
  esac
}

# emit_event key=value ...
#
# Always-present keys are filled in automatically (ts, run_id). Unknown keys
# are accepted verbatim so a future step can record its own dimension without
# touching this file.
emit_event() {
  local dir line kv key val
  dir=$(ledger_dir) || return 0
  mkdir -p "$dir" 2>/dev/null || return 0

  line="{\"ts\":\"$(json_escape "$(now_iso)")\""
  line="$line,\"run_id\":\"$(json_escape "$(run_id)")\""

  for kv in "$@"; do
    key=${kv%%=*}
    val=${kv#*=}
    [ -z "$key" ] && continue
    if _is_numeric_key "$key"; then
      case "$val" in
        ''|*[!0-9-]*) line="$line,\"$key\":null" ;;
        *) line="$line,\"$key\":$val" ;;
      esac
    else
      line="$line,\"$key\":\"$(json_escape "$val")\""
    fi
  done
  line="$line}"

  # Append atomically enough for our single-writer usage. Never fail the
  # caller : a broken ledger must not break a build.
  printf '%s\n' "$line" >> "$(ledger_path)" 2>/dev/null || true
}

# ----------------------------------------------------------- human helpers
# 754123 -> "12 min 34 s" ; 4210 -> "4.2 s"
fmt_ms() {
  local ms=${1:-0} s m
  case "$ms" in ''|*[!0-9]*) printf '—'; return ;; esac
  if [ "$ms" -lt 10000 ]; then
    printf '%d.%d s' $((ms / 1000)) $(((ms % 1000) / 100))
  else
    s=$((ms / 1000)); m=$((s / 60)); s=$((s % 60))
    if [ "$m" -eq 0 ]; then printf '%d s' "$s"; else printf '%d min %02d s' "$m" "$s"; fi
  fi
}

# Locate a task file whatever its lifecycle state. Prints nothing when absent.
task_file() {
  local id=$1 root f
  root=$(forge_root) || return 1
  for f in "$root/tasks/wip-$id.md" "$root/tasks/review-$id.md" \
           "$root/tasks/done-$id.md" "$root/tasks/todo-$id.md" \
           "$root/tasks/archived/archived-$id.md"; do
    [ -f "$f" ] && { printf '%s' "$f"; return 0; }
  done
  return 1
}
