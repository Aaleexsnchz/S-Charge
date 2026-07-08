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
COPY --chown=appuser:appuser scripts ./scripts
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/health').status == 200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ---------- scheduler: prod runtime + supercronic driving the refresh ETLs ----------
# amd64-only binary: the target VPS (Hetzner CX22) is x86; add an arm64 case if
# the host ever changes. tzdata is required for the CRON-in-Madrid-time entries.
FROM prod AS scheduler
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*
ADD --checksum=sha256:dcb1403c188a9438c47d4bba82a9c357fc9351ce91627fb2bae627f0f5becfc4 \
    --chmod=755 \
    https://github.com/aptible/supercronic/releases/download/v0.2.47/supercronic-linux-amd64 \
    /usr/local/bin/supercronic
COPY --chown=appuser:appuser crontab ./crontab
USER appuser
HEALTHCHECK NONE
CMD ["supercronic", "/app/crontab"]

# ---------- dev: full deps incl. tooling; source bind-mounted by compose ----------
FROM base AS dev
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked
COPY . .
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app/app"]
