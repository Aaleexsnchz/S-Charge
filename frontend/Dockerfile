# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e

ARG NODE_VERSION=24

# ---------- deps: install with pinned standalone pnpm + BuildKit store cache ----------
FROM node:${NODE_VERSION}-alpine AS deps
WORKDIR /app
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
# corepack install takes the pnpm version from package.json's packageManager,
# so the image, CI and the laptop cannot drift apart.
RUN corepack enable && corepack install
RUN --mount=type=cache,id=pnpm-store,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile

# ---------- build: produce dist/ for production serving ----------
FROM deps AS build
COPY . .
RUN pnpm build

# ---------- prod: serve built assets via nginx (opt-in via --target prod) ----------
FROM nginxinc/nginx-unprivileged:1.27-alpine@sha256:65e3e85dbaed8ba248841d9d58a899b6197106c23cb0ff1a132b7bfe0547e4c0 AS prod
ARG APP_VERSION
LABEL org.opencontainers.image.version=${APP_VERSION}
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
# 127.0.0.1, not localhost: localhost resolves to ::1 first and nginx listens on IPv4 only.
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/index.html || exit 1
CMD ["nginx", "-g", "daemon off;"]
