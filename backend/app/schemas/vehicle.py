import uuid

from pydantic import BaseModel, ConfigDict


class VehicleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    make: str
    model: str
    battery_kwh: float
    max_ac_kw: float
    max_dc_kw: float | None
    dc_connector: str | None
