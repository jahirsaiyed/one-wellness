# GCC Wellness Platform

A B2B2C mental wellness platform for the GCC region — therapist marketplace, AI companion, video sessions, and corporate wellness programs.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), Tailwind CSS, shadcn/ui, next-intl (EN + AR) |
| Backend | FastAPI (Python 3.12), SQLAlchemy async, Alembic |
| Database | PostgreSQL 16 + pgvector |
| Cache | Redis 7 |
| AI | Claude API (Anthropic) via swappable adapter layer |
| Video | Agora RTC (E2EE, no recording) |
| Payments | Tap Payments |
| Hosting | Vercel (frontend) + Render (backend/DB) |
| Storage | Cloudflare R2 |

## Quick Start

### Prerequisites

- Docker Desktop ≥ 4.25
- [just](https://github.com/casey/just) task runner (`cargo install just` or `brew install just`)

### Run locally

```bash
git clone https://github.com/jahirsaiyed/one-wellness.git
cd one-wellness

cp .env.example .env
# Fill in the minimum dev vars: DATABASE_URL, REDIS_URL, SECRET_KEY, PHI_ENCRYPTION_KEY

just up        # Start postgres, redis, backend, frontend
just migrate   # Apply Alembic migrations

curl http://localhost:8000/health
# {"status":"healthy","db":"connected","redis":"connected","env":"development"}

open http://localhost:3000
```

### Common commands

```bash
just up            # Start all services
just down          # Stop all services
just migrate       # Run database migrations
just test          # Backend unit + integration tests
just red-team      # Crisis detection red-team suite
just test-frontend # Frontend Jest tests
just psql          # Open psql shell
just logs          # Tail backend logs
just reset-db      # Destroy and recreate local DB (WARNING: data loss)
just ci            # Full local CI check (lint + phi-check + tests)
```

## Repository Structure

```
one-wellness/
├── backend/                  # FastAPI monorepo
│   ├── app/
│   │   ├── main.py           # App entry point + /health endpoint
│   │   ├── core/
│   │   │   ├── config.py     # pydantic-settings (all env vars)
│   │   │   ├── database.py   # Async SQLAlchemy engine + session
│   │   │   ├── redis.py      # Redis connection pool
│   │   │   └── security.py   # JWT RS256 + password hashing
│   │   ├── services/         # Domain services (auth, booking, ai, …)
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   └── routers/          # FastAPI route handlers
│   ├── alembic/              # Database migrations
│   ├── Dockerfile            # Multi-stage: development + production
│   └── pyproject.toml        # Python dependencies
├── frontend/                 # Next.js 14 App Router
│   ├── app/
│   │   └── [locale]/         # EN + AR locale routing (next-intl)
│   ├── messages/             # i18n strings (en.json, ar.json)
│   ├── Dockerfile            # Multi-stage: deps → builder → production
│   └── package.json          # Node dependencies
├── .github/
│   ├── workflows/ci.yml      # lint → test → build → deploy pipeline
│   └── PULL_REQUEST_TEMPLATE.md
├── scripts/
│   ├── validate-env.sh       # Check all required env vars are set
│   └── check-phi-leaks.sh    # Grep source for PHI/PII patterns
├── docs/                     # Technical specifications
├── docker-compose.yml        # Local dev: all 4 services
├── justfile                  # Task runner
├── render.yaml               # Render IaC (backend + DB)
├── vercel.json               # Vercel config + security headers
└── .env.example              # All required env vars (no secrets)
```

## Documentation

All technical specs live in `docs/`:

| Document | Contents |
|---|---|
| `ARCHITECTURE.md` | C4 diagrams (L1/L2/L3) |
| `docs/SPRINT_PLAN.md` | 52 stories across 8 sprints |
| `docs/API_SPEC.md` | Full REST API reference |
| `docs/DATA_MODEL.md` | PostgreSQL schema + RLS policies |
| `docs/AI_SERVICE_SPEC.md` | AI agent prompts + crisis pipeline |
| `docs/SECURITY_SPEC.md` | JWT, AES-256 PHI encryption, RBAC, PDPL |
| `docs/ENVIRONMENT_SETUP.md` | Full setup + infra config |
| `docs/TESTING_STRATEGY.md` | Test pyramid, red-team suite, k6 load tests |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for branching strategy, commit conventions, PHI rules, and PR requirements.

## Deployment

- **Staging:** auto-deploys to Render + Vercel on every merge to `main`
- **Production:** requires manual approval in GitHub Environments after staging E2E tests pass
- See `render.yaml` and `vercel.json` for infrastructure configuration
- See `SPRINT_0_MANUAL_CHECKLIST.md` for one-time provisioning steps

## License

Proprietary — all rights reserved.
