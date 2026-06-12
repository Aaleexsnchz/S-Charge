"""Idempotent seed of the curated EV catalogue.

Specs (usable battery kWh, max AC kW, max DC kW) from public manufacturer
spec sheets; close-enough values for simulation purposes, not official data.
"""

import asyncio
import sys
import uuid

from sqlalchemy.dialects.postgresql import insert

from app.database import SessionLocal
from app.models.vehicle import Vehicle

CCS = "IEC_62196_T2_COMBO"
CHADEMO = "CHADEMO"

# (make, model, battery_kwh, max_ac_kw, max_dc_kw, dc_connector)
VEHICLES: list[tuple[str, str, float, float, float | None, str | None]] = [
    ("Audi", "Q4 e-tron 40", 77.0, 11.0, 135.0, CCS),
    ("BMW", "i4 eDrive40", 80.7, 11.0, 205.0, CCS),
    ("BYD", "Atto 3", 60.5, 11.0, 88.0, CCS),
    ("Citroën", "ë-C4", 46.3, 11.0, 100.0, CCS),
    ("Cupra", "Born 58", 58.0, 11.0, 120.0, CCS),
    ("Dacia", "Spring", 26.8, 6.6, 30.0, CCS),
    ("Fiat", "500e", 37.3, 11.0, 85.0, CCS),
    ("Ford", "Mustang Mach-E ER", 91.0, 11.0, 150.0, CCS),
    ("Hyundai", "Ioniq 5", 72.6, 11.0, 220.0, CCS),
    ("Hyundai", "Kona Electric 64", 64.0, 11.0, 77.0, CCS),
    ("Kia", "e-Niro 64", 64.0, 11.0, 77.0, CCS),
    ("Kia", "EV6", 77.4, 11.0, 240.0, CCS),
    ("Mercedes-Benz", "EQA 250", 66.5, 11.0, 100.0, CCS),
    ("MG", "MG4 Long Range", 61.7, 11.0, 135.0, CCS),
    ("MG", "ZS EV", 68.3, 11.0, 92.0, CCS),
    ("Mini", "Cooper SE", 28.9, 11.0, 50.0, CCS),
    ("Nissan", "Leaf 40", 39.0, 6.6, 46.0, CHADEMO),
    ("Opel", "Corsa-e", 46.3, 11.0, 100.0, CCS),
    ("Peugeot", "e-208", 46.3, 11.0, 100.0, CCS),
    ("Porsche", "Taycan", 79.2, 11.0, 225.0, CCS),
    ("Renault", "Mégane E-Tech EV60", 60.0, 22.0, 130.0, CCS),
    ("Renault", "Zoe ZE50", 52.0, 22.0, 46.0, CCS),
    ("Seat", "Mii Electric", 32.3, 7.2, 40.0, CCS),
    ("Skoda", "Enyaq 80", 77.0, 11.0, 135.0, CCS),
    ("Smart", "EQ Fortwo", 16.7, 22.0, None, None),
    ("Tesla", "Model 3 RWD", 57.5, 11.0, 170.0, CCS),
    ("Tesla", "Model Y Long Range", 75.0, 11.0, 250.0, CCS),
    ("Toyota", "bZ4X", 71.4, 11.0, 150.0, CCS),
    ("Volkswagen", "ID.3 Pro", 58.0, 11.0, 120.0, CCS),
    ("Volkswagen", "ID.4 Pro", 77.0, 11.0, 135.0, CCS),
    ("Volvo", "XC40 Recharge", 78.0, 11.0, 150.0, CCS),
]


async def seed() -> int:
    async with SessionLocal() as db:
        for make, model, battery, ac, dc, dc_std in VEHICLES:
            payload = {
                "id": uuid.uuid4(),
                "make": make,
                "model": model,
                "battery_kwh": battery,
                "max_ac_kw": ac,
                "max_dc_kw": dc,
                "dc_connector": dc_std,
            }
            stmt = insert(Vehicle).values(**payload)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_vehicles_make_model",
                set_={k: stmt.excluded[k] for k in payload if k not in ("id", "make", "model")},
            )
            await db.execute(stmt)
        await db.commit()
    print(f"{len(VEHICLES)} vehicles seeded")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(seed()))
