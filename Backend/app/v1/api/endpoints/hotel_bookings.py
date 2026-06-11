"""
Hotel Booking API Endpoints
OTP verification flow (same pattern as tour bookings)
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from ...schema.hotel_booking_schema import (
    HotelBookingCreate,
    HotelBookingOTPResponse,
    HotelVerifyOTPRequest,
    HotelResendOTPRequest,
    HotelBookingCancelRequest,
    MyHotelBookingListResponse,
    MyHotelBookingDetailResponse,
)
from ...services.hotel_booking_service import HotelBookingService, get_hotel_booking_service
from ...core.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/create-with-otp", response_model=HotelBookingOTPResponse)
async def create_hotel_booking_with_otp(
    booking_data: HotelBookingCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: HotelBookingService = Depends(get_hotel_booking_service)
):
    """Tạo đặt phòng khách sạn + gửi OTP xác nhận qua email"""
    # Override user_id from token
    data = booking_data.model_dump()
    data['user_id'] = current_user['user_id']

    result = await service.create_booking_with_otp(data)
    if result["EC"] != 0:
        raise HTTPException(
            status_code=400 if result["EC"] <= 3 else 500,
            detail=result["EM"]
        )
    return result


@router.post("/verify-otp", response_model=HotelBookingOTPResponse)
async def verify_hotel_booking_otp(
    request: HotelVerifyOTPRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: HotelBookingService = Depends(get_hotel_booking_service)
):
    """Xác thực OTP để xác nhận đặt phòng khách sạn"""
    result = await service.verify_otp(str(request.booking_id), request.otp_code)
    if result["EC"] != 0:
        raise HTTPException(
            status_code=400 if result["EC"] <= 5 else 500,
            detail=result["EM"]
        )
    return result


@router.post("/resend-otp", response_model=HotelBookingOTPResponse)
async def resend_hotel_booking_otp(
    request: HotelResendOTPRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: HotelBookingService = Depends(get_hotel_booking_service)
):
    """Gửi lại mã OTP cho đặt phòng khách sạn"""
    result = await service.resend_otp(str(request.booking_id))
    if result["EC"] != 0:
        raise HTTPException(status_code=400, detail=result["EM"])
    return result


@router.get("/my-bookings", response_model=MyHotelBookingListResponse)
async def get_my_hotel_bookings(
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: HotelBookingService = Depends(get_hotel_booking_service)
):
    """Lấy danh sách đặt phòng khách sạn của user"""
    result = service.get_my_bookings(current_user['user_id'])
    return result


@router.get("/my-bookings/{booking_id}", response_model=MyHotelBookingDetailResponse)
async def get_hotel_booking_detail(
    booking_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: HotelBookingService = Depends(get_hotel_booking_service)
):
    """Lấy chi tiết một đặt phòng khách sạn"""
    result = service.get_booking_detail(booking_id, current_user['user_id'])
    if result["EC"] != 0:
        raise HTTPException(status_code=404, detail=result["EM"])
    return result


@router.post("/{booking_id}/cancel", response_model=HotelBookingOTPResponse)
async def cancel_hotel_booking(
    booking_id: str,
    cancel_data: HotelBookingCancelRequest = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: HotelBookingService = Depends(get_hotel_booking_service)
):
    """Hủy đặt phòng khách sạn"""
    reason = cancel_data.reason if cancel_data else None
    result = await service.cancel_booking(booking_id, current_user['user_id'], reason)
    if result["EC"] != 0:
        raise HTTPException(status_code=400, detail=result["EM"])
    return result
