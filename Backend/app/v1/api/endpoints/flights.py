"""
Flight API Endpoints - Public
Query real database instead of mock data
"""
from fastapi import APIRouter, Query, Depends
from typing import Optional

from ...services.flight_search_service import get_flight_search_service, FlightSearchService

router = APIRouter()


@router.get("/airports")
async def get_airports(
    service: FlightSearchService = Depends(get_flight_search_service)
):
    """Lay danh sach san bay"""
    return service.get_airports()


@router.get("/airlines")
async def get_airlines(
    service: FlightSearchService = Depends(get_flight_search_service)
):
    """Lay danh sach hang bay"""
    return service.get_airlines()


@router.get("/search")
async def search_flights(
    departure: str = Query(..., description="Ma san bay di"),
    arrival: str = Query(..., description="Ma san bay den"),
    date: Optional[str] = Query(None, description="Ngay di (YYYY-MM-DD)"),
    limit: int = Query(10, ge=1, le=20, description="So ket qua toi da"),
    service: FlightSearchService = Depends(get_flight_search_service)
):
    """Tim kiem chuyen bay"""
    return service.search_flights(departure, arrival, date, limit)
