# List available recipes
default:
    @just --list

# ---------- dev ----------

# Install/refresh both toolchains
install:
    cd backend && uv sync --locked --all-groups
    cd frontend && pnpm install --frozen-lockfile

# Start Postgres (the only containerised piece in dev)
up:
    docker compose up -d

# Stop Postgres
down:
    docker compose down

# Tail Postgres logs
logs:
    docker compose logs -f db

# Destroy the dev database, volume included, and start it fresh — DELETES ALL LOCAL DATA
db-reset:
    docker compose down -v
    docker compose up -d

# Start Postgres, then run the API with reload (http://localhost:8000)
dev: up api

# Run the API with reload (http://localhost:8000)
api:
    cd backend && uv run uvicorn app.main:app --reload

# Run the Vite dev server (http://localhost:5173) — second terminal
web:
    cd frontend && pnpm run dev

# ---------- database ----------

# Apply pending migrations
migrate:
    cd backend && uv run alembic upgrade head

# Autogenerate a migration — always review the diff before applying
revision msg:
    cd backend && uv run alembic revision --autogenerate -m "{{ msg }}"

# ---------- checks ----------

# Backend tests
test:
    cd backend && uv run pytest

# Lint + format check, backend + frontend
lint:
    cd backend && uv run ruff check && uv run ruff format --check
    cd frontend && pnpm run lint

# Auto-fix what `just lint` reports (linter before formatter, per ruff's guidance)
fix:
    cd backend && uv run ruff check --fix && uv run ruff format
    cd frontend && pnpm run format

# Backend type check — CI gates it
typecheck:
    cd backend && uv run basedpyright

# Everything CI runs — run before pushing
ci: lint typecheck test
    cd frontend && pnpm run test && pnpm run build

# Regenerate frontend API types from the backend schema (+ biome re-format)
gen-api:
    cd frontend && pnpm run gen:api && pnpm run format

# ---------- ops ----------

# PII-safe seed dump (also the prod bootstrap artifact)
backup-seed:
    ./scripts/backup_db.sh --seed

# SITE_ADDRESS is required by compose interpolation for EVERY prod command,
# not only up — locally there is no root .env, so each recipe supplies it.
prod_compose := "SITE_ADDRESS=${SITE_ADDRESS:-localhost} docker compose -f docker-compose.prod.yml"

# Local prod smoke test: build + run the full containerised stack (https://localhost, self-signed)
prod-up:
    {{ prod_compose }} up -d --build

# Tail prod-stack logs (e.g. just prod-logs scheduler)
prod-logs service="":
    {{ prod_compose }} logs -f {{ service }}

# Tear down the local prod stack INCLUDING its volumes
prod-down:
    {{ prod_compose }} down -v
