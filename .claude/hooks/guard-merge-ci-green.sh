#!/usr/bin/env bash
# Hook PreToolUse (Bash matcher) — blocks merge if CI is RED on the target branch
# Only triggers on "gh pr merge" commands.
#
# CONFIGURE: set FORGE_CI_WORKFLOW to your workflow name (default: "CI")
#   export FORGE_CI_WORKFLOW="Build and Test"
#
# Copyright 2026 Yannis TOCREAU — Apache License 2.0

INPUT=$(cat)

COMMAND=$(echo "$INPUT" | python3 -c "
import json, sys
data = json.load(sys.stdin)
inp = data.get('tool_input', {})
print(inp.get('command') or '')
" 2>/dev/null)

if ! echo "$COMMAND" | grep -qE 'gh pr merge'; then
  exit 0
fi

WORKFLOW_NAME="${FORGE_CI_WORKFLOW:-CI}"
TARGET_BRANCH="${FORGE_TARGET_BRANCH:-develop}"

echo "Pre-merge verification: checking CI status on $TARGET_BRANCH..."

# Get the latest workflow run status on the target branch
CI_STATUS=$(gh run list --branch "$TARGET_BRANCH" --limit 1 --json conclusion --jq '.[0].conclusion' 2>/dev/null)

if [ "$CI_STATUS" != "success" ]; then
  echo "BLOCKED: CI is not GREEN on $TARGET_BRANCH (status: $CI_STATUS)."
  echo ""
  echo "The orchestrator MUST NOT merge while CI is RED."
  echo "Fix the failing CI on $TARGET_BRANCH before merging any PR."
  echo ""
  echo "To check CI status manually:"
  echo "  gh run list --branch $TARGET_BRANCH --limit 1"
  echo ""
  echo "To configure the target branch:"
  echo "  export FORGE_TARGET_BRANCH='main'"
  exit 2
fi

echo "CI is GREEN on $TARGET_BRANCH. Merge allowed."
exit 0
