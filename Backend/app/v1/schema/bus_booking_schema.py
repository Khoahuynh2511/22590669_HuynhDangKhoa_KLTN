"""
Bus Booking Schemas
Following hotel_booking_schema.py pattern
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class BusBookingCreate(BaseModel):
    """Schema for creating a bus booking with OTP"""
    bus_id: str = Field(..., description="ID của chuyến xe")
    seat_type_id: str = Field(..., description="Loại ghế: standard, premium, single_sleeper, double_sleeper")
    num_passengers: int = Field(1, ge=1, le=9, description="Số hành khách (1-9)")
    passenger_name: str = Field(..., min_length=2, max_length=100, description="Tên hành khách")
    passenger_email: str = Field(..., description="Email để nhận OTP")
    passenger_phone: str = Field(..., min_length=10, max_length=20, description="Số điện thoại")
    selected_seats: Optional[str] = Field(None, description="Danh sách mã ghế đã chọn, ví dụ: 'A1,A2'")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "bus_id": "SM_SG_DL_20250615_0800",
                "seat_type_id": "standard",
                "num_passengers": 2,
                "passenger_name": "Nguyen Van A",
                "passenger_email": "user@example.com",
                "passenger_phone": "0901234567",
                "selected_seats": "A1,A2"
            }
        }
    )


class BusBookingOTPResponse(BaseModel):
    """Response for OTP booking operations"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[dict] = None


class BusVerifyOTPRequest(BaseModel):
    """Schema for verifying bus booking OTP"""
    booking_id: str = Field(..., description="ID của booking")
    otp_code: str = Field(..., min_length=6, max_length=6, pattern="^[0-9]{6}$", description="Mã OTP 6 số")


class BusResendOTPRequest(BaseModel):
    """Schema for resending bus booking OTP"""
    booking_id: str = Field(..., description="ID của booking cần gửi lại OTP")


class BusBookingCancelRequest(BaseModel):
    """Schema for cancelling bus booking"""
    reason: Optional[str] = Field(None, max_length=500, description="Lý do hủy")


class MyBusBookingItem(BaseModel):
    """Schema for booking item in user's bus booking list"""
    booking_id: str
    bus_number: str = Field("N/A", description="Số chuyến xe")
    company_name: str = Field("N/A", description="Tên hãng xe")
    departure_city: str = Field("", description="Thành phố đi")
    arrival_city: str = Field("", description="Thành phố đến")
    departure_time: str = Field("", description="Thời gian khởi hành")
    seat_type: str = Field("", description="Loại ghế")
    num_passengers: int
    total_price: float
    status: str
    created_at: str


class MyBusBookingListResponse(BaseModel):
    """Response for user's bus booking list"""
    EC: int
    EM: str
    data: Optional[list[MyBusBookingItem]] = None
    total: Optional[int] = None


class MyBusBookingDetail(BaseModel):
    """Schema for detailed bus booking"""
    booking_id: str
    status: str
    passenger_name: str
    passenger_phone: str
    passenger_email: Optional[str] = None
    seat_type: str
    num_passengers: int
    total_price: float
    selected_seats: Optional[str] = None
    created_at: str
    updated_at: str
    bus: Optional[dict] = None


class MyBusBookingDetailResponse(BaseModel):
    """Response for bus booking detail"""
    EC: int
    EM: str
    data: Optional[MyBusBookingDetail] = None

