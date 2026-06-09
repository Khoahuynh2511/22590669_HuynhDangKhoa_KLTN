"""
Admin Hotel Management Endpoints
"""
from fastapi import APIRouter, Query, Depends, HTTPException, Form, File, UploadFile
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from ...services.admin_hotel_service import get_admin_hotel_service, AdminHotelService
from ...core.dependencies import get_current_admin

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("")
async def get_all_hotels(
    limit: Optional[int] = Query(None, ge=1),
    offset: Optional[int] = Query(None, ge=0),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminHotelService = Depends(get_admin_hotel_service)
):
    """Lấy danh sách khách sạn (admin)"""
    result = service.get_all_hotels(limit=limit, offset=offset, search=search, is_active=is_active)
    if result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result


@router.post("")
async def create_hotel(
    hotel_name: str = Form(..., description="Tên khách sạn"),
    location: str = Form(..., description="Vị trí/Khu vực"),
    description: str = Form(..., description="Mô tả chi tiết"),
    address: str = Form(..., description="Địa chỉ đầy đủ"),
    star_rating: float = Form(..., description="Số sao (1-5)", ge=1, le=5),
    review_score: float = Form(..., description="Điểm đánh giá (0-10)", ge=0, le=10),
    review_count: int = Form(..., description="Số lượt đánh giá", ge=0),
    price: float = Form(..., description="Giá phòng/đêm VNĐ", gt=0),
    original_price: Optional[float] = Form(None, description="Giá gốc VNĐ (nếu có giảm giá)", gt=0),
    discount: Optional[int] = Form(None, description="% giảm giá (0-100)", ge=0, le=100),
    amenities: Optional[str] = Form(None, description="Tiện ích (ngăn cách bằng dấu phẩy)"),
    available_rooms: int = Form(..., description="Số phòng còn trống", ge=0),
    is_active: bool = Form(True, description="Trạng thái kích hoạt"),
    images: List[UploadFile] = File([], description="Ảnh khách sạn (max 10 ảnh, định dạng: JPEG/JPG/PNG/WebP)"),
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminHotelService = Depends(get_admin_hotel_service)
):
    """
    Tạo khách sạn mới với upload ảnh trực tiếp lên Cloudinary

    Endpoint này tự động:
    - Upload ảnh lên Cloudinary
    - Tạo khách sạn với URLs từ Cloudinary
    - Rollback nếu có lỗi

    Args:
        hotel_name: Tên khách sạn
        location: Vị trí/Khu vực
        description: Mô tả chi tiết
        address: Địa chỉ đầy đủ
        star_rating: Số sao (1-5)
        review_score: Điểm đánh giá (0-10)
        review_count: Số lượt đánh giá
        price: Giá phòng/đêm VNĐ
        original_price: Giá gốc VNĐ (nếu có giảm giá)
        discount: % giảm giá (0-100)
        amenities: Tiện ích (ngăn cách bằng dấu phẩy)
        available_rooms: Số phòng còn trống
        is_active: Trạng thái kích hoạt
        images: Danh sách file ảnh (tối đa 10 ảnh, định dạng: JPEG/JPG/PNG/WebP)
        current_admin: Admin hiện tại
        service: Admin hotel service instance

    Returns:
        Dict với thông tin khách sạn đã tạo
    """
    try:
        # Validate max 10 images
        if len(images) > 10:
            raise HTTPException(status_code=400, detail="Maximum 10 images allowed")

        # Validate image types
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
        for image in images:
            if image.content_type not in allowed_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file type: {image.content_type}. Allowed: jpeg, jpg, png, webp"
                )

        # Upload images to Cloudinary
        logger.info(f"Uploading {len(images)} images to Cloudinary...")
        image_urls = await service.upload_images(images)

        if not image_urls:
            raise HTTPException(status_code=500, detail="Failed to upload images")

        # Prepare hotel data
        hotel_data = {
            "hotel_name": hotel_name,
            "location": location,
            "description": description,
            "address": address,
            "star_rating": star_rating,
            "review_score": review_score,
            "review_count": review_count,
            "price": price,
            "original_price": original_price,
            "discount": discount,
            "amenities": amenities,
            "available_rooms": available_rooms,
            "is_active": is_active,
            "image_urls": "|".join(image_urls)  # Pipe-separated URLs
        }

        # Create hotel
        result = service.create_hotel(hotel_data)

        if result["EC"] != 0:
            # Rollback: Delete uploaded images
            await service.delete_images_from_urls(hotel_data["image_urls"])
            raise HTTPException(status_code=400, detail=result["EM"])

        logger.info(f"✓ Created hotel with {len(image_urls)} images")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_hotel endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{hotel_id}")
async def get_hotel_by_id(
    hotel_id: str,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminHotelService = Depends(get_admin_hotel_service)
):
    """Lấy chi tiết khách sạn"""
    result = service.get_hotel_by_id(hotel_id)
    if result["EC"] == 1:
        raise HTTPException(status_code=404, detail=result["EM"])
    elif result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result


@router.put("/{hotel_id}")
async def update_hotel(
    hotel_id: str,
    update_data: Dict[str, Any],
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminHotelService = Depends(get_admin_hotel_service)
):
    """Cập nhật khách sạn"""
    result = service.update_hotel(hotel_id, update_data)
    if result["EC"] == 1:
        raise HTTPException(status_code=404, detail=result["EM"])
    elif result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result


@router.delete("/{hotel_id}")
async def delete_hotel(
    hotel_id: str,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminHotelService = Depends(get_admin_hotel_service)
):
    """Xóa khách sạn (soft delete)"""
    result = service.delete_hotel(hotel_id)
    if result["EC"] == 1:
        raise HTTPException(status_code=404, detail=result["EM"])
    elif result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result


@router.patch("/{hotel_id}/status")
async def toggle_hotel_status(
    hotel_id: str,
    status_data: Dict[str, Any],
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminHotelService = Depends(get_admin_hotel_service)
):
    """Bật/tắt trạng thái khách sạn"""
    is_active = status_data.get("is_active")
    if is_active is None:
        raise HTTPException(status_code=400, detail="Thiếu trạng thái is_active")
    result = service.toggle_hotel_status(hotel_id, is_active)
    if result["EC"] != 0:
        raise HTTPException(status_code=400 if result["EC"] == 1 else 500, detail=result["EM"])
    return result
