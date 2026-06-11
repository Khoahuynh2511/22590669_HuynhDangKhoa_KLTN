"""
Train Booking API Endpoints
OTP verification flow (same pattern as hotel bookings)
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from ...schema.train_booking_schema import (
    TrainBookingCreate,
    TrainBookingOTPResponse,
    TrainVerifyOTPRequest,
    TrainResendOTPRequest,
    TrainBookingCancelRequest,
    MyTrainBookingListResponse,
    MyTrainBookingDetailResponse,
)
from ...services.train_booking_service import get_train_booking_service
from ...core.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/create-with-otp", response_model=TrainBookingOTPResponse)
async def create_train_booking_with_otp(
    booking_data: TrainBookingCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service=Depends(get_train_booking_service)
):
    """Tạo đặt vé tàu + gửi OTP xác nhận qua email"""
    data = booking_data.model_dump()
    data['user_id'] = current_user['user_id']

    result = await service.create_booking_with_otp(data)
    if result["EC"] != 0:
        raise HTTPException(
            status_code=400 if result["EC"] <= 4 else 500,
            detail=result["EM"]
        )
    return result


@router.post("/verify-otp", response_model=TrainBookingOTPResponse)
async def verify_train_booking_otp(
    request: TrainVerifyOTPRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service=Depends(get_train_booking_service)
):
    """Xác thực OTP để xác nhận đặt vé tàu"""
    result = await service.verify_otp(request.booking_id, request.otp_code)
    if result["EC"] != 0:
        raise HTTPException(
            status_code=400 if result["EC"] <= 5 else 500,
            detail=result["EM"]
        )
    return result


@router.post("/resend-otp", response_model=TrainBookingOTPResponse)
async def resend_train_booking_otp(
    request: TrainResendOTPRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service=Depends(get_train_booking_service)
):
    """Gửi lại mã OTP cho đặt vé tàu"""
    result = await service.resend_otp(request.booking_id)
    if result["EC"] != 0:
        raise HTTPException(status_code=400, detail=result["EM"])
    return result


@router.get("/my-bookings", response_model=MyTrainBookingListResponse)
async def get_my_train_bookings(
    current_user: Dict[str, Any] = Depends(get_current_user),
    service=Depends(get_train_booking_service)
):
    """Lấy danh sách đặt vé tàu của user"""
    return service.get_my_bookings(current_user['user_id'])


@router.get("/my-bookings/{booking_id}", response_model=MyTrainBookingDetailResponse)
async def get_train_booking_detail(
    booking_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service=Depends(get_train_booking_service)
):
    """Lấy chi tiết một đặt vé tàu"""
    result = service.get_booking_detail(booking_id, current_user['user_id'])
    if result["EC"] != 0:
        raise HTTPException(status_code=404, detail=result["EM"])
    return result


@router.post("/{booking_id}/cancel", response_model=TrainBookingOTPResponse)
async def cancel_train_booking(
    booking_id: str,
    cancel_data: TrainBookingCancelRequest = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service=Depends(get_train_booking_service)
):
    """Hủy đặt vé tàu"""
    reason = cancel_data.reason if cancel_data else None
    result = await service.cancel_booking(booking_id, current_user['user_id'], reason)
    if result["EC"] != 0:
        raise HTTPException(status_code=400, detail=result["EM"])
    return result
