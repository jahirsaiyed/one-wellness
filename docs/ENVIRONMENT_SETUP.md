# Environment Setup — GCC Wellness Platform

Developer onboarding, local environment, and production infrastructure configuration.

---

## 1. Prerequisites

| Tool | Version | Install |
|---|---|---|
| Docker Desktop | ≥ 4.25 | https://docker.com/products/docker-desktop |
| Python | 3.12+ | `pyenv install 3.12` |
| Node.js | 20 LTS | `nvm install 20` |
| pnpm | 9+ | `npm install -g pnpm` |
| Git | ≥ 2.40 | via OS package manager |
| Just (task runner) | latest | `cargo install just` or `brew install just` |

---

## 2. Repository Structure

```
gcc-wellness/
├── backend/                    # FastAPI monorepo
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py       # Settings (pydantic-settings)
│   │   │   ├── database.py     # Async SQLAlchemy engine
│   │   │   ├── redis.py        # Redis connection pool
│   │   │   └── security.py     # JWT, encryption utilities
│   │   ├── services/
│   │   │   ├── auth/
│   │   │   ├── booking/
│   │   │   ├── payment/
│   │   │   ├── ai/
│   │   │   │   ├── adapters/
│   │   │   │   │   ├── base.py
│   │   │   │   │   ├── anthropic_adapter.py
│   │   │   │   │   └── openai_adapter.py
│   │   │   │   ├── agents/
│   │   │   │   │   ├── companion.py
│   │   │   │   │   ├── booking_agent.py
│   │   │   │   │   ├── matching.py
│   │   │   │   │   ├── support_agent.py
│   │   │   │   │   └── crisis_detector.py
│   │   │   │   └── prompts/
│   │   │   │       ├── companion.py
│   │   │   │       ├── booking_agent.py
│   │   │   │       ├── matching.py
│   │   │   │       ├── support_agent.py
│   │   │   │       └── crisis.py
│   │   │   ├── notification/
│   │   │   ├── content/
│   │   │   ├── corporate/
│   │   │   └── admin/
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic request/response models
│   │   ├── routers/            # FastAPI route handlers
│   │   └── tests/
│   │       ├── unit/
│   │       ├── integration/
│   │       ├── e2e/
│   │       └── red_team/       # Crisis detection scenarios
│   ├── alembic/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/                   # Next.js 14 App Router
│   ├── app/
│   │   ├── [locale]/           # next-intl locale routing
│   │   │   ├── (public)/       # Landing, therapist browse (no auth)
│   │   │   ├── (auth)/         # Login, register, TOTP
│   │   │   ├── (client)/       # Dashboard, companion, booking
│   │   │   ├── (therapist)/    # Therapist portal
│   │   │   ├── (hr-admin)/     # Corporate HR portal
│   │   │   └── (admin)/        # Platform admin
│   │   └── api/                # Next.js API routes (BFF proxies)
│   ├── components/
│   ├── lib/
│   ├── messages/
│   │   ├── en.json
│   │   └── ar.json
│   ├── public/
│   ├── Dockerfile
│   ├── next.config.ts
│   └── package.json
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── .env.test
├── justfile                    # Task runner commands
└── docs/                       # All technical documents
```

---

## 3. Local Development Setup

### Step 1: Clone and configure environment

```bash
git clone https://github.com/your-org/gcc-wellness.git
cd gcc-wellness

# Copy environment template
cp .env.example .env

# Edit .env with your development credentials
# Minimum required for local dev: see Section 4
```

### Step 2: Start all services

```bash
# Start PostgreSQL 16, Redis 7, FastAPI backend, Next.js frontend
docker-compose up -d

# Verify all services are healthy (should see all green within 60s)
docker-compose ps
```

### Step 3: Run database migrations

```bash
# Apply all Alembic migrations
docker-compose exec backend alembic upgrade head

# Verify migrations applied
docker-compose exec backend alembic current
```

### Step 4: Seed development data

```bash
# Create test users, therapist profiles, and sample content
docker-compose exec backend python scripts/seed_dev_data.py
```

### Step 5: Verify setup

```bash
# Backend health check
curl http://localhost:8000/health
# Expected: {"status": "healthy", "db": "connected", "redis": "connected"}

# Frontend
open http://localhost:3000
```

---

## 4. Environment Variables Reference

**File:** `.env.example` — commit this file. **Never commit `.env`.**

### Core Application

