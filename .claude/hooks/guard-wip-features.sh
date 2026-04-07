#!/usr/bin/env bash
# Hook PreToolUse (Bash matcher) — blocks git push if .feature files have @wip
# but step definitions exist (indicating false coverage).
#
# Rationale: @wip-tagged scenarios give a false impression of test coverage.
# If step definitions exist, the feature should be fully implemented, not @wip.
#
# CONFIGURE: set FEATURES_DIR and STEPS_DIR for your project structure.
#   FEATURES_DIR: glob pattern for .feature files (default: **/Features/**/*.feature)
#   STEPS_DIR: glob pattern for step definition files (default: **/StepDefinitions/**)
#
# Copyright 2026 Yannis TOCREAU — Apache License 2.0

INPUT=$(cat)

COMMAND=$(echo "$INPUT" | python3 -c "
import json, sys
data = json.load(sys.stdin)
inp = data.get('tool_input', {})
print(inp.get('command') or '')
" 2>/dev/null)

if ! echo "$COMMAND" | grep -qE '^git push'; then
  exit 0
fi

# Configurable paths — override via environment variables
FEATURES_DIR="${FORGE_FEATURES_DIR:-**/Features/**/*.feature}"
STEPS_PATTERN="${FORGE_STEPS_PATTERN:-StepDefinitions}"

echo "Checking for @wip features with existing step definitions..."

VIOLATIONS=""

for feature_file in $(git ls-files "$FEATURES_DIR" 2>/dev/null); do
  if [ ! -f "$feature_file" ]; then continue; fi

  # Check if file contains @wip tag
  if ! grep -qE '^\s*@wip' "$feature_file" 2>/dev/null; then continue; fi

  # Extract scenario names from @wip-tagged scenarios
  FEATURE_NAME=$(basename "$feature_file" .feature)

  # Check if step definitions exist for this feature
  STEP_FILES=$(git ls-files | grep -i "$STEPS_PATTERN" | grep -i "$FEATURE_NAME" 2>/dev/null)

  if [ -n "$STEP_FILES" ]; then
    VIOLATIONS="$VIOLATIONS\n- $feature_file has @wip but step definitions exist: $STEP_FILES"
  fi
done

if [ -n "$VIOLATIONS" ]; then
  echo "BLOCKED: @wip features with existing step definitions detected."
  echo ""
  echo "Violations found:"
  echo -e "$VIOLATIONS"
  echo ""
  echo "@wip-tagged features with step definitions give a false impression of coverage."
  echo "Either remove @wip (the tests should run) or remove the step definitions."
  echo ""
  echo "To configure paths, set environment variables:"
  echo "  FORGE_FEATURES_DIR='tests/**/*.feature'"
  echo "  FORGE_STEPS_PATTERN='step_definitions'"
  exit 2
fi

echo "@wip check passed."
exit 0
