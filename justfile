# List available recipes
default:
    @just --list

# Start the dev stack (db + backend + frontend)
up:
    docker compose up -d

# Stop the dev stack
down:
    docker compose down

# Tail dev logs (optionally one service: just logs backend)
logs service="":
    docker compose logs -f {{ service }}

# Apply pending migrations
migrate:
    docker compose exec -T backend uv run alembic upgrade head

# Autogenerate a migration — always review the diff before applying
revision msg:
    docker compose exec -T backend uv run alembic revision --autogenerate -m "{{ msg }}"

# Backend tests (in-container; dev stack must be up)
test:
    docker compose exec -T backend uv run pytest

# Lint + format check, backend + frontend (same as pre-commit)
lint:
    cd backend && uv run ruff check && uv run ruff format --check
    docker compose exec -T frontend pnpm run lint

# Backend type check — NOT in pre-commit, CI gates it
typecheck:
    cd backend && uv run basedpyright

# Everything CI runs — run before pushing
ci: lint typecheck test
    docker compose exec -T frontend sh -c "pnpm run test && pnpm run build"

# Regenerate frontend API types from the running backend (+ biome re-format)
gen-api:
    cd frontend && pnpm run gen:api && pnpm run format

# PII-safe seed dump (also the prod bootstrap artifact)
backup-seed:
    ./scripts/backup_db.sh --seed

# SITE_ADDRESS is required by compose interpolation for EVERY prod command,
# not only up — locally there is no root .env, so each recipe supplies it.
prod_compose := "SITE_ADDRESS=${SITE_ADDRESS:-localhost} docker compose -f docker-compose.prod.yml"

# Local prod smoke test: build + run the prod stack next to dev (https://localhost, self-signed)
prod-up:
    {{ prod_compose }} up -d --build

# Tail prod-stack logs (e.g. just prod-logs scheduler)
prod-logs service="":
    {{ prod_compose }} logs -f {{ service }}

# Tear down the local prod stack INCLUDING its volumes
prod-down:
    {{ prod_compose }} down -v