```env
# ============================================================
# APPLICATION
# ============================================================
APP_ENV=development                    # development | staging | production
APP_DEBUG=true                         # false in staging/production
SECRET_KEY=                            # 32-byte random hex; python -c "import secrets; print(secrets.token_hex(32))"
ALLOWED_ORIGINS=http://localhost:3000  # Comma-separated list for CORS

# ============================================================
# DATABASE
# ============================================================
DATABASE_URL=postgresql+asyncpg://wellness_user:wellness_pass@postgres:5432/wellness_db
# Production: postgresql+asyncpg://user:password@render-host:5432/wellness_prod

# ============================================================
# REDIS
# ============================================================
REDIS_URL=redis://redis:6379/0
# Production: rediss://user:password@render-redis-host:6379/0  (note: rediss:// for TLS)

# ============================================================
# JWT
# ============================================================
JWT_PRIVATE_KEY=                       # RSA-2048 private key PEM (multiline — use PRIVATE_KEY_FILE in prod)
JWT_PUBLIC_KEY=                        # RSA-2048 public key PEM
JWT_PRIVATE_KEY_FILE=                  # Alternative: path to PEM file (production)
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# ============================================================
# ENCRYPTION (PHI at-rest)
# ============================================================
PHI_ENCRYPTION_KEY=                    # 32-byte hex key for AES-256 PHI encryption
# NEVER use the same key in dev and production
# Generate: python -c "import secrets; print(secrets.token_hex(32))"

# ============================================================
# AI PROVIDERS
# ============================================================
AI_PROVIDER=anthropic                  # anthropic | openai | gemini
AI_MODEL=claude-sonnet-4-6
AI_FALLBACK_PROVIDER=openai

ANTHROPIC_API_KEY=sk-ant-...           # From console.anthropic.com
OPENAI_API_KEY=sk-...                  # From platform.openai.com (fallback)
# GEMINI_API_KEY=                      # Future — not used in MVP

# ============================================================
# AGORA (Video Sessions)
# ============================================================
AGORA_APP_ID=                          # From Agora Console
AGORA_APP_CERTIFICATE=                 # From Agora Console (used for token generation)

# ============================================================
# TAP PAYMENTS
# ============================================================
TAP_SECRET_KEY=sk_test_...             # Sandbox: sk_test_... | Production: sk_live_...
TAP_PUBLISHABLE_KEY=pk_test_...        # Used in frontend for Tap.js
TAP_WEBHOOK_SECRET=                    # Tap Payments webhook signing secret

# ============================================================
# SENDGRID (Email)
# ============================================================
SENDGRID_API_KEY=SG....
SENDGRID_FROM_EMAIL=noreply@gcc-wellness.com
SENDGRID_FROM_NAME=GCC Wellness

# SendGrid Template IDs
SENDGRID_TEMPLATE_BOOKING_CONFIRMATION=d-...
SENDGRID_TEMPLATE_BOOKING_REMINDER_24H=d-...
SENDGRID_TEMPLATE_BOOKING_REMINDER_1H=d-...
SENDGRID_TEMPLATE_WELCOME=d-...
SENDGRID_TEMPLATE_PAYOUT_STATEMENT=d-...
SENDGRID_TEMPLATE_DELETION_CONFIRMATION=d-...

# ============================================================
# TWILIO (SMS)
# ============================================================
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=+19...              # Twilio phone number

# ============================================================
# FIREBASE (Push Notifications)
# ============================================================
FIREBASE_PROJECT_ID=gcc-wellness
FIREBASE_SERVICE_ACCOUNT_JSON=        # Base64-encoded service account JSON
# OR: FIREBASE_SERVICE_ACCOUNT_FILE=path/to/service-account.json

# ============================================================
# CLOUDFLARE R2 (Object Storage)
# ============================================================
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=gcc-wellness-staging    # gcc-wellness-prod in production
R2_PUBLIC_URL=https://r2.gcc-wellness.com

# ============================================================
# GOOGLE OAUTH2 (User auth + Calendar)
# ============================================================
GOOGLE_CLIENT_ID=...apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-...
GOOGLE_REDIRECT_URI=http://localhost:8000/v1/auth/google/callback

# ============================================================
# POSTHOG (Analytics)
# ============================================================
POSTHOG_API_KEY=phc_...
POSTHOG_HOST=https://app.posthog.com
# POSTHOG_DISABLED=true              # Uncomment for local dev to avoid polluting analytics

# ============================================================
# SENTRY (Error Monitoring)
# ============================================================
SENTRY_DSN=https://...@sentry.io/...
SENTRY_ENVIRONMENT=development         # development | staging | production
# Note: PHI scrubber configured in sentry init — never logs health data

# ============================================================
# FRONTEND (Next.js)
# ============================================================
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_AGORA_APP_ID=             # Same as AGORA_APP_ID — exposed to browser
NEXT_PUBLIC_TAP_PUBLISHABLE_KEY=      # Same as TAP_PUBLISHABLE_KEY
NEXT_PUBLIC_POSTHOG_KEY=              # Same as POSTHOG_API_KEY
NEXT_PUBLIC_FIREBASE_CONFIG=          # JSON string of Firebase web app config
```

