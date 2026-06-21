from decimal import Decimal

from app.models.vehicle import Vehicle
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


async def test_list_vehicles_ordered(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    db_session.add_all(
        [
            Vehicle(
                make="Tesla",
                model="Model 3 RWD",
                battery_kwh=Decimal("57.5"),
                max_ac_kw=Decimal("11.0"),
                max_dc_kw=Decimal("170.0"),
                dc_connector="IEC_62196_T2_COMBO",
            ),
            Vehicle(
                make="Dacia",
                model="Spring",
                battery_kwh=Decimal("26.8"),
                max_ac_kw=Decimal("6.6"),
                max_dc_kw=Decimal("30.0"),
                dc_connector="IEC_62196_T2_COMBO",
            ),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/vehicles")

    assert response.status_code == 200
    body = response.json()
    assert [item["make"] for item in body] == ["Dacia", "Tesla"]
    assert body[1]["battery_kwh"] == 57.5
    assert body[1]["dc_connector"] == "IEC_62196_T2_COMBO"
