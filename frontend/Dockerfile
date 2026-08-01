# syntax=docker/dockerfile:1.7

ARG NODE_VERSION=24

# ---------- deps: install with pinned standalone pnpm + BuildKit store cache ----------
FROM node:${NODE_VERSION}-alpine AS deps
WORKDIR /app
RUN npm install -g pnpm@11
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN --mount=type=cache,id=pnpm-store,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile

# ---------- build: produce dist/ for production serving ----------
FROM deps AS build
COPY . .
RUN pnpm build

# ---------- prod: serve built assets via nginx (opt-in via --target prod) ----------
FROM nginx:1.27-alpine AS prod
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
