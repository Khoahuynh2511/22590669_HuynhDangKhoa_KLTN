"""
Place Collection API Endpoints
"Bộ sưu tập" của user: wishlist địa điểm (save/remove/list) + gộp nơi đã đến.
Pattern theo visited_provinces.py.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from ...core.dependencies import get_current_user
from ...schema.place_schema import (
    CombinedCollectionResponse,
    PlaceCollectionResponse,
    PlaceExistsResponse,
    SavePlaceRequest,
    SavePlaceResponse,
)
from ...services.place_collection_service import PlaceCollectionService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_place_collection_service():
    """Dependency để get PlaceCollectionService instance."""
    return PlaceCollectionService()


@router.get("/", response_model=PlaceCollectionResponse)
async def list_saved_places(
    current_user: dict = Depends(get_current_user),
    service: PlaceCollectionService = Depends(get_place_collection_service),
):
    """
    Lấy wishlist địa điểm của user hiện tại.

    Example:
        GET /api/v1/place-collections/
    """
    try:
        user_id = current_user["user_id"]
        result = await service.list_user_saves(user_id=user_id)
        if result["EC"] != 0:
            raise HTTPException(status_code=500, detail=result["EM"])
        return PlaceCollectionResponse(
            EC=result["EC"],
            EM=result["EM"],
            total=result["total"],
            wishlist=result["saves"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in list_saved_places endpoint: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/combined", response_model=CombinedCollectionResponse)
async def get_combined_collection(
    current_user: dict = Depends(get_current_user),
    service: PlaceCollectionService = Depends(get_place_collection_service),
):
    """
    Lấy bộ sưu tập gộp: wishlist + nơi đã đến (visited_provinces).

    Example:
        GET /api/v1/place-collections/combined
    """
    try:
        user_id = current_user["user_id"]
        result = await service.get_combined_collection(user_id=user_id)
        if result["EC"] != 0:
            raise HTTPException(status_code=500, detail=result["EM"])
        return CombinedCollectionResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in get_combined_collection endpoint: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/exists", response_model=PlaceExistsResponse)
async def check_place_saved(
    osm_id: int = Query(..., description="OpenStreetMap ID cần kiểm tra"),
    current_user: dict = Depends(get_current_user),
    service: PlaceCollectionService = Depends(get_place_collection_service),
):
    """
    Kiểm tra user đã lưu place (theo osm_id) chưa.

    Example:
        GET /api/v1/place-collections/exists?osm_id=123456789
    """
    try:
        user_id = current_user["user_id"]
        result = await service.check_saved(user_id=user_id, osm_id=osm_id)
        if result["EC"] != 0:
            raise HTTPException(status_code=500, detail=result["EM"])
        return PlaceExistsResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in check_place_saved endpoint: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=SavePlaceResponse)
async def save_place(
    request: SavePlaceRequest,
    current_user: dict = Depends(get_current_user),
    service: PlaceCollectionService = Depends(get_place_collection_service),
):
    """
    Lưu 1 place vào wishlist (idempotent).

    Example:
        POST /api/v1/place-collections/
        Body: { "place_name": "Eiffel Tower", "place_display_name": "...", "latitude": 48.858, "longitude": 2.294, "category": "attraction", "osm_id": 123456 }
    """
    try:
        user_id = current_user["user_id"]
        result = await service.add_save(user_id=user_id, place=request.model_dump())
        if result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        return SavePlaceResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in save_place endpoint: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{save_id}", response_model=SavePlaceResponse)
async def remove_saved_place(
    save_id: str,
    current_user: dict = Depends(get_current_user),
    service: PlaceCollectionService = Depends(get_place_collection_service),
):
    """
    Bỏ lưu 1 place khỏi wishlist.

    Example:
        DELETE /api/v1/place-collections/07e8c89e-90d4-4ebc-9302-384dc6cb2f0c
    """
    try:
        user_id = current_user["user_id"]
        result = await service.remove_save(user_id=user_id, save_id=save_id)
        if result["EC"] != 0:
            raise HTTPException(status_code=400, detail=result["EM"])
        return SavePlaceResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in remove_saved_place endpoint: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
