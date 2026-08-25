import uuid
from datetime import datetime, time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.models.charging_point import PricingKind

AggregateStatus = Literal["available", "occupied", "unknown"]


class TariffRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    currency: str
    valid_from: datetime | None
    valid_to: datetime | None


class ConnectorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    standard: str
    format: str
    power_type: str
    max_electric_power: int | None
    max_voltage: int
    max_amperage: int
    pricing_kind: PricingKind
    current_price_per_kwh: float | None
    tariff: TariffRead | None


class EvseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    evse_id: str | None
    physical_reference: str | None
    floor_level: str | None
    capabilities: list[str] | None
    wheelchair_accessibility: str | None
    status: str | None
    connectors: list[ConnectorRead]


class PointRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    name: str | None
    cpo_name: str | None
    address: str
    city: str
    postal_code: str | None
    region: str | None
    state: str | None
    country_code: str
    latitude: float
    longitude: float
    parking_type: str | None
    facilities: list[str] | None
    time_zone: str
    opening_24_7: bool
    opening_hours: list[dict[str, Any]] | None
    charging_when_closed: bool | None
    aggregate_status: AggregateStatus
    evses: list[EvseRead]


class PriceBandRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    start_time: time
    end_time: time
    price_per_kwh: float
    is_current: bool


class ConnectorScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    connector_ids: list[uuid.UUID]
    bands: list[PriceBandRead]


class PointDetailRead(PointRead):
    """One point, with the price schedules its connectors are charged by.

    Separate from ``PointRead`` because ``GET /points`` takes a bbox and has no
    limit: resolving bands for every connector in a viewport would serve a list
    that shows none of them.
    """

    price_schedules: list[ConnectorScheduleRead]
