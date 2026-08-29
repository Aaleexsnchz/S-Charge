# Open from earlier phases

A phase closes when it has delivered what [plan.md](../plan.md) asks of it. Anything still open that blocks nothing stays visible here, so starting a later phase never means losing sight of it.

**This is an index, not a second copy.** One line per item; the detail lives in the phase plan that owns it, and that plan stays the source of truth. Two rules keep it honest:

- **An item that blocks the current phase is not carry-over.** It becomes a slice of the phase it blocks, and its row leaves this file.
- **A row is deleted when the item is done**, in the same change that closes it — not marked resolved. Git holds the history.

Items scheduled into a *later* phase are not carry-over either: those live in [plan.md](../plan.md) under the phase that will do them, and in [production-readiness.md](../production-readiness.md) when they are gaps rather than tasks.

| From | Item | Needs | Detail |
| --- | --- | --- | --- |
| 2 | Map viewport loading — open-on-position, zoom-gated `bbox` fetch, padded cache | Phase 14 | [features/map.md](../features/map.md) |
| 5 · 7 | Server-side `.env` written with every secret rotated | host | [phase-5](phase-5.md#slice-7--first-deploy) |
| 5 · 7 | Verify on a phone: the site loads and the PWA installs | a phone | [phase-5](phase-5.md#slice-7--first-deploy) |
| 5 · 8 | Google OAuth + Resend against the production origin, for users other than the owner | host, Google + Resend consoles | [phase-5](phase-5.md#slice-8--external-services-on-the-prod-origin) |
| 5 · 10 | Security gate, laptop cutover, backup cron on the server | host | [phase-5](phase-5.md#slice-10--security-gate-cutover-first-release) |
| 5 · 13 | Re-check the auth rate limits on the deployed instance, against a real public IP | host | [phase-5](phase-5.md#slice-13--auth-surface-hardening) |
| 5 · 15 | Browser click-through after login — the one claim resting on argument rather than a run | — | [phase-5](phase-5.md#slice-15--authenticate-the-read-endpoints-x) |
| 6 | `CONGESTION_TIME` bands are never priced — 218 rows carry a component type absent from REVE's enum | a reason to care | [features/points.md](../features/points.md) |
| 6 | `price` is ex-VAT per OCPI and the app does not say so | a decision on what the driver is shown | [features/points.md](../features/points.md) |
| 6 | A failing REVE target stalls the ones below it silently — nothing alerts, only `--status` shows it | a way to notice without looking | [operations.md](../operations.md) |
| 6 | An alternative to `supercronic` is investigated and a decision recorded either way — it is an amd64-only binary in the critical path of the one job that must not silently stop | time, and no downstream work | [plan](../plan.md#phase-6--etl-reactivation--price-model--done-v020) |

## Open decisions

| From | Decision | Decide by |
| --- | --- | --- |
| 5 | Whether to keep registration invite-only during the demo window — [phase-5](phase-5.md#open-decision) | before the URL is shared |
