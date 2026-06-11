"""
Train API Endpoints - Public
Query real database instead of mock data
"""
from fastapi import APIRouter, Query, Depends
from typing import Optional

from ...services.train_search_service import get_train_search_service, TrainSearchService

router = APIRouter()


@router.get("/stations")
async def get_stations(
    service: TrainSearchService = Depends(get_train_search_service)
):
    """Lay danh sach ga tau"""
    return service.get_stations()


@router.get("/types")
async def get_train_types(
    service: TrainSearchService = Depends(get_train_search_service)
):
    """Lay danh sach loai tau + loai ghe"""
    return service.get_types()


@router.get("/search")
async def search_trains(
    departure: str = Query(..., description="Ma ga di"),
    arrival: str = Query(..., description="Ma ga den"),
    date: Optional[str] = Query(None, description="Ngay di (YYYY-MM-DD)"),
    limit: int = Query(10, ge=1, le=20, description="So ket qua toi da"),
    service: TrainSearchService = Depends(get_train_search_service)
):
    """Tim kiem tau hoa"""
    return service.search_trains(departure, arrival, date, limit)
