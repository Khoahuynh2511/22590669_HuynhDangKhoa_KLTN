"""
Admin Hotel Management Endpoints
"""
from fastapi import APIRouter, Query, Depends, HTTPException, Form, File, UploadFile
from typing import Optional, Dict, Any, List
from datetime import datetime
import csv
import io
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


@router.post("/bulk/csv")
async def create_hotels_from_csv(
    file: UploadFile = File(..., description="CSV file chứa dữ liệu khách sạn"),
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminHotelService = Depends(get_admin_hotel_service)
):
    """
    Tạo nhiều khách sạn từ file CSV

    CSV file phải có các cột sau (header):
    - hotel_name: Tên khách sạn (bắt buộc)
    - location: Vị trí/Khu vực (bắt buộc)
    - description: Mô tả chi tiết (bắt buộc)
    - address: Địa chỉ (bắt buộc)
    - star_rating: Số sao 1-5 (bắt buộc)
    - review_score: Điểm đánh giá 0-10 (bắt buộc)
    - review_count: Số lượt đánh giá (bắt buộc)
    - price: Giá phòng/đêm VNĐ (bắt buộc)
    - original_price: Giá gốc VNND (tùy chọn)
    - discount: % giảm giá (tùy chọn)
    - available_rooms: Số phòng trống (bắt buộc)
    - amenities: Tiện ích, ngăn cách bằng | (tùy chọn)
    - image_urls: URL hình ảnh, ngăn cách bằng | (tùy chọn)
    - is_active: Trạng thái true/false (tùy chọn, mặc định: true)
    """
    try:
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File phải có định dạng CSV")

        contents = await file.read()
        try:
            csv_text = contents.decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                csv_text = contents.decode('cp1258')
            except Exception:
                csv_text = contents.decode('utf-8', errors='replace')

        csv_reader = csv.DictReader(io.StringIO(csv_text))

        required_fields = [
            'hotel_name', 'location', 'description', 'address',
            'star_rating', 'review_score', 'review_count',
            'price', 'available_rooms'
        ]

        if not csv_reader.fieldnames:
            raise HTTPException(status_code=400, detail="File CSV không có header")

        missing_fields = [f for f in required_fields if f not in csv_reader.fieldnames]
        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Thiếu các cột bắt buộc: {', '.join(missing_fields)}"
            )

        hotels_data = []
        errors = []
        row_num = 1

        for row in csv_reader:
            row_num += 1
            try:
                hotel_data = {
                    'hotel_name': row['hotel_name'].strip(),
                    'location': row['location'].strip(),
                    'description': row['description'].strip(),
                    'address': row['address'].strip(),
                    'star_rating': float(row['star_rating']),
                    'review_score': float(row['review_score']),
                    'review_count': int(float(row['review_count'])),
                    'price': float(row['price']),
                    'available_rooms': int(float(row['available_rooms'])),
                }

                if row.get('original_price'):
                    hotel_data['original_price'] = float(row['original_price'])
                if row.get('discount'):
                    hotel_data['discount'] = int(float(row['discount']))
                if row.get('amenities'):
                    hotel_data['amenities'] = row['amenities'].strip()
                if row.get('image_urls'):
                    hotel_data['image_urls'] = row['image_urls'].strip()

                if row.get('is_active'):
                    is_active_str = row['is_active'].strip().lower()
                    hotel_data['is_active'] = is_active_str in ['true', '1', 'yes', 'y']
                else:
                    hotel_data['is_active'] = True

                # Validation
                if not hotel_data['hotel_name']:
                    raise ValueError("hotel_name không được để trống")
                if not hotel_data['location']:
                    raise ValueError("location không được để trống")
                if hotel_data['star_rating'] < 1 or hotel_data['star_rating'] > 5:
                    raise ValueError("star_rating phải từ 1-5")
                if hotel_data['price'] <= 0:
                    raise ValueError("price phải lớn hơn 0")
                if hotel_data['available_rooms'] < 0:
                    raise ValueError("available_rooms phải >= 0")

                hotels_data.append(hotel_data)

            except ValueError as e:
                errors.append(f"Dòng {row_num}: {str(e)}")
            except Exception as e:
                errors.append(f"Dòng {row_num}: Lỗi parse dữ liệu - {str(e)}")

        if not hotels_data:
            raise HTTPException(
                status_code=400,
                detail=f"Không có dữ liệu hợp lệ. Lỗi: {'; '.join(errors)}"
            )

        result = service.create_hotels_bulk(hotels_data)

        if errors:
            result['data']['parsing_errors'] = errors

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_hotels_from_csv: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý file CSV: {str(e)}")


@router.post("/{hotel_id}/images")
async def manage_hotel_images(
    hotel_id: str,
    replace_existing: bool = Query(False, description="True = thay thế tất cả ảnh cũ, False = thêm ảnh mới"),
    images: List[UploadFile] = File([], description="Ảnh khách sạn (định dạng: JPEG/JPG/PNG/WebP)"),
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminHotelService = Depends(get_admin_hotel_service)
):
    """
    Upload/thay thế ảnh cho khách sạn

    - replace_existing=False: Thêm ảnh mới vào danh sách hiện có
    - replace_existing=True: Xóa ảnh cũ, thay bằng ảnh mới
    """
    try:
        if not images:
            raise HTTPException(status_code=400, detail="Không có ảnh nào được gửi")

        # Validate image types
        allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
        for image in images:
            if image.content_type not in allowed_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Loại file không hợp lệ: {image.content_type}. Chấp nhận: jpeg, jpg, png, webp"
                )

        # Validate total images
        if not replace_existing:
            hotel = service.get_hotel_by_id(hotel_id)
            if hotel["EC"] != 0:
                raise HTTPException(status_code=404, detail=hotel["EM"])
            existing_count = len(
                [u for u in (hotel["data"].get("image_urls") or "").split("|") if u.strip()]
            )
            if existing_count + len(images) > 10:
                raise HTTPException(
                    status_code=400,
                    detail=f"Tối đa 10 ảnh. Hiện có {existing_count} ảnh, chỉ thêm được {10 - existing_count} ảnh nữa"
                )

        result = await service.manage_images(hotel_id, images, replace_existing)

        if result["EC"] != 0:
            raise HTTPException(status_code=500, detail=result["EM"])

        return {"EC": 0, "EM": "Cập nhật ảnh thành công", "image_urls": result["image_urls"]}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in manage_hotel_images: {str(e)}")
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
