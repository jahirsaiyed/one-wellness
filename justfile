# GCC Wellness Platform — Task Runner
# Install: cargo install just  OR  brew install just
# Usage:   just <recipe>

# Start all services locally
up:
    docker-compose up -d

# Stop all services
down:
    docker-compose down

# Run database migrations
migrate:
    docker-compose exec backend alembic upgrade head

# Create a new migration (usage: just migration "add-user-table")
migration name:
    docker-compose exec backend alembic revision --autogenerate -m "{{name}}"

# Run backend tests
test:
    docker-compose exec backend pytest tests/ -v --cov=app --cov-report=term-missing

# Run crisis red-team tests
red-team:
    docker-compose exec backend pytest tests/red_team/ -v --tb=short

# Run frontend tests
test-frontend:
    docker-compose exec frontend pnpm test

# Tail backend logs
logs:
    docker-compose logs -f backend

# Open psql shell
psql:
    docker-compose exec postgres psql -U wellness_user -d wellness_db

# Build backend image (production target)
build-backend:
    docker build --target production -t gcc-wellness-backend:local ./backend

# Build frontend image (production target)
build-frontend:
    docker build --target production -t gcc-wellness-frontend:local ./frontend

# Reset database (WARNING: destroys all local data)
reset-db:
    docker-compose down -v
    docker-compose up -d postgres
    sleep 5
    docker-compose exec backend alembic upgrade head
    docker-compose exec backend python scripts/seed_dev_data.py

# Run PHI leak check
check-phi:
    bash scripts/check-phi-leaks.sh

# Validate environment variables
validate-env:
    bash scripts/validate-env.sh

# Lint backend with Ruff
lint-backend:
    docker-compose exec backend ruff check app/

# Format backend with Ruff
fmt-backend:
    docker-compose exec backend ruff format app/

# Full CI check locally (mirrors GitHub Actions)
ci:
    just lint-backend
    just check-phi
    just validate-env
    just test
    just test-frontend
