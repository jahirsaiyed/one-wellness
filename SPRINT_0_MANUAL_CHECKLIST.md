# Sprint 0 — Manual Checklist

These tasks cannot be automated and must be completed by the team lead / DevOps before Sprint 1 begins.

| # | Action | Done When | Owner |
|---|---|---|---|
| 1 | **GitHub branch protection on `main`** — require PR approval + all CI checks to pass before merge | Settings → Branches → Branch protection rule shows `main` protected | Lead |
| 2 | **Provision Render staging** — create FastAPI web service (`gcc-wellness-api`) + PostgreSQL 16 (`gcc-wellness-db`) + Redis 7 (`gcc-wellness-redis`) on Render | `GET https://staging.gcc-wellness.com/health` returns `{"status":"healthy"}` | DevOps |
| 3 | **Provision Vercel project** — connect GitHub repo, set `NEXT_PUBLIC_API_URL=https://staging.gcc-wellness.com`, add preview deployment | Next.js staging URL loads without errors | DevOps |
| 4 | **Create Cloudflare R2 bucket** — bucket name `gcc-wellness-staging`; enable public access via custom subdomain `r2.gcc-wellness.com` | SDK test upload/download succeeds | DevOps |
| 5 | **Obtain Anthropic API key** — create production account at console.anthropic.com; set monthly spend cap; store key in Render `production-secrets` environment group | `ANTHROPIC_API_KEY` present in Render secrets | Lead |
| 6 | **Obtain Tap Payments sandbox credentials** — register at tap.company/en/developers; copy `TAP_SECRET_KEY` + `TAP_PUBLISHABLE_KEY` + `TAP_WEBHOOK_SECRET` to Render staging secrets | Sandbox dashboard accessible; test charge succeeds | Lead |
| 7 | **Obtain Agora App ID + App Certificate** — create project at console.agora.io with Media Encryption enabled; copy to Render secrets | SDK test call (token generation) succeeds | Lead |
| 8 | **Sign up for SendGrid, Twilio, Firebase FCM** — obtain API keys and store in Render staging secrets (`SENDGRID_API_KEY`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `FIREBASE_SERVICE_ACCOUNT_JSON`) | Each service receives a test event | Lead |
| 9 | **Engage clinical advisor** — NDA and contract signed for AI prompt review before Sprint 3 (KAN-25 AI Companion) | Signed documents on file | Lead |
| 10 | **Create PostHog + Sentry projects** — configure PHI scrubbing in Sentry `before_send`; add `POSTHOG_API_KEY` and `SENTRY_DSN` to `.env` and Render secrets | Both dashboards receive a test event | DevOps |

---

## Automated Sprint 0 Deliverables (already committed)

All files below were scaffolded by the Sprint 0 implementation task:

| File | Status |
|---|---|
| `.gitignore` | Done |
| `CONTRIBUTING.md` | Done |
| `.env.example` | Done |
| `docker-compose.yml` | Done |
| `justfile` | Done |
| `render.yaml` | Done |
| `vercel.json` | Done |
| `.github/workflows/ci.yml` | Done |
| `.github/PULL_REQUEST_TEMPLATE.md` | Done |
| `backend/Dockerfile` | Done |
| `backend/pyproject.toml` | Done |
| `backend/requirements.txt` | Done |
| `backend/app/main.py` | Done |
| `backend/app/core/config.py` | Done |
| `backend/app/core/database.py` | Done |
| `backend/app/core/redis.py` | Done |
| `backend/app/core/security.py` | Done |
| `backend/alembic.ini` | Done |
| `backend/alembic/env.py` | Done |
| `frontend/Dockerfile` | Done |
| `frontend/package.json` | Done |
| `frontend/next.config.ts` | Done |
| `frontend/app/layout.tsx` | Done |
| `frontend/app/[locale]/layout.tsx` | Done |
| `frontend/app/[locale]/page.tsx` | Done |
| `frontend/messages/en.json` | Done |
| `frontend/messages/ar.json` | Done |
| `scripts/validate-env.sh` | Done |
| `scripts/check-phi-leaks.sh` | Done |

---

## Sprint 1 Start Gate

Sprint 1 (KAN-67 Docker Dev Env + KAN-68 CI/CD) can begin once:
- [ ] All 10 manual checklist items above are complete
- [ ] `docker-compose up -d` starts all 4 services locally
- [ ] `GET http://localhost:8000/health` returns `{"status":"healthy","db":"connected","redis":"connected"}`
- [ ] CI pipeline runs green on a test PR to `main`
