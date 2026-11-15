# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e

# Every stage derives from this one pinned reference.
FROM python:3.13-slim@sha256:7ce4b6dfe35e55397b7cda544f8a13f191b7ae28dc5aad71fe664dbc9bc2623f AS python-base

# Shared base: pinned uv binary + build env.
FROM python-base AS base
ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv
COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /uvx /bin/
WORKDIR /app

# ---------- build-prod: runtime dependencies only ----------
FROM base AS build-prod
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# ---------- prod: lean, non-root runtime (no uv, no dev deps) ----------
FROM python-base AS prod
# Set by CD from the git tag. No default: app/config.py owns the fallback.
ARG APP_VERSION
ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    APP_VERSION=${APP_VERSION}
LABEL org.opencontainers.image.version=${APP_VERSION}
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
# Trust X-Forwarded-For from the Docker network, or every request is attributed
# to Caddy. A CIDR rather than "*", which takes the leftmost (client-supplied)
# entry; the CIDR makes uvicorn walk the chain to the first untrusted hop.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--forwarded-allow-ips", "172.16.0.0/12"]

# ---------- scheduler: prod runtime + supercronic driving the refresh ETLs ----------
# amd64-only binary, matching the production host. tzdata backs the crontab's
# Madrid time.
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
