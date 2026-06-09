"""
Hotel API Endpoints - Public
"""
from fastapi import APIRouter, Query, Depends
from typing import Optional

from ...services.hotel_service import get_hotel_service, HotelService

router = APIRouter()


@router.get("")
async def get_hotels(
    location: Optional[str] = Query(None, description="Lọc theo địa điểm"),
    search: Optional[str] = Query(None, description="Tìm theo tên/địa điểm"),
    min_price: Optional[float] = Query(None, ge=0, description="Giá tối thiểu"),
    max_price: Optional[float] = Query(None, ge=0, description="Giá tối đa"),
    limit: Optional[int] = Query(None, ge=1, le=100),
    offset: Optional[int] = Query(None, ge=0),
    service: HotelService = Depends(get_hotel_service)
):
    """Lấy danh sách khách sạn"""
    return service.get_all_hotels(
        location=location, search=search,
        min_price=min_price, max_price=max_price,
        limit=limit, offset=offset
    )


@router.get("/locations")
async def get_hotel_locations(
    service: HotelService = Depends(get_hotel_service)
):
    """Lấy danh sách địa điểm có khách sạn"""
    return service.get_hotel_locations()


@router.get("/{hotel_id}")
async def get_hotel(
    hotel_id: str,
    service: HotelService = Depends(get_hotel_service)
):
    """Lấy chi tiết khách sạn"""
    result = service.get_hotel_by_id(hotel_id)
    if result["EC"] == 1:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=result["EM"])
    return result
