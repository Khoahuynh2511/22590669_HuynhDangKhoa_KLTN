"""
Customer Query Agent — NLU schema
Structured output cho node phân loại ý định + rút slot (blueprint 03-customer-query-agent).

Lưu ý: dùng các field tường minh (Optional) thay vì Dict[str, Any] vì OpenAI strict
structured-output yêu cầu additionalProperties=false — Dict động sẽ bị reject.
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class IntentClassification(BaseModel):
    """Kết quả phân loại ý định + rút slot từ tin nhắn người dùng."""

    intent: str = Field(
        description=(
            "Một trong: flight_search, train_search, bus_search, hotel_search, "
            "tour_recommendation, build_itinerary, booking, payment, general"
        )
    )
    confidence: float = Field(description="Độ tin tưởng 0.0-1.0", ge=0.0, le=1.0)

    # --- Slots (tường minh, strict-compatible) ---
    origin: Optional[str] = Field(default=None, description="Nơi đi / điểm xuất phát")
    destination: Optional[str] = Field(default=None, description="Nơi đến / điểm đến du lịch")
    location: Optional[str] = Field(default=None, description="Địa điểm tìm khách sạn (thành phố/tỉnh)")
    departure_city: Optional[str] = Field(default=None, description="Thành phố/ga/bến đi (nếu khác origin)")
    arrival_city: Optional[str] = Field(default=None, description="Thành phố/ga/bến đến (nếu khác destination)")
    start_date: Optional[str] = Field(default=None, description="Ngày đi / nhận phòng (YYYY-MM-DD)")
    end_date: Optional[str] = Field(default=None, description="Ngày về / trả phòng (YYYY-MM-DD)")
    adults: Optional[int] = Field(default=None, description="Số người lớn")
    budget: Optional[float] = Field(default=None, description="Ngân sách tổng (VND)")
    min_price: Optional[float] = Field(default=None, description="Giá tối thiểu (VND)")
    max_price: Optional[float] = Field(default=None, description="Giá tối đa (VNDND)")
    num_rooms: Optional[int] = Field(default=None, description="Số phòng khách sạn")
    num_guests: Optional[int] = Field(default=None, description="Số khách")

    missing_slots: List[str] = Field(
        default_factory=list,
        description="Các slot bắt buộc còn thiếu cho intent đã phát hiện",
    )
