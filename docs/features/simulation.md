# Pre-charge simulation

**Status:** ✅ Implemented · **Shipped in** [Phase 3](../phases/phase-3.md)

Before plugging in, a driver picks their car model and a connector and gets the predicted duration, energy and cost of the charge. Spec-based, not measured: power is `min(vehicle, connector)`, AC is flat, DC tapers above 80% SoC.

## Today

- **Backend** — `POST /api/simulate` over the simulation service. Cost is the sum over SoC steps of the energy each delivers times the band pricing the minute it arrives, so a session crossing a band boundary is billed at both; the result reports the effective price, the cost divided by the energy priced.
- **A connector with no published price has no cost.** Duration and energy still come back. The `PVPC + margen` estimate that used to fill the gap presented a guess as the operator's price — it survives in `services/price_suggestion.py` as the suggestion an owner gets for their own point ([Phase 7](../plan.md)), with no caller until then.
- **Frontend** — `features/simulate`: the "Simular carga" dialog on point detail (vehicle picker, connector context, SoC range, result metrics).

## Related

Algorithm chapter: [thesis/simulacion-de-recarga.md](../thesis/simulacion-de-recarga.md).

## Pending

- **Charging-curve chart.** The model can already produce a real power-vs-SoC curve; showing it needs a small `/api/simulate` addition plus a chart component. A genuine enhancement, not a mock — it shipped as metrics only.
