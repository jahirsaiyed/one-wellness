#!/usr/bin/env bash
# check-phi-leaks.sh — CI script that greps source code for potential PHI/PII leaks.
# Checks for logging of sensitive field names, hardcoded credential patterns, etc.
# Exit code 0 = clean. Exit code 1 = potential leaks found.

set -euo pipefail

ERRORS=0
SCAN_DIRS=("backend/app" "frontend/app" "frontend/components" "frontend/lib")

echo "Scanning for potential PHI/PII patterns..."

# ── Helper ────────────────────────────────────────────────────────────────────
scan_pattern() {
  local description="$1"
  local pattern="$2"
  shift 2
  local dirs=("$@")

  for dir in "${dirs[@]}"; do
    [[ -d "$dir" ]] || continue
    local matches
    matches=$(grep -rn --include="*.py" --include="*.ts" --include="*.tsx" \
      -E "$pattern" "$dir" \
      --exclude-dir=".next" --exclude-dir="node_modules" \
      2>/dev/null || true)
    if [[ -n "$matches" ]]; then
      echo ""
      echo "POTENTIAL LEAK [$description]:"
      echo "$matches"
      ERRORS=$((ERRORS + 1))
    fi
  done
}

# ── PHI field names in log calls ─────────────────────────────────────────────
# Flag: print/console.log/logger calls that contain sensitive field names.
scan_pattern \
  "PHI field in log/print statement" \
  "(print|console\.log|logger\.(info|debug|warning|error|critical))\s*\(.*\b(session_notes|mood_score|mood_text|diagnosis|prescription|mental_health|clinical_notes|phi_|encrypted_)\b" \
  "${SCAN_DIRS[@]}"

# ── Hardcoded secrets patterns ────────────────────────────────────────────────
scan_pattern \
  "Hardcoded API key or secret" \
  "(sk-ant-|sk-|SG\.|phc_|AC[0-9a-f]{32}|GOCSPX-)" \
  "${SCAN_DIRS[@]}"

# ── JWT private key pasted inline ─────────────────────────────────────────────
scan_pattern \
  "Inline PEM private key" \
  "-----BEGIN (RSA |EC )?PRIVATE KEY-----" \
  "${SCAN_DIRS[@]}"

# ── Password/secret in plain assignment ──────────────────────────────────────
scan_pattern \
  "Hardcoded password assignment" \
  "password\s*=\s*['\"][^'\"]{8,}['\"]" \
  "backend/app" "frontend/app"

echo ""
if [[ "$ERRORS" -gt 0 ]]; then
  echo "FAILED: $ERRORS potential PHI/PII leak(s) found. Review the matches above." >&2
  echo "If a match is a false positive, add an inline '# noqa: phi' comment." >&2
  exit 1
else
  echo "OK: No PHI/PII leak patterns detected."
fi
