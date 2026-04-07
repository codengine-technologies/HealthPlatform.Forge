#!/usr/bin/env bash
# Hook PreToolUse — blocks writing technical jargon in .feature files
# Rule: .feature files are PO property. Purely functional.
# Zero HTTP codes, zero URLs, zero JWT, zero database.
# Technical details go in step definitions (.cs/.ts/.py), not in .feature.
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
if ! echo "$FILE_PATH" | grep -qE '\.feature$'; then exit 0; fi

CONTENT=$(echo "$INPUT" | python3 -c "
import json, sys
data = json.load(sys.stdin)
inp = data.get('tool_input', {})
print(inp.get('content') or inp.get('new_string') or '')
" 2>/dev/null)

if [ -z "$CONTENT" ]; then exit 0; fi

VIOLATIONS=""

if echo "$CONTENT" | grep -qEi '(status|returns?|receive|code)\s+(200|201|400|401|403|404|409|422|500)|(200|201|400|401|403|404|409|422|500)\s+(error|Forbidden|Unauthorized|Not Found|Conflict|OK|Created)'; then
  VIOLATIONS="$VIOLATIONS\n- HTTP status codes detected — use functional language instead"
fi

if echo "$CONTENT" | grep -qE '(GET|POST|PUT|DELETE|PATCH)\s+/|/api/'; then
  VIOLATIONS="$VIOLATIONS\n- API paths detected — describe the action, not the endpoint"
fi

if echo "$CONTENT" | grep -qEi '\b(JWT|JSON|SQL|ClinicId|endpoint|header[s]?|HTTP|tenant)\b'; then
  VIOLATIONS="$VIOLATIONS\n- Technical terms detected — use business language"
fi

if echo "$CONTENT" | grep -qEi '\b(access token|refresh token|authentication token|bearer token)\b'; then
  VIOLATIONS="$VIOLATIONS\n- Token references detected — describe the auth flow functionally"
fi

if echo "$CONTENT" | grep -qEi '\bin the database\b|\bfrom the database\b'; then
  VIOLATIONS="$VIOLATIONS\n- Database references detected — describe the business outcome"
fi

if echo "$CONTENT" | grep -qEi 'validation error for'; then
  VIOLATIONS="$VIOLATIONS\n- Internal field names in errors — describe what the user sees"
fi

if [ -n "$VIOLATIONS" ]; then
  echo "BLOCKED: .feature file contains forbidden technical jargon."
  echo ""
  echo "Violations found:"
  echo -e "$VIOLATIONS"
  echo ""
  echo "Feature files must be purely functional (PO natural language)."
  echo "Technical details (HTTP codes, URLs, tokens) go in step definitions."
  echo ""
  echo "Examples:"
  echo "  'the response status is 200'  →  'the operation succeeds'"
  echo "  'I POST /api/v1/auth/login'   →  'the user logs in'"
  echo "  'I receive a JWT token'       →  'the user is authenticated'"
  echo "  'returns 403'                 →  'the user is denied access'"
  exit 2
fi

exit 0
