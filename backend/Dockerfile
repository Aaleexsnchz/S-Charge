# syntax=docker/dockerfile:1.7

# Shared base: pinned uv binary + build env.
FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv
COPY --from=ghcr.io/astral-sh/uv:0.11.22 /uv /uvx /bin/
WORKDIR /app

# ---------- build-prod: runtime dependencies only ----------
FROM base AS build-prod
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# ---------- prod: lean, non-root runtime (no uv, no dev deps) ----------
FROM python:3.12-slim AS prod
ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"
RUN useradd -m -u 10001 appuser
WORKDIR /app
COPY --from=build-prod --chown=appuser:appuser /app/.venv /app/.venv
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser alembic ./alembic
COPY --chown=appuser:appuser alembic.ini ./alembic.ini
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/health').status == 200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ---------- dev: full deps incl. tooling; source bind-mounted by compose ----------
FROM base AS dev
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked
COPY . .
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app/app"]
