"""
Train Booking Schemas
Following hotel_booking_schema.py pattern
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class TrainBookingCreate(BaseModel):
    """Schema for creating a train booking with OTP"""
    train_id: str = Field(..., description="ID của chuyến tàu")
    seat_type_id: str = Field(..., description="Loại ghế: standard, soft_seat, hard_sleeper, soft_sleeper, etc.")
    num_passengers: int = Field(1, ge=1, le=9, description="Số hành khách (1-9)")
    passenger_name: str = Field(..., min_length=2, max_length=100, description="Tên hành khách")
    passenger_email: str = Field(..., description="Email để nhận OTP")
    passenger_phone: str = Field(..., min_length=10, max_length=20, description="Số điện thoại")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "train_id": "SE1_20250615_0800",
                "seat_type_id": "soft_sleeper",
                "num_passengers": 2,
                "passenger_name": "Nguyen Van A",
                "passenger_email": "user@example.com",
                "passenger_phone": "0901234567"
            }
        }
    )


class TrainBookingOTPResponse(BaseModel):
    """Response for OTP booking operations"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[dict] = None


class TrainVerifyOTPRequest(BaseModel):
    """Schema for verifying train booking OTP"""
    booking_id: str = Field(..., description="ID của booking")
    otp_code: str = Field(..., min_length=6, max_length=6, pattern="^[0-9]{6}$", description="Mã OTP 6 số")


class TrainResendOTPRequest(BaseModel):
    """Schema for resending train booking OTP"""
    booking_id: str = Field(..., description="ID của booking cần gửi lại OTP")


class TrainBookingCancelRequest(BaseModel):
    """Schema for cancelling train booking"""
    reason: Optional[str] = Field(None, max_length=500, description="Lý do hủy")


class MyTrainBookingItem(BaseModel):
    """Schema for booking item in user's train booking list"""
    booking_id: str
    train_number: str = Field("N/A", description="Số chuyến tàu")
    departure_city: str = Field("", description="Thành phố đi")
    arrival_city: str = Field("", description="Thành phố đến")
    departure_time: str = Field("", description="Thời gian khởi hành")
    seat_type: str = Field("", description="Loại ghế")
    num_passengers: int
    total_price: float
    status: str
    created_at: str


class MyTrainBookingListResponse(BaseModel):
    """Response for user's train booking list"""
    EC: int
    EM: str
    data: Optional[list[MyTrainBookingItem]] = None
    total: Optional[int] = None


class MyTrainBookingDetail(BaseModel):
    """Schema for detailed train booking"""
    booking_id: str
    status: str
    passenger_name: str
    passenger_phone: str
    passenger_email: Optional[str] = None
    seat_type: str
    num_passengers: int
    total_price: float
    created_at: str
    updated_at: str
    train: Optional[dict] = None


class MyTrainBookingDetailResponse(BaseModel):
    """Response for train booking detail"""
    EC: int
    EM: str
    data: Optional[MyTrainBookingDetail] = None
