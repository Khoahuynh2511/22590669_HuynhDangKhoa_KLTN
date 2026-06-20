"""
Visited Provinces API Endpoints
Tính năng "Bản đồ khám phá Việt Nam": check-in tỉnh thành + thống kê tiến độ.
Pattern theo favorites.py.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID

from ...core.dependencies import get_current_user
from ...schema.visited_province_schema import (
    AddVisitedRequest,
    AutoCheckinResponse,
    ProvinceListResponse,
    VisitedListResponse,
    VisitedResponse,
)
from ...services.visited_province_service import VisitedProvinceService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_visited_service():
    """Dependency để get VisitedProvinceService instance."""
    return VisitedProvinceService()


@router.get("/provinces", response_model=ProvinceListResponse)
async def get_all_provinces(
    current_user: dict = Depends(get_current_user),
    service: VisitedProvinceService = Depends(get_visited_service),
):
    """
    Lấy 63 tỉnh/thành để render bản đồ.

    Example:
        GET /api/v1/visited-provinces/provinces
    """
    try:
        result = await service.get_all_provinces()
        if result["EC"] != 0:
            raise HTTPException(status_code=500, detail=result["EM"])
        return ProvinceListResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in get_all_provinces endpoint: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/my", response_model=VisitedListResponse)
async def get_my_visited(
    current_user: dict = Depends(get_current_user),
    service: VisitedProvinceService = Depends(get_visited_service),
):
    """
    Lấy danh sách tỉnh đã check-in của user hiện tại + thống kê tiến độ khám phá.

    Example:
        GET /api/v1/visited-provinces/my
    """
    try:
        user_id = current_user["user_id"]
        result = await service.get_user_visited(user_id=user_id)
        if result["EC"] != 0:
            raise HTTPException(status_code=500, detail=result["EM"])
        return VisitedListResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in get_my_visited endpoint: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=VisitedResponse)
async def add_visited(
    request: AddVisitedRequest,
    current_user: dict = Depends(get_current_user),
    service: VisitedProvinceService = Depends(get_visited_service),
):
    """
    Check-in một tỉnh (manual). Idempotent.

    Example:
        POST /api/v1/visited-provinces/
        Body: { "province_id": "07e8c89e-90d4-4ebc-9302-384dc6cb2f0c" }
    """
    try:
        user_id = current_user["user_id"]
        result = await service.add_visited(user_id=user_id, province_id=str(request.province_id))
        if result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        return VisitedResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in add_visited endpoint: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{province_id}", response_model=VisitedResponse)
async def remove_visited(
    province_id: UUID,
    current_user: dict = Depends(get_current_user),
    service: VisitedProvinceService = Depends(get_visited_service),
):
    """
    Bỏ check-in một tỉnh.

    Example:
        DELETE /api/v1/visited-provinces/07e8c89e-90d4-4ebc-9302-384dc6cb2f0c
    """
    try:
        user_id = current_user["user_id"]
        result = await service.remove_visited(user_id=user_id, province_id=str(province_id))
        if result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        return VisitedResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in remove_visited endpoint: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-checkin", response_model=AutoCheckinResponse)
async def trigger_auto_checkin(
    current_user: dict = Depends(get_current_user),
    service: VisitedProvinceService = Depends(get_visited_service),
):
    """
    Đồng bộ tỉnh đã đến từ booking đã xác nhận (tour/hotel).
    Trả về số tỉnh mới check-in + danh sách match (minh bạch).

    Example:
        POST /api/v1/visited-provinces/auto-checkin
    """
    try:
        user_id = current_user["user_id"]
        result = await service.auto_checkin_from_bookings(user_id=user_id)
        if result["EC"] != 0:
            raise HTTPException(status_code=500, detail=result["EM"])
        return AutoCheckinResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in auto_checkin endpoint: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
