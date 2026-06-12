from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PricePoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hour_start: datetime
    price_per_kwh: float
