"""
Hotel Booking Schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime, date
from uuid import UUID


class HotelBookingCreate(BaseModel):
    """Schema for creating a hotel booking with OTP"""
    hotel_id: UUID = Field(..., description="ID của khách sạn")
    user_id: UUID = Field(..., description="ID của người dùng")
    check_in: date = Field(..., description="Ngày nhận phòng (YYYY-MM-DD)")
    check_out: date = Field(..., description="Ngày trả phòng (YYYY-MM-DD)")
    num_rooms: int = Field(1, ge=1, le=10, description="Số lượng phòng (1-10)")
    num_guests: int = Field(1, ge=1, le=20, description="Số lượng khách (1-20)")
    guest_name: str = Field(..., min_length=2, max_length=100, description="Tên người liên hệ")
    guest_email: str = Field(..., description="Email để nhận OTP")
    guest_phone: str = Field(..., min_length=10, max_length=20, description="Số điện thoại")
    special_requests: Optional[str] = Field(None, max_length=500, description="Yêu cầu đặc biệt")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "hotel_id": "07e8c89e-90d4-4ebc-9302-384dc6cb2f0c",
                "user_id": "9b3d0691-eccd-4a81-9f43-383f5be344b8",
                "check_in": "2026-07-01",
                "check_out": "2026-07-03",
                "num_rooms": 1,
                "num_guests": 2,
                "guest_name": "Nguyen Van A",
                "guest_email": "user@example.com",
                "guest_phone": "0901234567",
                "special_requests": "Phòng view biển"
            }
        }
    )


class HotelBookingResponse(BaseModel):
    """Schema for hotel booking response"""
    booking_id: str
    hotel_id: UUID
    user_id: UUID
    check_in: date
    check_out: date
    num_rooms: int
    num_guests: int
    total_price: float
    guest_name: str
    guest_phone: str
    guest_email: Optional[str] = None
    special_requests: Optional[str] = None
    status: str
    otp_verified: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HotelBookingOTPResponse(BaseModel):
    """Response for OTP booking operations"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[dict] = None


class HotelVerifyOTPRequest(BaseModel):
    """Schema for verifying hotel booking OTP"""
    booking_id: str = Field(..., description="ID của booking")
    otp_code: str = Field(..., min_length=6, max_length=6, pattern="^[0-9]{6}$", description="Mã OTP 6 số")


class HotelResendOTPRequest(BaseModel):
    """Schema for resending hotel booking OTP"""
    booking_id: str = Field(..., description="ID của booking cần gửi lại OTP")


class HotelBookingCancelRequest(BaseModel):
    """Schema for cancelling hotel booking"""
    reason: Optional[str] = Field(None, max_length=500, description="Lý do hủy")


class HotelInfoInBooking(BaseModel):
    """Hotel info embedded in booking response"""
    hotel_id: UUID
    hotel_name: str
    location: str
    star_rating: float
    image_urls: Optional[str] = None
    price: float


class MyHotelBookingItem(BaseModel):
    """Schema for booking item in user's hotel booking list"""
    booking_id: str
    hotel_name: str = Field(..., description="Tên khách sạn")
    location: str = Field(..., description="Địa điểm")
    check_in: date
    check_out: date
    num_rooms: int
    num_guests: int
    total_price: float
    status: str
    image_urls: Optional[str] = None
    created_at: datetime


class MyHotelBookingListResponse(BaseModel):
    """Response for user's hotel booking list"""
    EC: int
    EM: str
    data: Optional[list[MyHotelBookingItem]] = None
    total: Optional[int] = None


class MyHotelBookingDetail(BaseModel):
    """Schema for detailed hotel booking"""
    booking_id: str
    status: str
    check_in: date
    check_out: date
    num_rooms: int
    num_guests: int
    total_price: float
    guest_name: str
    guest_phone: str
    guest_email: Optional[str] = None
    special_requests: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    hotel: Optional[HotelInfoInBooking] = None


class MyHotelBookingDetailResponse(BaseModel):
    """Response for hotel booking detail"""
    EC: int
    EM: str
    data: Optional[MyHotelBookingDetail] = None
