"""
Shared Itinerary Schemas
Pydantic models cho tính năng chia sẻ lịch trình công khai (QR + link).
Pattern theo visited_province_schema.py (EC/EM convention).
"""
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class CreateShareRequest(BaseModel):
    """Body cho POST /api/v1/itineraries/share."""
    payload: Dict[str, Any] = Field(
        ...,
        description="Nội dung lịch trình (destination, travel_date, duration_days, group_size, days, total_price, ...)",
    )
    title: Optional[str] = Field(None, description="Tiêu đề tuỳ chọn (vd: 'Đà Lạt 3 ngày 2 đêm')")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Đà Lạt 3 ngày 2 đêm",
                "payload": {
                    "destination": "Đà Lạt",
                    "travel_date": "2026-07-10",
                    "duration_days": 3,
                    "group_size": 2,
                    "total_price": 4500000,
                    "days": [
                        {"day": 1, "morning": ["Cáp treo Đà Lạt"], "afternoon": ["Hồ Xuân Hương"], "evening": ["Chợ đêm"]}
                    ],
                },
            }
        }
    )


class CreateShareResponse(BaseModel):
    """Response cho POST /share."""
    EC: int = Field(0, description="Error code")
    EM: str = Field("Success", description="Error message")
    share_id: Optional[str] = Field(None, description="ID chia sẻ (UUID)")
    url: Optional[str] = Field(None, description="Link công khai để xem lịch trình")


class SharedItineraryResponse(BaseModel):
    """Response cho GET /{share_id} (public)."""
    EC: int = Field(0, description="Error code")
    EM: str = Field("Success", description="Error message")
    title: str = Field("", description="Tiêu đề lịch trình")
    itinerary: Dict[str, Any] = Field(default_factory=dict, description="Nội dung lịch trình")
    view_count: int = Field(0, description="Số lượt xem")
    created_at: Optional[datetime] = Field(None, description="Thời điểm tạo")
