# Contributing to GCC Wellness Platform

## Branching Strategy

All development follows a **feature-branch → main** model.

```
main          ← protected; production-ready at all times
  └── feature/KAN-XX-short-description   ← your work branch
  └── fix/KAN-XX-short-description       ← bug fixes
  └── chore/KAN-XX-short-description     ← non-feature changes (deps, config)
```

**Rules:**
- Never push directly to `main`.
- Branch names must reference the Jira ticket: `feature/KAN-25-ai-companion-api`.
- Keep branches short-lived (≤ 5 days). Rebase onto `main` before opening a PR.

## Commit Conventions

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(scope): <subject>    ← subject max 72 chars, imperative tense

[optional body]

[optional footer: e.g. Closes KAN-25]
```

**Types:** `feat` | `fix` | `chore` | `refactor` | `test` | `docs` | `ci` | `perf`

**Examples:**
```
feat(auth): add RS256 JWT refresh token rotation
fix(crisis): handle empty message payload in detector
chore(deps): bump fastapi to 0.115
test(booking): add integration tests for calendar conflict
```

## Pull Requests

1. Open a PR against `main` (never against another feature branch).
2. Fill out every section of the PR template (`.github/PULL_REQUEST_TEMPLATE.md`).
3. Assign at least **1 reviewer**; require approval before merge.
4. CI must be green (lint + test-backend + test-frontend + build).
5. Squash-merge into `main`; delete the source branch after merge.

## PHI / Security Rules

- **Never** log, print, or return raw PHI fields (`session_notes`, `mood_*`, diagnosis fields).
- **Never** commit secrets, API keys, or `.env` files. Use `.env.example` only.
- Run `bash scripts/check-phi-leaks.sh` locally before pushing.
- Any change to `backend/app/core/security.py` or AI prompt files requires **2 reviewers**.

## Local Setup

See `docs/ENVIRONMENT_SETUP.md` for full setup instructions.

Quick start:
```bash
cp .env.example .env
# Fill in minimum dev vars (DATABASE_URL, REDIS_URL, SECRET_KEY)
docker-compose up -d
just migrate
curl http://localhost:8000/health
```

## Testing Requirements

| Layer | Minimum Coverage | Command |
|---|---|---|
| Backend unit | 80% | `just test` |
| Crisis red-team | 100% pass | `just red-team` |
| Frontend | Build passes | `just test-frontend` |

Crisis-related stories (KAN-26, KAN-58, KAN-59) require red-team tests to pass before merging. No exceptions.
