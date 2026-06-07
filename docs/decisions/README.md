# Architectural Decision Records

Per-decision records for the load-bearing architectural choices in TFM. Format is a lightweight [MADR](https://adr.github.io/madr/) variant: front-matter with id / status / phase, then the decision body (Decision · Rationale · Implementation · Rejected alternatives · References).

ADRs are append-only — when a decision is revised, append a dated revisions block at the top of the file rather than editing the body in place. Superseded ADRs keep their content and gain a `superseded_by:` field. See the root [CLAUDE.md](../../CLAUDE.md) "Documentation discipline" section for the workflow.

## Auth

| ID | Title | Phase |
| --- | --- | --- |
| [auth-0001](auth-0001-fastapi-users.md) | Use `fastapi-users` as the authentication library | Slice 1 |
| [auth-0002](auth-0002-cookie-session.md) | Single HttpOnly cookie session, no refresh tokens | Slice 1 |
| [auth-0003](auth-0003-preregistration-shell-mitigation.md) | Pre-registration shell attack mitigation (verify gate + OAuth-link hash reset) | Slice 3 |

Concept-level summary of what the library and these ADRs deliver: [thesis/auth.md](../thesis/auth.md).

## Frontend

| ID | Title | Phase |
| --- | --- | --- |
| [fe-0001](fe-0001-mui.md) | Use MUI (Material UI) as the frontend component library | Slice 4 |
| [fe-0002](fe-0002-pwa.md) | Ship the frontend as an installable Progressive Web App | Slice 4 |

## Thesis-writeup chapters

Concept-level summaries written for the thesis document, with links to the ADRs above for the deep rationale:

| File | Coverage |
| --- | --- |
| [../thesis/auth.md](../thesis/auth.md) | Auth — identity, password storage, session, OAuth, verification, audit, rate limiting. |
| [../thesis/session-theft.md](../thesis/session-theft.md) | Session theft and bearer-token replay — threat model for infostealer + cookie replay, what an application can and cannot defend against, DBSC / WebAuthn step-up as the defensive frontier, what this project's session does and explicitly does not. |

## Adding a new ADR

1. Pick the next free number in the relevant area (`auth-NNNN`, `fe-NNNN` for frontend, future `be-NNNN` for backend non-auth, `infra-NNNN` for deployment).
2. Copy an existing ADR as a template; fill in the front-matter (`id`, `status`, `phase`, `date`, optional `related: [auth-NNNN, ...]` for cross-refs). The body `# id: Title` heading is the canonical title — don't duplicate it in front-matter.
3. Add the row to this index in the right table.
4. Update any references in [PLAN.md](../PLAN.md), [README.md](../../README.md), or `CLAUDE.md` files if the new ADR locks a previously open question.
5. Commit with the code change that implements the decision (or with a `docs(adr):` commit when the decision is recorded ahead of implementation).
