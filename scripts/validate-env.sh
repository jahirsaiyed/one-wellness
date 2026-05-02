#!/usr/bin/env bash
# validate-env.sh — CI script that checks all required env vars are set and non-empty.
# Exit code 0 = all present. Exit code 1 = one or more missing.

set -euo pipefail

REQUIRED_VARS=(
  # Application
  APP_ENV
  SECRET_KEY
  ALLOWED_ORIGINS

  # Database
  DATABASE_URL

  # Redis
  REDIS_URL

  # JWT
  ACCESS_TOKEN_EXPIRE_MINUTES
  REFRESH_TOKEN_EXPIRE_DAYS

  # PHI encryption
  PHI_ENCRYPTION_KEY
)

# In production, additional vars are required:
REQUIRED_VARS_PRODUCTION=(
  ANTHROPIC_API_KEY
  AGORA_APP_ID
  AGORA_APP_CERTIFICATE
  TAP_SECRET_KEY
  TAP_WEBHOOK_SECRET
  SENDGRID_API_KEY
  TWILIO_ACCOUNT_SID
  TWILIO_AUTH_TOKEN
  FIREBASE_PROJECT_ID
  R2_ACCOUNT_ID
  R2_ACCESS_KEY_ID
  R2_SECRET_ACCESS_KEY
  SENTRY_DSN
)

ERRORS=0

check_var() {
  local var_name="$1"
  local value="${!var_name:-}"
  if [[ -z "$value" ]]; then
    echo "ERROR: Required environment variable '$var_name' is not set or empty." >&2
    ERRORS=$((ERRORS + 1))
  fi
}

echo "Checking required environment variables..."

for var in "${REQUIRED_VARS[@]}"; do
  check_var "$var"
done

# Only enforce production vars when APP_ENV=production
if [[ "${APP_ENV:-development}" == "production" ]]; then
  echo "APP_ENV=production — checking production-only variables..."
  for var in "${REQUIRED_VARS_PRODUCTION[@]}"; do
    check_var "$var"
  done
fi

if [[ "$ERRORS" -gt 0 ]]; then
  echo ""
  echo "FAILED: $ERRORS required environment variable(s) missing." >&2
  echo "Copy .env.example to .env and fill in all values." >&2
  exit 1
else
  echo "OK: All required environment variables are set."
fi
