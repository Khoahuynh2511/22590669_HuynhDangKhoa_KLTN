"""
Shared Itineraries API Endpoints
Tính năng chia sẻ lịch trình công khai (QR + link) — nhóm "viral".
- POST /share   (cần login): tạo link chia sẻ từ nội dung lịch trình.
- GET  /{id}    (public)   : xem lịch trình read-only.
Pattern theo visited_provinces.py.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException

from ...core.dependencies import get_current_user
from ...schema.shared_itinerary_schema import (
    CreateShareRequest,
    CreateShareResponse,
    SharedItineraryResponse,
)
from ...services.shared_itinerary_service import SharedItineraryService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_shared_itinerary_service():
    """Dependency để get SharedItineraryService instance."""
    return SharedItineraryService()


@router.post("/share", response_model=CreateShareResponse)
async def create_share(
    request: CreateShareRequest,
    current_user: dict = Depends(get_current_user),
    service: SharedItineraryService = Depends(get_shared_itinerary_service),
):
    """
    Tạo link chia sẻ lịch trình công khai (cho QR / share MXH).

    Example:
        POST /api/v1/itineraries/share
        Body: { "title": "Đà Lạt 3N2Đ", "payload": { ... } }
    """
    try:
        user_id = current_user["user_id"]
        result = await service.create_share(user_id=user_id, payload=request.payload, title=request.title)
        if result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        return CreateShareResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in create_share endpoint: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{share_id}", response_model=SharedItineraryResponse)
async def get_shared_itinerary(
    share_id: str,
    service: SharedItineraryService = Depends(get_shared_itinerary_service),
):
    """
    Xem lịch trình chia sẻ công khai (KHÔNG cần auth). Tăng view_count mỗi lượt xem.

    Example:
        GET /api/v1/itineraries/abc-123
    """
    try:
        result = await service.get_shared(share_id=share_id)
        if result["EC"] != 0:
            raise HTTPException(status_code=404, detail=result["EM"])
        return SharedItineraryResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in get_shared_itinerary endpoint: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
