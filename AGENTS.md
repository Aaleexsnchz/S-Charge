# Repository Guidelines

## Project Structure & Module Organization
This repository is a small full-stack app with separate services:
- `backend/`: FastAPI service code in `backend/app/`, Alembic files in `backend/alembic/`, and a placeholder `backend/tests/` directory.
- `frontend/`: React + TypeScript (Vite) app, source in `frontend/src/`, static files in `frontend/public/`.
- `docker-compose.yml`: local stack for Postgres, backend, and frontend.
- `.env.example`: environment variable template for local setup.

Keep changes scoped to the service you are modifying, and place new modules near related code (`backend/app/<domain>/...`, `frontend/src/<feature>/...`).

## Build, Test, and Development Commands
Run commands from the relevant service directory unless noted.
- `docker compose up --build` (repo root): starts DB, backend, and frontend together.
- `cd backend && uv sync --locked --all-groups`: install backend dependencies.
- `cd backend && uv run uvicorn app.main:app --reload`: run backend locally.
- `cd backend && uv run ruff check app && uv run ruff format --check app && uv run mypy app`: backend quality checks.
- `cd frontend && pnpm install`: install frontend dependencies.
- `cd frontend && pnpm dev`: run frontend dev server.
- `cd frontend && pnpm build`: type-check and production build.
- `cd frontend && pnpm lint`: run ESLint.

## Coding Style & Naming Conventions
- Python: 4-space indentation, max line length 100, and Black-compatible formatting style. If you use a Black editor extension, configure line length to `100` for consistency. Repository checks use Ruff + MyPy via `pyproject.toml`.
- TypeScript/React: use Prettier for formatting and follow ESLint rules in `frontend/eslint.config.js`; prefer functional components.
- Naming: `snake_case` for Python files/functions, `PascalCase` for React components, `camelCase` for TS variables/functions.

## Testing Guidelines
- Backend tests should live in `backend/tests/` and use `pytest` (`uv run pytest`).
- Frontend tests should use Vitest + Testing Library (`pnpm vitest`) with files named `*.test.ts` or `*.test.tsx` next to source or in a `__tests__/` folder.
- Add/update tests for behavior changes; keep test data minimal and explicit.

## Commit & Pull Request Guidelines
Git history is currently minimal (`first commit`), so follow `CONTRIBUTING.md` as the source of truth:
- Use Conventional Commits: `<type>(<scope>): <summary>` (e.g., `feat(backend): add health endpoint`).
- Preferred scopes: `backend`, `frontend`, `root`, `infra`.
- For non-trivial work, open a PR with: what changed, why, and how it was tested; squash merge is preferred.