### Secrets Management in Production

**Render:** Use Render Environment Groups for shared secrets across services.
- Create "production-secrets" environment group
- Add all production values
- Attach group to FastAPI service

**Never in environment variables for production:**
- `JWT_PRIVATE_KEY` — use `JWT_PRIVATE_KEY_FILE` pointing to a mounted secret file
- `PHI_ENCRYPTION_KEY` — rotate regularly; store in Render secrets, not code

---

## 5. Docker Compose Configuration

### `docker-compose.yml` (local development)

```yaml
version: '3.9'

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: wellness_db
      POSTGRES_USER: wellness_user
      POSTGRES_PASSWORD: wellness_pass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U wellness_user -d wellness_db"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      target: development
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./backend:/app
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 15s
      timeout: 5s
      retries: 5
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ./frontend
      target: development
    ports:
      - "3000:3000"
    env_file:
      - .env
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    depends_on:
      - backend
    command: pnpm dev

volumes:
  postgres_data:
```

### Backend Dockerfile (multi-stage)

```dockerfile
FROM python:3.12-slim AS base
WORKDIR /app
RUN adduser --disabled-password --gecos "" appuser

FROM base AS development
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
USER appuser
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -f http://localhost:8000/health || exit 1

FROM base AS production
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && rm -rf /root/.cache
COPY . .
RUN chown -R appuser:appuser /app
USER appuser
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Frontend Dockerfile (multi-stage)

```dockerfile
FROM node:20-alpine AS base
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs

FROM base AS deps
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN npm install -g pnpm && pnpm install --frozen-lockfile

FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED 1
RUN pnpm build

FROM base AS production
WORKDIR /app
ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
USER nextjs
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -f http://localhost:3000/ || exit 1
CMD ["node", "server.js"]
```

---

## 6. CI/CD Pipeline (GitHub Actions)

### `.github/workflows/ci.yml`

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Lint backend (Ruff)
        run: docker run --rm -v $PWD/backend:/app python:3.12-slim sh -c "pip install ruff && ruff check /app"
      - name: Lint frontend (ESLint)
        run: docker run --rm -v $PWD/frontend:/app node:20-alpine sh -c "npm install -g pnpm && pnpm install && pnpm lint"
      - name: PHI leak check
        run: bash scripts/check-phi-leaks.sh

  test-backend:
    runs-on: ubuntu-latest
    needs: lint
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_DB: wellness_test
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
    steps:
      - uses: actions/checkout@v4
      - name: Run unit tests
        env:
          DATABASE_URL: postgresql+asyncpg://test_user:test_pass@localhost:5432/wellness_test
          REDIS_URL: redis://localhost:6379/0
          AI_PROVIDER: mock
        run: |
          cd backend
          pip install -r requirements.txt
          alembic upgrade head
          pytest tests/unit -v --cov=app --cov-report=xml
      - name: Run integration tests
        run: |
          cd backend
          pytest tests/integration -v

  test-frontend:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - name: Install dependencies
        run: cd frontend && pnpm install --frozen-lockfile
      - name: Run Jest tests
        run: cd frontend && pnpm test --coverage

  build:
    runs-on: ubuntu-latest
    needs: [test-backend, test-frontend]
    steps:
      - uses: actions/checkout@v4
      - name: Build backend Docker image
        run: docker build --target production -t gcc-wellness-backend:${{ github.sha }} ./backend
      - name: Build frontend Docker image
        run: docker build --target production -t gcc-wellness-frontend:${{ github.sha }} ./frontend
      - name: Validate env vars
        run: bash scripts/validate-env.sh

  deploy-staging:
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to Render (staging)
        run: |
          curl -X POST ${{ secrets.RENDER_DEPLOY_HOOK_STAGING }}
      - name: Wait for deploy
        run: sleep 60
      - name: Run E2E tests against staging
        run: |
          cd frontend
          pnpm cypress run --env baseUrl=https://staging.gcc-wellness.com

  deploy-production:
    runs-on: ubuntu-latest
    needs: deploy-staging
    if: github.ref == 'refs/heads/main'
    environment:
      name: production           # Requires manual approval in GitHub Environments
    steps:
      - name: Deploy to Render (production)
        run: |
          curl -X POST ${{ secrets.RENDER_DEPLOY_HOOK_PRODUCTION }}
      - name: Deploy to Vercel (production)
        run: |
          npx vercel --prod --token=${{ secrets.VERCEL_TOKEN }}
```

