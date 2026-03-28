# Backend

## Quality Checks

Run from the `backend/` directory:

```bash
uv sync --locked --all-groups
uv run ruff check app
uv run ruff format --check app
uv run mypy app
```

Auto-fix formatting/lint issues:

```bash
uv run ruff check app --fix
uv run ruff format app
```
