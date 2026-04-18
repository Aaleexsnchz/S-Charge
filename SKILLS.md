# Claude Code Skills — Installed Reference

Current skills available to Claude Code while working on TFM, grouped by scope. Skills are **discoverable by Claude without being listed in a CLAUDE.md** — this document exists for *your* reference, not Claude's.

## Summary

| Scope | Location | Count | Loads when |
| --- | --- | --- | --- |
| Global | `~/.claude/skills/` | 7 | Always, every project |
| Frontend | `frontend/.claude/skills/` | 5 | VS Code opened at `frontend/` |
| Backend | `backend/.claude/skills/` | 1 | VS Code opened at `backend/` |

Claude Code only loads project skills from the **workspace root**, not ancestor directories. So frontend skills don't load when working in `backend/`, and root-level skills don't load when working in either package.

## Global `~/.claude/skills/`

Universal skills available in every project you work on.

| Skill | Source | Purpose |
| --- | --- | --- |
| `find-skills` | vercel-labs/skills | Discover and install new skills |
| `skill-creator` | anthropics/skills | Author your own skills |
| `git-commit` | github/awesome-copilot | Conventional Commits messages |
| `systematic-debugging` | obra/superpowers | Structured debugging workflow |
| `api-design-principles` | wshobson/agents | REST API conventions (used by both FE+BE) |
| `postgresql-table-design` | wshobson/agents | Postgres schema design patterns |
| `multi-stage-dockerfile` | github/awesome-copilot | Docker image optimization |

## Backend `backend/.claude/skills/`

FastAPI / Python stack skills. Load when VS Code is opened at `backend/`.

| Skill | Source | Purpose |
| --- | --- | --- |
| `fastapi-templates` | wshobson/agents | FastAPI route patterns, dependency injection, Pydantic v2 |

Planned additions (install when relevant phase arrives):

- `github/awesome-copilot@pytest-coverage` — before Phase 6 (testing deliverable)

## Frontend `frontend/.claude/skills/`

React / Vite / MUI / PWA stack skills. Load when VS Code is opened at `frontend/`.

| Skill | Source | Purpose |
| --- | --- | --- |
| `frontend-design` | anthropics/skills | General frontend design guidance |
| `react-doctor` | community | Post-change React review |
| `vercel-composition-patterns` | vercel-labs/agent-skills | React composition rules (compound components, state lifting) |
| `vercel-react-best-practices` | vercel-labs/agent-skills | React performance and best practices (ignore Next.js-specific rules) |
| `web-design-guidelines` | vercel-labs/agent-skills | Vercel web design system principles |

Planned additions (defer until needed):

- `alinaqi/claude-bootstrap@pwa-development` — when implementing PWA installability
- `remix-run/agent-skills@react-router-framework-mode` — only if React Router v7 APIs become friction
- `accessibility` + `vitest` — when hitting Phase 6 polish and testing

## Working Workflow

Open the narrowest VS Code workspace for what you're editing:

| Editing... | Open VS Code at | Skills loaded |
| --- | --- | --- |
| `frontend/src/**` | `/home/aaleexsnchz/tfm/frontend` | global + frontend |
| `backend/app/**`, `backend/alembic/**` | `/home/aaleexsnchz/tfm/backend` | global + backend |
| `docker-compose.yml`, `PLAN.md`, root configs | `/home/aaleexsnchz/tfm` | global only |

Two VS Code windows open at once is normal when you're touching both sides in a session.

## Managing Skills

### Add

```bash
# Global — any directory
npx skills add <owner/repo@skill> -g -y

# Backend-only — must cd into backend/
cd /home/aaleexsnchz/tfm/backend
npx skills add <owner/repo@skill> -y

# Frontend-only — must cd into frontend/
cd /home/aaleexsnchz/tfm/frontend
npx skills add <owner/repo@skill> -y
```

At the agents prompt, always select **Claude Code only** to avoid regenerating an `.agents/` directory.

### Remove

```bash
rm -rf ~/.claude/skills/<skill-name>                       # global
rm -rf /home/aaleexsnchz/tfm/backend/.claude/skills/<name>  # backend
rm -rf /home/aaleexsnchz/tfm/frontend/.claude/skills/<name> # frontend
```

### Inspect

```bash
ls ~/.claude/skills/                         # global
ls /home/aaleexsnchz/tfm/backend/.claude/skills/
ls /home/aaleexsnchz/tfm/frontend/.claude/skills/
```

### Update all

```bash
npx skills update
```

## Update This Document

Whenever you add or remove a skill, update the corresponding section here so the reference stays accurate.
