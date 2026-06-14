"""
Flight Booking API Endpoints
OTP verification flow (same pattern as hotel bookings)
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from ...schema.flight_booking_schema import (
    FlightBookingCreate,
    FlightBookingOTPResponse,
    FlightVerifyOTPRequest,
    FlightResendOTPRequest,
    FlightBookingCancelRequest,
    MyFlightBookingListResponse,
    MyFlightBookingDetailResponse,
)
from ...services.flight_booking_service import get_flight_booking_service
from ...core.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/create-with-otp", response_model=FlightBookingOTPResponse)
async def create_flight_booking_with_otp(
    booking_data: FlightBookingCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service=Depends(get_flight_booking_service)
):
    """Tạo đặt vé máy bay + gửi OTP xác nhận qua email"""
    data = booking_data.model_dump()
    data['user_id'] = current_user['user_id']

    result = await service.create_booking_with_otp(data)
    if result["EC"] != 0:
        raise HTTPException(
            status_code=400 if result["EC"] <= 4 else 500,
            detail=result["EM"]
        )
    return result


@router.post("/verify-otp", response_model=FlightBookingOTPResponse)
async def verify_flight_booking_otp(
    request: FlightVerifyOTPRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service=Depends(get_flight_booking_service)
):
    """Xác thực OTP để xác nhận đặt vé máy bay"""
    result = await service.verify_otp(request.booking_id, request.otp_code)
    if result["EC"] != 0:
        raise HTTPException(
            status_code=400 if result["EC"] <= 5 else 500,
            detail=result["EM"]
        )
    return result


@router.post("/resend-otp", response_model=FlightBookingOTPResponse)
async def resend_flight_booking_otp(
    request: FlightResendOTPRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service=Depends(get_flight_booking_service)
):
    """Gửi lại mã OTP cho đặt vé máy bay"""
    result = await service.resend_otp(request.booking_id)
    if result["EC"] != 0:
        raise HTTPException(status_code=400, detail=result["EM"])
    return result


@router.get("/my-bookings", response_model=MyFlightBookingListResponse)
async def get_my_flight_bookings(
    current_user: Dict[str, Any] = Depends(get_current_user),
    service=Depends(get_flight_booking_service)
):
    """Lấy danh sách đặt vé máy bay của user"""
    return service.get_my_bookings(current_user['user_id'])


@router.get("/my-bookings/{booking_id}", response_model=MyFlightBookingDetailResponse)
async def get_flight_booking_detail(
    booking_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service=Depends(get_flight_booking_service)
):
    """Lấy chi tiết một đặt vé máy bay"""
    result = service.get_booking_detail(booking_id, current_user['user_id'])
    if result["EC"] != 0:
        raise HTTPException(status_code=404, detail=result["EM"])
    return result


@router.post("/{booking_id}/cancel", response_model=FlightBookingOTPResponse)
async def cancel_flight_booking(
    booking_id: str,
    cancel_data: FlightBookingCancelRequest = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service=Depends(get_flight_booking_service)
):
    """Hủy đặt vé máy bay"""
    reason = cancel_data.reason if cancel_data else None
    result = await service.cancel_booking(booking_id, current_user['user_id'], reason)
    if result["EC"] != 0:
        raise HTTPException(status_code=400, detail=result["EM"])
    return result


@router.get("/occupied-seats/{flight_id}")
async def get_occupied_flight_seats(
    flight_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service=Depends(get_flight_booking_service)
):
    """Lấy danh sách các ghế đã được đặt của chuyến bay"""
    result = service.get_occupied_seats(flight_id)
    if result["EC"] != 0:
        raise HTTPException(status_code=400, detail=result["EM"])
    return result

