#!/usr/bin/env bash
# tools/timing/measure.sh — time one command and record it in the forge ledger.
#
# Usage :
#   tools/timing/measure.sh --task task-183 --step develop --repo api-mail \
#       --kind build -- dotnet build HealthPlatform.Api.Mail.sln
#
#   tools/timing/measure.sh --task task-183 --step sonar --repo api-mail \
#       --kind test --label coverage -- dotnet test tests/x/x.csproj --collect:...
#
# Everything after the first `--` is the command, verbatim — later `--` are
# preserved (needed for `npm test -- --watch=false`).
#
# Contract :
#   - stdout/stderr are NOT captured : the caller sees the compiler / test
#     output exactly as if the command had been run directly.
#   - the command's exit code is propagated unchanged, so `&&` chains and the
#     agent's RED/GREEN logic keep working.
#   - the command is exec'd directly, so MSYS argument conversion and any
#     exported env (MSYS_NO_PATHCONV, SONAR_TOKEN, ...) behave identically to
#     a direct invocation. This is what makes it safe to wrap
#     `dotnet sonarscanner begin`.
#   - a failure in the instrumentation itself never fails the command.
#
# --kind is the dimension that answers "how many full builds / test suites does
# one task really cost". Use one of :
#   build | test | scan | lint | capture | restore | nuget-wait | other

set -u

SELF_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=lib.sh
. "$SELF_DIR/lib.sh"

task="-"; step="-"; repo="-"; kind="other"; label=""; cwd=""

while [ $# -gt 0 ]; do
  case "$1" in
    --task)  task=${2:-"-"}; shift 2 ;;
    --step)  step=${2:-"-"}; shift 2 ;;
    --repo)  repo=${2:-"-"}; shift 2 ;;
    --kind)  kind=${2:-other}; shift 2 ;;
    --label) label=${2:-}; shift 2 ;;
    --cwd)   cwd=${2:-}; shift 2 ;;
    --) shift; break ;;
    *)
      echo "measure.sh: unknown option '$1' (expected --task/--step/--repo/--kind/--label/--cwd then -- command)" >&2
      exit 64
      ;;
  esac
done

if [ $# -eq 0 ]; then
  echo "measure.sh: no command given (nothing after '--')" >&2
  exit 64
fi

# --cwd lets the call site stay at the workspace root, so `tools/timing/...`
# always resolves. Resolved against the current directory first, then against
# the forge root — `--cwd Api/Mail` works from anywhere.
if [ -n "$cwd" ]; then
  if [ -d "$cwd" ]; then
    cd "$cwd" || { echo "measure.sh: cannot cd into '$cwd'" >&2; exit 66; }
  elif [ -d "$(forge_root)/$cwd" ]; then
    cd "$(forge_root)/$cwd" || { echo "measure.sh: cannot cd into '$cwd'" >&2; exit 66; }
  else
    echo "measure.sh: --cwd '$cwd' not found (neither relative to PWD nor to the forge root)" >&2
    exit 66
  fi
fi

t0=$(now_ms)
"$@"
rc=$?
t1=$(now_ms)

emit_event \
  type=cmd \
  task="$task" \
  step="$step" \
  repo="$repo" \
  kind="$kind" \
  label="$label" \
  cwd="${cwd:--}" \
  cmd="$*" \
  duration_ms=$((t1 - t0)) \
  exit_code="$rc"

exit "$rc"
