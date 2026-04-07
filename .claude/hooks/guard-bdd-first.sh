#!/usr/bin/env bash
# Hook PreToolUse — warns when creating handler/service files without corresponding test specs
# Enforces BDD-first: test specs should exist BEFORE implementation.
#
# CONFIGURE: set patterns via environment variables:
#   FORGE_HANDLER_PATTERN: regex for handler/service files (default: Handler|Service|UseCase|Command|Query)
#   FORGE_TEST_DIRS: colon-separated list of test directories to check (default: tests:test:spec:features)
#
# Copyright 2026 Yannis TOCREAU — Apache License 2.0

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
data = json.load(sys.stdin)
inp = data.get('tool_input', {})
print(inp.get('file_path') or inp.get('path') or inp.get('target_file') or '')
" 2>/dev/null)

if [ -z "$FILE_PATH" ]; then exit 0; fi

# Configurable patterns
HANDLER_PATTERN="${FORGE_HANDLER_PATTERN:-Handler|Service|UseCase|Command|Query}"
TEST_DIRS="${FORGE_TEST_DIRS:-tests:test:spec:features}"

# Only check files that match the handler/service pattern
if ! echo "$FILE_PATH" | grep -qE "($HANDLER_PATTERN)"; then
  exit 0
fi

# Skip test files themselves
if echo "$FILE_PATH" | grep -qEi '(test|spec|step|feature)'; then
  exit 0
fi

# Extract the base name without extension to search for corresponding tests
BASE_NAME=$(basename "$FILE_PATH" | sed 's/\.[^.]*$//' | sed -E "s/(Handler|Service|UseCase|Command|Query)$//")

if [ -z "$BASE_NAME" ]; then exit 0; fi

# Search for corresponding test files in configured test directories
FOUND_TESTS=""
IFS=':' read -ra DIRS <<< "$TEST_DIRS"
for dir in "${DIRS[@]}"; do
  if [ -d "$dir" ]; then
    MATCHES=$(find "$dir" -type f -iname "*${BASE_NAME}*" 2>/dev/null | head -5)
    if [ -n "$MATCHES" ]; then
      FOUND_TESTS="$FOUND_TESTS$MATCHES"
    fi
  fi
done

if [ -z "$FOUND_TESTS" ]; then
  echo "WARNING: BDD-first violation detected."
  echo ""
  echo "Creating handler/service file: $FILE_PATH"
  echo "But no corresponding test spec found for '$BASE_NAME' in test directories."
  echo ""
  echo "BDD-first rule: test specs (Gherkin .feature, unit tests, integration tests)"
  echo "should exist BEFORE the implementation. Write the test first, verify RED,"
  echo "then implement until GREEN."
  echo ""
  echo "Expected: a file matching '*${BASE_NAME}*' in one of: $TEST_DIRS"
  echo ""
  echo "To configure handler detection pattern:"
  echo "  export FORGE_HANDLER_PATTERN='Handler|Service|UseCase|Controller'"
  echo "To configure test directories:"
  echo "  export FORGE_TEST_DIRS='tests:test:spec:features:__tests__'"
  echo ""
  echo "Proceeding anyway (warning only — set FORGE_BDD_STRICT=1 to block)."

  if [ "${FORGE_BDD_STRICT:-0}" = "1" ]; then
    echo ""
    echo "BLOCKED: FORGE_BDD_STRICT is enabled. Write test specs first."
    exit 2
  fi
fi

exit 0
