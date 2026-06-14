"""
Bus Booking API Endpoints
OTP verification flow (same pattern as hotel bookings)
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from ...schema.bus_booking_schema import (
    BusBookingCreate,
    BusBookingOTPResponse,
    BusVerifyOTPRequest,
    BusResendOTPRequest,
    BusBookingCancelRequest,
    MyBusBookingListResponse,
    MyBusBookingDetailResponse,
)
from ...services.bus_booking_service import get_bus_booking_service
from ...core.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/create-with-otp", response_model=BusBookingOTPResponse)
async def create_bus_booking_with_otp(
    booking_data: BusBookingCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service=Depends(get_bus_booking_service)
):
    """Tạo đặt vé xe + gửi OTP xác nhận qua email"""
    data = booking_data.model_dump()
    data['user_id'] = current_user['user_id']

    result = await service.create_booking_with_otp(data)
    if result["EC"] != 0:
        raise HTTPException(
            status_code=400 if result["EC"] <= 4 else 500,
            detail=result["EM"]
        )
    return result


@router.post("/verify-otp", response_model=BusBookingOTPResponse)
async def verify_bus_booking_otp(
    request: BusVerifyOTPRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service=Depends(get_bus_booking_service)
):
    """Xác thực OTP để xác nhận đặt vé xe"""
    result = await service.verify_otp(request.booking_id, request.otp_code)
    if result["EC"] != 0:
        raise HTTPException(
            status_code=400 if result["EC"] <= 5 else 500,
            detail=result["EM"]
        )
    return result


@router.post("/resend-otp", response_model=BusBookingOTPResponse)
async def resend_bus_booking_otp(
    request: BusResendOTPRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service=Depends(get_bus_booking_service)
):
    """Gửi lại mã OTP cho đặt vé xe"""
    result = await service.resend_otp(request.booking_id)
    if result["EC"] != 0:
        raise HTTPException(status_code=400, detail=result["EM"])
    return result


@router.get("/my-bookings", response_model=MyBusBookingListResponse)
async def get_my_bus_bookings(
    current_user: Dict[str, Any] = Depends(get_current_user),
    service=Depends(get_bus_booking_service)
):
    """Lấy danh sách đặt vé xe của user"""
    return service.get_my_bookings(current_user['user_id'])


@router.get("/my-bookings/{booking_id}", response_model=MyBusBookingDetailResponse)
async def get_bus_booking_detail(
    booking_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service=Depends(get_bus_booking_service)
):
    """Lấy chi tiết một đặt vé xe"""
    result = service.get_booking_detail(booking_id, current_user['user_id'])
    if result["EC"] != 0:
        raise HTTPException(status_code=404, detail=result["EM"])
    return result


@router.post("/{booking_id}/cancel", response_model=BusBookingOTPResponse)
async def cancel_bus_booking(
    booking_id: str,
    cancel_data: BusBookingCancelRequest = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service=Depends(get_bus_booking_service)
):
    """Hủy đặt vé xe"""
    reason = cancel_data.reason if cancel_data else None
    result = await service.cancel_booking(booking_id, current_user['user_id'], reason)
    if result["EC"] != 0:
        raise HTTPException(status_code=400, detail=result["EM"])
    return result


@router.get("/occupied-seats/{bus_id}")
async def get_occupied_bus_seats(
    bus_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service=Depends(get_bus_booking_service)
):
    """Lấy danh sách các ghế đã được đặt của chuyến xe"""
    result = service.get_occupied_seats(bus_id)
    if result["EC"] != 0:
        raise HTTPException(status_code=400, detail=result["EM"])
    return result

