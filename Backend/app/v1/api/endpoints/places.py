"""
Place Suggestion API Endpoints
Gợi ý điểm đến du lịch toàn cầu (open-source: Nominatim + Overpass + Wikimedia).
Pattern theo visited_provinces.py.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from ...core.dependencies import get_optional_current_user
from ...schema.place_schema import (
    GeocodeResponse,
    PlaceSuggestionResponse,
)
from ...services.place_suggestion_service import PlaceSuggestionService
from ...services.place_collection_service import PlaceCollectionService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_place_suggestion_service():
    """Dependency để get PlaceSuggestionService instance."""
    return PlaceSuggestionService()


def get_place_collection_service():
    return PlaceCollectionService()


@router.get("/suggest", response_model=PlaceSuggestionResponse)
async def suggest_places(
    q: str = Query(..., min_length=1, description="Tên địa điểm cần gợi ý (vd: Paris, Tokyo, Đà Lạt)"),
    limit: int = Query(10, ge=1, le=30, description="Số địa điểm gợi ý tối đa mỗi trang"),
    radius_km: float = Query(15.0, ge=1.0, le=100.0, description="Bán kính tìm POI (km)"),
    offset: int = Query(0, ge=0, description="Phân trang: vị trí bắt đầu (0, limit, 2*limit, ...)"),
    current_user: Optional[dict] = Depends(get_optional_current_user),
    service: PlaceSuggestionService = Depends(get_place_suggestion_service),
    collection_service: PlaceCollectionService = Depends(get_place_collection_service),
):
    """
    Gợi ý các điểm đến / attraction du lịch quanh một địa điểm (toàn cầu).
    Hỗ trợ phân trang qua `offset` + `limit`. Response kèm `total` (tổng số POI)
    để frontend biết còn trang nào để "Xem thêm".

    Example:
        GET /api/v1/places/suggest?q=Paris&limit=12&radius_km=20&offset=0
        GET /api/v1/places/suggest?q=Paris&limit=12&radius_km=20&offset=12
    """
    try:
        result = await service.suggest_places(query=q, limit=limit, radius_km=radius_km, offset=offset)
        if result["EC"] != 0:
            # Không tìm thấy địa điểm -> trả 200 kèm EM (không raise, client tự xử lý).
            return PlaceSuggestionResponse(**result)

        # Nếu user đã login, đánh dấu các place đã lưu vào wishlist.
        if current_user and result.get("places"):
            try:
                saved_ids = await collection_service.get_saved_osm_ids(current_user["user_id"])
                for p in result["places"]:
                    p["saved_by_user"] = p.get("osm_id") in saved_ids
            except Exception as e:
                logger.warning("Could not annotate saved_by_user: %s", e)

        return PlaceSuggestionResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in suggest_places endpoint: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/geocode", response_model=GeocodeResponse)
async def geocode_place(
    q: str = Query(..., min_length=1, description="Tên địa điểm cần geocode"),
    service: PlaceSuggestionService = Depends(get_place_suggestion_service),
):
    """
    Geocode tên địa điểm -> tọa độ (tiện ích cho frontend).

    Example:
        GET /api/v1/places/geocode?q=Hanoi
    """
    try:
        location = await service.geocode_place(q)
        if not location:
            return GeocodeResponse(EC=1, EM=f"Không tìm thấy địa điểm '{q}'", location=None)
        return GeocodeResponse(EC=0, EM="Success", location=location)
    except Exception as e:
        logger.error("Error in geocode_place endpoint: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
