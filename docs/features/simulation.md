# Pre-charge simulation

**Status:** ✅ Implemented · **Shipped in** [Phase 3](../phases/phase-3.md)

Before plugging in, a driver picks their car model and a connector and gets the predicted duration, energy and cost of the charge. Spec-based, not measured: power is `min(vehicle, connector)`, AC is flat, DC tapers above 80% SoC.

**This is the quote step of a [charging session](sessions.md).** It stands alone today, and from Phase 10 it is what a driver accepts or declines before a session starts — the number it returns is the amount held against their [wallet](wallet.md). Nothing about the model changes; what changes is that its answer becomes binding, so a session records this prediction rather than computing a second one of its own.

## Today

- **Backend** — `POST /api/simulate` over the simulation service. Cost is the sum over SoC steps of the energy each delivers times the band pricing the minute it arrives, so a session crossing a band boundary is billed at both; the result reports the effective price, the cost divided by the energy priced.
- **A connector with no published price has no cost.** Duration and energy still come back. The `PVPC + margen` estimate that used to fill the gap presented a guess as the operator's price — it survives in `services/price_suggestion.py` as the suggestion an owner gets for their own point ([Phase 7](../plan.md)), with no caller until then.
- **Frontend** — `features/simulate`: the "Simular carga" dialog on point detail (vehicle picker, connector context, SoC range, result metrics).

## Known limitations of the cost

Both push the real bill **above** the quote, never below, so a driver is never
surprised by a number larger than the one they accepted.

- **Charging losses are not modelled.** The simulation computes energy *into the
  battery* (`battery_kwh × ΔSoC`); the charger bills what it *delivers* through
  the cable, which is 5-10% more on DC and 10-15% more on AC. The quote undershoots
  the meter by roughly that margin.
- **VAT handling is unresolved.** `tariff_elements.vat` is parsed and stored (1,780
  ENERGY components carry `21.00`) but never applied to the cost. Under a strict OCPI
  reading `price` excludes VAT, which would make every quote 21% low; in practice
  Spanish CPOs tend to publish the retail price. The data cannot settle it — it needs
  one manual comparison against a charger whose real tariff is visible on site.

Neither is a defect in the arithmetic. At the catalogue's own medians (0,322 €/kWh
AC, 0,447 €/kWh DC across 38,552 priced connectors) a 60 kWh car charging 20% to 80%
costs 11,60 € on AC and 16,09 € on DC, which is what Spanish public charging
actually costs. A quote above 10 € is the expected result, not a sign of a bug.

## Related

Algorithm chapter: [thesis/simulacion-de-recarga.md](../thesis/simulacion-de-recarga.md).

## Pending

- **Charging-curve chart.** The model can already produce a real power-vs-SoC curve; showing it needs a small `/api/simulate` addition plus a chart component. A genuine enhancement, not a mock — it shipped as metrics only.
