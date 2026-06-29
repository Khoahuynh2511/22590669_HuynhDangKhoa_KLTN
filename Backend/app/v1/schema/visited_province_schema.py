"""
Visited Province Schemas
Pydantic models cho tính năng Bản đồ khám phá Việt Nam (check-in tỉnh thành).
Pattern theo favorite_schema.py (EC/EM convention).
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProvinceDetail(BaseModel):
    """Một tỉnh/thành (không kèm trạng thái visited)."""
    province_id: UUID
    province_code: str
    province_name: str
    province_name_en: Optional[str] = None
    region: str  # 'north' | 'central' | 'south'
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class VisitedProvinceItem(ProvinceDetail):
    """Một tỉnh đã được user check-in."""
    visit_id: UUID
    visited_at: datetime
    visit_source: str  # 'manual' | 'auto_booking'

    model_config = ConfigDict(from_attributes=True)


class AddVisitedRequest(BaseModel):
    province_id: UUID = Field(..., description="ID của province cần check-in / bỏ check-in")
    model_config = ConfigDict(
        json_schema_extra={"example": {"province_id": "07e8c89e-90d4-4ebc-9302-384dc6cb2f0c"}}
    )


class VisitedResponse(BaseModel):
    """Response cho add/remove visited."""
    EC: int = Field(0, description="Error code (0 = success)")
    EM: str = Field("Success", description="Error message")
    is_visited: bool = Field(..., description="Trạng thái visited sau thao tác")


class VisitedListResponse(BaseModel):
    """Response cho GET /my — kèm thống kê tiến độ khám phá."""
    EC: int = Field(0, description="Error code")
    EM: str = Field("Success", description="Error message")
    total: int = Field(0, description="Tổng số tỉnh đã đến")
    total_provinces: int = Field(63, description="Tổng số tỉnh của VN (63)")
    north_count: int = Field(0, description="Số tỉnh miền Bắc đã đến")
    central_count: int = Field(0, description="Số tỉnh miền Trung đã đến")
    south_count: int = Field(0, description="Số tỉnh miền Nam đã đến")
    progress_percentage: float = Field(0, description="Tiến độ khám phá (%)")
    provinces: List[VisitedProvinceItem] = Field(default_factory=list)


class ProvinceListResponse(BaseModel):
    """Response cho GET /provinces — danh sách 63 tỉnh để render bản đồ."""
    EC: int = Field(0, description="Error code")
    EM: str = Field("Success", description="Error message")
    total: int = Field(0, description="Tổng số tỉnh")
    provinces: List[ProvinceDetail] = Field(default_factory=list)


class AutoCheckinResponse(BaseModel):
    """Response cho POST /auto-checkin — đồng bộ từ booking đã xác nhận."""
    EC: int = Field(0, description="Error code")
    EM: str = Field("Success", description="Error message")
    auto_checkins: int = Field(0, description="Số tỉnh mới được check-in tự động")
    matched: List[str] = Field(default_factory=list, description="Tên các tỉnh đã match (minh bạch)")


class LeaderboardUserItem(BaseModel):
    """Một dòng trong bảng xếp hạng người khám phá."""
    user_id: UUID
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    provinces_visited: int = Field(0, description="Số tỉnh đã check-in")
    north_count: int = Field(0, description="Số tỉnh miền Bắc")
    central_count: int = Field(0, description="Số tỉnh miền Trung")
    south_count: int = Field(0, description="Số tỉnh miền Nam")
    last_visit_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LeaderboardData(BaseModel):
    """Payload data cho leaderboard."""
    items: List[LeaderboardUserItem] = Field(default_factory=list)
    total: int = Field(0, description="Tổng số explorer (đã check-in ít nhất 1 tỉnh)")
    limit: int = 20
    offset: int = 0
    my_rank: Optional[int] = Field(None, description="Hạng của user hiện tại (None nếu chưa check-in)")
    my_provinces_visited: int = Field(0, description="Số tỉnh của user hiện tại")


class LeaderboardResponse(BaseModel):
    """Response cho GET /leaderboard — bảng xếp hạng người khám phá."""
    EC: int = Field(0, description="Error code")
    EM: str = Field("Success", description="Error message")
    data: LeaderboardData = Field(default_factory=LeaderboardData)
