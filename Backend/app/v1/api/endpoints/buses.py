"""
Bus API Endpoints - Public
Query real database instead of mock data
"""
from fastapi import APIRouter, Query, Depends
from typing import Optional

from ...services.bus_search_service import get_bus_search_service, BusSearchService

router = APIRouter()


@router.get("/stations")
async def get_stations(
    service: BusSearchService = Depends(get_bus_search_service)
):
    """Lay danh sach ben xe"""
    return service.get_stations()


@router.get("/types")
async def get_bus_types(
    service: BusSearchService = Depends(get_bus_search_service)
):
    """Lay danh sach loai xe + loai ghe"""
    return service.get_types()


@router.get("/search")
async def search_buses(
    departure: str = Query(..., description="Ma ben di"),
    arrival: str = Query(..., description="Ma ben den"),
    date: Optional[str] = Query(None, description="Ngay di (YYYY-MM-DD)"),
    limit: int = Query(10, ge=1, le=20, description="So ket qua toi da"),
    service: BusSearchService = Depends(get_bus_search_service)
):
    """Tim kiem xe khach"""
    return service.search_buses(departure, arrival, date, limit)
