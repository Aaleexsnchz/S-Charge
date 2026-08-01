# Pre-charge simulation

**Status:** ✅ Implemented · **Shipped in** [Phase 3](../phases/phase-3.md)

Before plugging in, a driver picks their car model and a connector and gets the predicted duration, energy and cost of the session. Spec-based, not measured: power is `min(vehicle, connector)`, AC is flat, DC tapers above 80% SoC.

## Today

- **Backend** — `POST /api/simulate` over the simulation service; cost comes from the point's REVE tariff, or the price cascade where there is none.
- **Frontend** — `features/simulate`: the "Simular carga" dialog on point detail (vehicle picker, connector context, SoC range, result metrics).

## Related

Algorithm chapter: [thesis/simulacion-de-recarga.md](../thesis/simulacion-de-recarga.md).

## Pending

- **Charging-curve chart.** The model can already produce a real power-vs-SoC curve; showing it needs a small `/api/simulate` addition plus a chart component. A genuine enhancement, not a mock — it shipped as metrics only.