---

## 7. Production Infrastructure (MVP)

### Render Services

| Service | Type | Config |
|---|---|---|
| `gcc-wellness-api` | Web Service (Docker) | 1 vCPU, 512MB RAM starter; auto-scale to 2GB at 70% CPU |
| `gcc-wellness-db` | PostgreSQL 16 | Render managed; daily backups; connection pooling via PgBouncer |
| `gcc-wellness-redis` | Redis 7 | Render managed; 25MB starter |

### Render `render.yaml`

```yaml
services:
  - type: web
    name: gcc-wellness-api
    env: docker
    dockerfilePath: ./backend/Dockerfile
    dockerContext: ./backend
    dockerTarget: production
    plan: starter
    autoDeploy: true
    healthCheckPath: /health
    envVars:
      - fromGroup: production-secrets
      - key: APP_ENV
        value: production
      - key: APP_DEBUG
        value: false

databases:
  - name: gcc-wellness-db
    plan: starter
    ipAllowList: []
```

### Vercel Configuration (`vercel.json`)

```json
{
  "framework": "nextjs",
  "buildCommand": "pnpm build",
  "devCommand": "pnpm dev",
  "installCommand": "pnpm install",
  "regions": ["cdg1", "fra1"],
  "env": {
    "NEXT_PUBLIC_API_URL": "https://api.gcc-wellness.com"
  },
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "X-Content-Type-Options", "value": "nosniff" }
      ]
    }
  ],
  "rewrites": [
    { "source": "/api/:path*", "destination": "https://api.gcc-wellness.com/v1/:path*" }
  ]
}
```

---

## 8. Useful Commands (Justfile)

```makefile
# Run all services locally
up:
    docker-compose up -d

# Run database migrations
migrate:
    docker-compose exec backend alembic upgrade head

# Create a new migration
migration name:
    docker-compose exec backend alembic revision --autogenerate -m "{{name}}"

# Run backend tests
test:
    docker-compose exec backend pytest tests/ -v

# Run crisis red-team tests
red-team:
    docker-compose exec backend pytest tests/red_team/ -v --tb=short

# Tail backend logs
logs:
    docker-compose logs -f backend

# Open psql
psql:
    docker-compose exec postgres psql -U wellness_user -d wellness_db

# Stop all services
down:
    docker-compose down

# Reset database (WARNING: destroys all local data)
reset-db:
    docker-compose down -v
    docker-compose up -d postgres
    sleep 5
    docker-compose exec backend alembic upgrade head
    docker-compose exec backend python scripts/seed_dev_data.py
```

---

## 9. External Service Sandbox Setup

### Tap Payments Sandbox
1. Register at [tap.company/en/developers](https://tap.company/en/developers)
2. Create a test app; copy sandbox keys to `.env`
3. Test card numbers: `4111 1111 1111 1111` (Visa), `5100 0000 0000 0000` (Mastercard)
4. mada test: `4000 0020 0000 0000`

### Agora Sandbox
1. Register at [agora.io](https://console.agora.io)
2. Create project with APP ID + APP Certificate enabled
3. Enable Media Encryption in project settings
4. Copy APP_ID and APP_CERTIFICATE to `.env`

### Anthropic API
1. Create account at [console.anthropic.com](https://console.anthropic.com)
2. Set usage limits (recommended: $50/month cap in development)
3. Copy API key to `.env`

### Firebase FCM
1. Create Firebase project
2. Enable Cloud Messaging
3. Generate service account JSON (Project Settings → Service Accounts)
4. Base64-encode: `base64 -i service-account.json | tr -d '\n'`
5. Set `FIREBASE_SERVICE_ACCOUNT_JSON` in `.env`
