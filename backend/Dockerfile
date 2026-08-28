# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e

# The single upstream reference: every stage below derives from it, so the tag
# and its digest are written once and cannot drift apart between stages.
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
# Set by CD from the git tag. Deliberately without a default: an unstamped
# build arrives as an empty string, and app/config.py owns the one fallback.
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
# Without this uvicorn trusts only 127.0.0.1, so every request is attributed to
# Caddy's container address. A CIDR rather than "*": "*" short-circuits uvicorn
# to the leftmost X-Forwarded-For entry, which is only safe while Caddy keeps
# discarding client-sent values (see Caddyfile), whereas the network match makes
# it walk the chain and take the first untrusted hop either way.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--forwarded-allow-ips", "172.16.0.0/12"]

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
