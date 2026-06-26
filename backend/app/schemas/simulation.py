import uuid
from typing import Literal

from pydantic import BaseModel, Field, model_validator

ChargeType = Literal["AC", "DC"]
PriceSource = Literal["reve_tariff", "pvpc_plus_margin"]


class SimulationRequest(BaseModel):
    vehicle_id: uuid.UUID
    connector_id: uuid.UUID
    soc_from: float = Field(default=20, ge=0, lt=100)
    soc_to: float = Field(default=80, gt=0, le=100)

    @model_validator(mode="after")
    def _soc_window(self) -> "SimulationRequest":
        if self.soc_to <= self.soc_from:
            raise ValueError("soc_to must be greater than soc_from")
        return self


class SimulationResult(BaseModel):
    charge_type: ChargeType
    soc_from: float
    soc_to: float
    energy_kwh: float
    duration_minutes: float
    peak_power_kw: float
    average_power_kw: float
    cost_eur: float | None
    price_per_kwh: float | None
    price_source: PriceSource | None
    pvpc_per_kwh: float | None
    margin_per_kwh: float | None
