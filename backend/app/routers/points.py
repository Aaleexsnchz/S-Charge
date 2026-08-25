import uuid
from decimal import Decimal, InvalidOperation
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.point import ConnectorScheduleRead, PointDetailRead, PointRead
from app.services.points import Bbox, get_point, list_points, map_feature_collection
from app.services.tariff_pricing import point_price_schedules

router = APIRouter(prefix="/points", tags=["points"])

NOT_FOUND_BODY = {"status_code": 404, "status_message": "Charging point not found"}

BBOX_PARTS = 4

BBOX_DESCRIPTION = (
    "Bounding box as 'min_lng,min_lat,max_lng,max_lat' (GeoJSON axis order)."
)


def _parse_bbox(raw: str) -> Bbox:
    parts = raw.split(",")
    if len(parts) != BBOX_PARTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=BBOX_DESCRIPTION
        )
    try:
        min_lng, min_lat, max_lng, max_lat = (Decimal(part) for part in parts)
    except InvalidOperation as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=BBOX_DESCRIPTION
        ) from exc
    return min_lng, min_lat, max_lng, max_lat


@router.get("", response_model=list[PointRead])
async def read_points(
    db: Annotated[AsyncSession, Depends(get_db)],
    bbox: Annotated[str | None, Query(description=BBOX_DESCRIPTION)] = None,
    connector_standard: Annotated[
        str | None, Query(description="OCPI connector standard, e.g. IEC_62196_T2.")
    ] = None,
    max_price_per_kwh: Annotated[Decimal | None, Query(ge=0)] = None,
) -> list[PointRead]:
    points = await list_points(
        db,
        bbox=_parse_bbox(bbox) if bbox is not None else None,
        connector_standard=connector_standard,
        max_price_per_kwh=max_price_per_kwh,
    )
    return [PointRead.model_validate(point) for point in points]


@router.get("/map")
async def read_points_map(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    """GeoJSON FeatureCollection sized for the map's clustered source.

    Declared before ``/{point_id}`` so the literal segment wins the route match.
    """
    return await map_feature_collection(db)


@router.get(
    "/{point_id}",
    response_model=PointDetailRead,
    responses={404: {"description": "Unknown point; body mirrors REVE's error shape."}},
)
async def read_point(
    point_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    point = await get_point(db, point_id)
    if point is None:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND, content=NOT_FOUND_BODY
        )
    schedules = await point_price_schedules(db, point_id)
    detail = PointDetailRead(
        **PointRead.model_validate(point).model_dump(),
        price_schedules=[
            ConnectorScheduleRead.model_validate(schedule) for schedule in schedules
        ],
    )
    return JSONResponse(content=detail.model_dump(mode="json"))
