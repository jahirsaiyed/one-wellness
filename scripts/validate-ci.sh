#!/usr/bin/env bash
# validate-ci.sh — Dry-run CI quality gates locally before pushing.
#
# Checks (all must pass for Sprint 1 QA gate):
#   1. Ruff lint (backend/app)
#   2. Bandit security scan (no HIGH severity)
#   3. PHI leak script
#   4. pytest unit tests with 80% coverage gate
#
# Usage:
#   bash scripts/validate-ci.sh              # run from repo root
#   bash scripts/validate-ci.sh --lint-only  # skip tests

set -euo pipefail

ERRORS=0
SKIP_TESTS=false
BACKEND_DIR="backend"
APP_DIR="backend/app"

# ── Argument parsing ──────────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --lint-only) SKIP_TESTS=true ;;
    --help|-h)
      echo "Usage: bash scripts/validate-ci.sh [--lint-only]"
      exit 0
      ;;
  esac
done

log_step() { echo ""; echo "═══ $1 ═══"; }
log_pass() { echo "  PASS: $1"; }
log_fail() { echo "  FAIL: $1" >&2; ERRORS=$((ERRORS + 1)); }

# ── Step 1: Ruff lint ─────────────────────────────────────────────────────────
log_step "Step 1 — Ruff lint"
if command -v ruff &>/dev/null; then
  if ruff check "$APP_DIR/"; then
    log_pass "ruff lint clean"
  else
    log_fail "ruff found lint errors"
  fi
else
  echo "  SKIP: ruff not installed (run: pip install ruff)"
fi

# ── Step 2: Bandit security scan ─────────────────────────────────────────────
log_step "Step 2 — Bandit security scan (HIGH severity)"
if command -v bandit &>/dev/null; then
  if bandit -r "$APP_DIR/" -ll --skip B101 -q 2>&1 | grep -q "No issues identified"; then
    log_pass "bandit: no HIGH severity issues"
  else
    bandit_out=$(bandit -r "$APP_DIR/" -ll --skip B101 2>&1 || true)
    if echo "$bandit_out" | grep -qE "Severity: High"; then
      echo "$bandit_out"
      log_fail "bandit found HIGH severity issues"
    else
      log_pass "bandit: no HIGH severity issues"
    fi
  fi
else
  echo "  SKIP: bandit not installed (run: pip install bandit)"
fi

# ── Step 3: PHI leak check ────────────────────────────────────────────────────
log_step "Step 3 — PHI/PII leak scan"
if [[ -f "scripts/check-phi-leaks.sh" ]]; then
  if bash scripts/check-phi-leaks.sh; then
    log_pass "PHI leak scan clean"
  else
    log_fail "PHI/PII leak patterns detected"
  fi
else
  echo "  SKIP: scripts/check-phi-leaks.sh not found"
fi

# ── Step 4: Unit tests + coverage ─────────────────────────────────────────────
if [[ "$SKIP_TESTS" == "false" ]]; then
  log_step "Step 4 — pytest unit tests (≥80% coverage)"
  if command -v pytest &>/dev/null; then
    pushd "$BACKEND_DIR" > /dev/null
    if pytest tests/unit tests/test_auth.py \
        -v --tb=short \
        --cov=app \
        --cov-report=term-missing \
        --cov-fail-under=80 \
        --no-header; then
      log_pass "unit tests pass, coverage ≥ 80%"
    else
      log_fail "unit tests failed or coverage < 80%"
    fi
    popd > /dev/null
  else
    echo "  SKIP: pytest not installed"
  fi
else
  echo ""
  echo "═══ Step 4 — pytest (skipped via --lint-only) ═══"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
if [[ "$ERRORS" -gt 0 ]]; then
  echo "FAILED: $ERRORS gate(s) did not pass. Fix the issues above before pushing." >&2
  exit 1
else
  echo "ALL GATES PASSED — safe to push."
fi
