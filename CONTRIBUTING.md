# Contributing Guide (Solo Project)

This repository is maintained by one developer. The goal is to keep quality high without adding unnecessary process.

## Quick Workflow

1. Sync: `git checkout main && git pull`
2. Start work:
   - Small low-risk change: commit directly on `main`
   - Medium/high-risk change: `git checkout -b <type>/<scope>-<short-description>`
3. Commit using Conventional Commits:
   - Example: `git commit -m "feat(backend): add user profile endpoint"`
4. Push:
   - `git push -u origin <branch>` for branch work
   - `git push origin main` for direct `main` commits
5. Optional PR (recommended for non-trivial changes):
   - Open PR, self-review, squash merge into `main`
6. After merge, cleanup:
   - `git checkout main && git pull && git branch -d <branch>`

## 1. Branching Policy

### 1.1 Default Branch

- `main` should stay stable.
- Direct commits to `main` are allowed for very small, low-risk changes.
- Use feature branches for medium or high-risk work.

### 1.2 When To Use A Branch

Create a branch for:

- New features
- Bug fixes that touch multiple files
- Refactors
- Dependency upgrades
- Anything that could break behavior

Recommended branch naming:

- `feat/<scope>-<short-description>`
- `fix/<scope>-<short-description>`
- `chore/<scope>-<short-description>`
- `docs/<scope>-<short-description>`
- `refactor/<scope>-<short-description>`
- `test/<scope>-<short-description>`

`<scope>` is usually one of: `backend`, `frontend`, `root`, `infra`.

### 1.3 Branch Lifetime

- Keep branches short-lived (ideally 1-3 days).
- Rebase or merge `main` if work stays open longer.
- Prefer small focused changes over large batches.

## 2. Commit Policy

### 2.1 Commit Message Format

Use Conventional Commits:

`<type>(<scope>): <short imperative summary>`

Examples:

- `feat(backend): add health check endpoint`
- `fix(frontend): handle empty API response`
- `chore(root): update docker compose docs`

Allowed types:

- `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `build`, `ci`

### 2.2 Commit Rules

- One logical change per commit.
- Keep commits atomic and reversible.
- Do not mix unrelated changes in one commit.
- Include tests with the code change when practical.

### 2.3 Pre-Commit Checklist

- App runs locally.
- Relevant tests pass.
- Lint/format checks pass.
- No secrets or credentials are committed.

## 3. Pull Requests (Optional But Recommended)

For solo projects, PRs are optional. Use them when the change is non-trivial.

Use a PR when:

- You want a clean review trail.
- The change is risky or large.
- You want to document why a decision was made.

If you create a PR:

- Title it with Conventional Commits style.
- Add a short description: what changed, why, and how you tested it.
- Squash merge to keep history clean.

## 4. Hotfix Flow

For urgent production issues:

- Create `fix/<scope>-<description>` from `main`.
- Keep the fix minimal.
- Merge quickly after basic validation.
- Add a follow-up cleanup task if needed.

## 5. GitHub Protections For Solo Work

Recommended minimal protections on `main`:

- Block force pushes.
- Block branch deletion.

Optional protections if you want stricter flow:

- Require PR before merge.
- Require status checks to pass.

## 6. Practical Examples

- Small typo in docs:
  - Direct commit to `main`
  - `docs(root): fix typo in setup section`

- New backend endpoint:
  - Branch: `feat/backend-user-profile-endpoint`
  - Commit: `feat(backend): add user profile endpoint`

- Frontend bug fix:
  - Branch: `fix/frontend-navbar-overlap`
  - Commit: `fix(frontend): fix navbar overlap on mobile`
