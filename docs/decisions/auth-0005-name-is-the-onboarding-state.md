---
id: auth-0005
status: accepted
phase: 8
date: 2026-08
related: [auth-0001]
---

# auth-0005: A mandatory display name, with the null name as its own onboarding state

> The app greets the user by name. That turns an optional profile field into a required one, and raises the question of how the app knows whether a user has finished setting themselves up.

## Context

The dashboard opens with *Hola, {nombre}* and falls back to a bare *Hola* when `users.name` is null. The fallback is not a rendering detail — it is the app's first line, and it reads as broken.

`name` was optional because nothing depended on it. Two paths produce a null one:

- **Google sign-in.** `fastapi-users` provisions an OAuth user from the id and email alone; `httpx-oauth`'s Google client asks the People API for `emailAddresses` only, so no name ever reaches the callback.
- **Accounts created before the rule**, including every account in the database today.

Making registration require a name closes neither path. Something has to ask the users who already exist.

## Decision

**The name is required**, enforced at the edge: `UserCreate.name` is a non-empty, whitespace-stripped string of at most 100 characters, and `UserUpdate` refuses to clear it — an explicit `{"name": null}` is a `422`, while omitting the key leaves the stored value untouched.

**A null name is itself the unfinished-onboarding state.** No column, no flag, no status enum. `OnboardingGate` sits inside the protected route tree, above the layout, and renders a name prompt instead of the app whenever the session's user has no name. It clears the moment the name is stored, because the root loader revalidates after the action.

**Setting it and editing it are the same endpoint.** `PATCH /api/users/me` already existed and already accepted `name`; the onboarding prompt and the profile screen post to one action.

## Rationale

The alternative on the table was an `onboarding_status` column — or its lighter form, `onboarding_completed_at`. Both store a fact the database already answers. A user who has completed onboarding is a user with a name; a second column asserting the same thing can disagree with the first, and then something has to decide which one is right.

Deriving it also costs nothing to read. `GET /api/users/me` is already fetched by the React Router root loader on every page load, so the gate is a property of data the frontend holds regardless. A column would have to be added, migrated, backfilled for existing rows, and kept in step by every write path that touches the name.

**A gate, not a redirect.** Wrapping the protected subtree cannot be navigated around and cannot loop: there is no onboarding *route* to exclude from its own guard, and no URL that renders the app with the gate unsatisfied. A `/onboarding` redirect would need the guard to make an exception for its own target, which is the shape that produces redirect loops.

**The line where the rule is enforced is the API, not the schema.** `users.name` stays nullable, because the rows that predate the rule have no name to backfill with and inventing one to satisfy a `NOT NULL` would put fiction in the database to satisfy a constraint. The column can be tightened once no null rows remain.

## Consequences

- Every screen behind the session can assume a name. The dashboard greeting has no fallback branch to maintain.
- Existing users — including every Google account — meet the prompt once, on their next visit. It offers *cerrar sesión*, so nobody is trapped by it.
- Onboarding growing past one field reopens this. A second step the user may skip makes "skipped" and "never started" indistinguishable, and *that* is when a timestamp earns its place — not before.

## Rejected alternatives

- **An `onboarding_status` enum.** Resumable multi-step onboarding is the case it serves, and onboarding is one field. It stores derivable state and introduces a second source of truth for it.
- **An `onboarding_completed_at` timestamp.** The same objection while the name is mandatory and unskippable. It is the right answer *if* a skippable step is ever added, and is the first thing to reach for then.
- **Reading the name from Google's profile on sign-in.** It would spare OAuth users the prompt, but it means a second call to Google inside the login callback — a new failure mode on the most critical route in the app — and the gate still has to exist for accounts that predate the rule. `picture_url` is unwritten for the same reason.
- **A dedicated `POST /api/users/me/name` endpoint.** The generic `PATCH` already does this, with `safe=True` stripping `is_superuser`, `is_active` and `is_verified` from the payload. A second endpoint would be a narrower door onto the same room.

## References

- [features/auth.md](../features/auth.md) — what authentication does today
- [auth-0001](auth-0001-fastapi-users.md) — why the user routers are `fastapi-users`' rather than hand-written
