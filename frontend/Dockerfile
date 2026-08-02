# syntax=docker/dockerfile:1.7

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
# Vite inlines VITE_* values into the bundle, so the version is fixed here at
# build time — it is not runtime configuration and cannot be set on the container.
ARG APP_VERSION=dev
ENV VITE_APP_VERSION=${APP_VERSION}
COPY . .
RUN pnpm build

# ---------- prod: serve built assets via nginx (opt-in via --target prod) ----------
FROM nginx:1.27-alpine AS prod
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1/index.html || exit 1
CMD ["nginx", "-g", "daemon off;"]
