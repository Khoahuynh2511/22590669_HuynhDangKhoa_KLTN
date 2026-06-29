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
    BestSeasonResponse,
    FestivalResponse,
    GeocodeResponse,
    PlaceGalleryResponse,
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


@router.get("/gallery", response_model=PlaceGalleryResponse)
async def place_gallery(
    place: str = Query(..., min_length=1, description="Tên địa điểm cần tìm ảnh (vd: Vịnh Hạ Long, Eiffel Tower)"),
    limit: int = Query(12, ge=1, le=24, description="Số ảnh tối đa"),
    service: PlaceSuggestionService = Depends(get_place_suggestion_service),
):
    """
    Thư viện ảnh địa điểm từ Wikimedia Commons (ảnh CC, open-source, không cần key).
    Dùng cho quảng bá: cho user xem ảnh thật của điểm đến.

    Example:
        GET /api/v1/places/gallery?place=Vịnh Hạ Long&limit=12
    """
    try:
        result = await service.get_place_gallery(place_name=place, limit=limit)
        return PlaceGalleryResponse(**result)
    except Exception as e:
        logger.error("Error in place_gallery endpoint: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/best-season", response_model=BestSeasonResponse)
async def best_season(
    lat: float = Query(..., ge=-90, le=90, description="Vĩ độ"),
    lng: float = Query(..., ge=-180, le=180, description="Kinh độ"),
    place: str = Query("", description="Tên địa điểm (chỉ để hiển thị)"),
    service: PlaceSuggestionService = Depends(get_place_suggestion_service),
):
    """
    Gợi ý "mùa đẹp nhất" dựa trên khí hậu lịch sử (Open-Meteo Archive, open-source).
    Trả về 12 tháng (nhiệt độ/mưa trung bình) + các tháng lý tưởng nhất.

    Example:
        GET /api/v1/places/best-season?lat=20.9&lng=107.18&place=Vịnh Hạ Long
    """
    try:
        result = await service.get_best_season(lat=lat, lng=lng, place_name=place)
        return BestSeasonResponse(**result)
    except Exception as e:
        logger.error("Error in best_season endpoint: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/festivals", response_model=FestivalResponse)
async def local_festivals(
    province: Optional[str] = Query(None, description="Tên tỉnh/thành để lọc (best-effort, vd: Huế, Hà Nội)"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Tháng (1-12), bỏ qua để lấy tất cả"),
    region: Optional[str] = Query(None, description="Miền: north/central/south (chỉ Việt Nam)"),
    country: Optional[str] = Query(None, description="Quốc gia: tên (Nhật Bản/Thailand) hoặc mã ISO2 (JP). Để trống = Việt Nam; 'world' = toàn cầu"),
    country_code: Optional[str] = Query(None, description="Mã ISO2 override (vd JP, TH) — cho Nager.Date public holidays"),
    lat: Optional[float] = Query(None, ge=-90, le=90, description="Vĩ độ (dự phòng lọc theo vị trí)"),
    lon: Optional[float] = Query(None, ge=-180, le=180, description="Kinh độ (dự phòng lọc theo vị trí)"),
    service: PlaceSuggestionService = Depends(get_place_suggestion_service),
):
    """
    Lễ hội / sự kiện — TOÀN CẦU, gộp các nguồn open-source (key-free):
    dataset tĩnh (VN) + Wikidata SPARQL (lễ hội văn hóa theo nước) + Nager.Date
    (public holidays có ngày chính xác) + Wikipedia (enrich VN). Lọc theo nước/tỉnh/miền/tháng.

    Example:
        GET /api/v1/places/festivals                                  (Việt Nam, mặc định)
        GET /api/v1/places/festivals?country=world                    (toàn cầu)
        GET /api/v1/places/festivals?country=Nhật+Bản&month=4
        GET /api/v1/places/festivals?country_code=TH
        GET /api/v1/places/festivals?region=central                   (miền Trung VN)
    """
    try:
        result = await service.get_local_festivals(
            province_name=province, month=month, region=region,
            lat=lat, lon=lon, country=country, country_code=country_code,
        )
        return FestivalResponse(**result)
    except Exception as e:
        logger.error("Error in local_festivals endpoint: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
