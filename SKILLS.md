# Skills

Claude Code agent skills used in this project. The installed skill files live under
`.claude/skills/` (gitignored — they're fetched upstream, not authored here); this file plus
[skills-lock.json](skills-lock.json) are the committed, reproducible record of *which* skills
and *which version*.

## Installed

| Skill | Source | Pinned hash |
| --- | --- | --- |
| [frontend-design](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md) | `anthropics/skills` (GitHub) | `4eabc66…` |

## Installing on a fresh clone

`.claude/skills/` is gitignored, so after cloning you materialise the skills from the lock:

1. Each entry in [skills-lock.json](skills-lock.json) pins a skill to its `source`, `skillPath`
   and a content `computedHash`.
2. Install with the skill manager that wrote `skills-lock.json`, or manually: copy the upstream
   `skillPath` (e.g. `skills/frontend-design/SKILL.md` from `github.com/anthropics/skills`) into
   `.claude/skills/<name>/SKILL.md`.
3. Confirm it's picked up — the skill shows up in Claude Code's available skills.

When you add or update a skill, commit the updated `skills-lock.json` (and a row above) so the
set stays reproducible.
