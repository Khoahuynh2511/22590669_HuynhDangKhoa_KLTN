"""
Flight Booking Schemas
Following hotel_booking_schema.py pattern
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class FlightBookingCreate(BaseModel):
    """Schema for creating a flight booking with OTP"""
    flight_id: str = Field(..., description="ID của chuyến bay")
    seat_class: str = Field(..., description="Hạng ghế: economy, business, first_class")
    num_passengers: int = Field(1, ge=1, le=9, description="Số hành khách (1-9)")
    passenger_name: str = Field(..., min_length=2, max_length=100, description="Tên hành khách")
    passenger_email: str = Field(..., description="Email để nhận OTP")
    passenger_phone: str = Field(..., min_length=10, max_length=20, description="Số điện thoại")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "flight_id": "VN123_20250615_0800",
                "seat_class": "economy",
                "num_passengers": 2,
                "passenger_name": "Nguyen Van A",
                "passenger_email": "user@example.com",
                "passenger_phone": "0901234567"
            }
        }
    )


class FlightBookingOTPResponse(BaseModel):
    """Response for OTP booking operations"""
    EC: int = Field(..., description="Error code (0 = success)")
    EM: str = Field(..., description="Error message")
    data: Optional[dict] = None


class FlightVerifyOTPRequest(BaseModel):
    """Schema for verifying flight booking OTP"""
    booking_id: str = Field(..., description="ID của booking")
    otp_code: str = Field(..., min_length=6, max_length=6, pattern="^[0-9]{6}$", description="Mã OTP 6 số")


class FlightResendOTPRequest(BaseModel):
    """Schema for resending flight booking OTP"""
    booking_id: str = Field(..., description="ID của booking cần gửi lại OTP")


class FlightBookingCancelRequest(BaseModel):
    """Schema for cancelling flight booking"""
    reason: Optional[str] = Field(None, max_length=500, description="Lý do hủy")


class MyFlightBookingItem(BaseModel):
    """Schema for booking item in user's flight booking list"""
    booking_id: str
    flight_number: str = Field("N/A", description="Số chuyến bay")
    airline_name: str = Field("N/A", description="Tên hãng bay")
    departure_city: str = Field("", description="Thành phố đi")
    arrival_city: str = Field("", description="Thành phố đến")
    departure_time: str = Field("", description="Thời gian khởi hành")
    seat_class: str
    num_passengers: int
    total_price: float
    status: str
    created_at: str


class MyFlightBookingListResponse(BaseModel):
    """Response for user's flight booking list"""
    EC: int
    EM: str
    data: Optional[list[MyFlightBookingItem]] = None
    total: Optional[int] = None


class MyFlightBookingDetail(BaseModel):
    """Schema for detailed flight booking"""
    booking_id: str
    status: str
    passenger_name: str
    passenger_phone: str
    passenger_email: Optional[str] = None
    seat_class: str
    num_passengers: int
    total_price: float
    created_at: str
    updated_at: str
    flight: Optional[dict] = None


class MyFlightBookingDetailResponse(BaseModel):
    """Response for flight booking detail"""
    EC: int
    EM: str
    data: Optional[MyFlightBookingDetail] = None
