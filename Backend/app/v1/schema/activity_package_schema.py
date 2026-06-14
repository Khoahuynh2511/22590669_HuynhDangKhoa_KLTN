"""
Activity Package Schema Definitions
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class ActivityPackageBase(BaseModel):
    """Base schema for activity package"""
    name: str = Field(..., min_length=1, max_length=255, description="Tên hoạt động")
    description: Optional[str] = Field(None, description="Mô tả chi tiết")
    destination: str = Field(..., min_length=1, max_length=255, description="Điểm đến")
    time_slot: str = Field(..., description="Khung thời gian (morning/afternoon/evening)")
    category: Optional[str] = Field(None, max_length=100, description="Thể loại")
    duration_hours: Optional[float] = Field(None, description="Thời lượng (giờ)")
    price: float = Field(..., ge=0, description="Giá dịch vụ")
    difficulty: Optional[str] = Field(None, description="Độ khó (easy/moderate/hard)")
    location: Optional[str] = Field(None, max_length=255, description="Địa điểm cụ thể")
    image_url: Optional[str] = Field(None, description="URL hình ảnh chính")
    gallery_urls: Optional[List[str]] = Field(default=None, description="Các hình ảnh khác")
    included_services: Optional[List[str]] = Field(default=None, description="Dịch vụ đi kèm")
    max_participants: Optional[int] = Field(20, description="Số lượng người tối đa")
    min_participants: Optional[int] = Field(1, description="Số lượng người tối thiểu")
    is_active: bool = Field(default=True, description="Trạng thái hoạt động")


class ActivityPackageCreate(ActivityPackageBase):
    """Schema for creating a new activity package"""
    pass


class ActivityPackageUpdate(BaseModel):
    """Schema for updating activity package"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    destination: Optional[str] = Field(None, min_length=1, max_length=255)
    time_slot: Optional[str] = None
    category: Optional[str] = None
    duration_hours: Optional[float] = None
    price: Optional[float] = Field(None, ge=0)
    difficulty: Optional[str] = None
    location: Optional[str] = None
    image_url: Optional[str] = None
    gallery_urls: Optional[List[str]] = None
    included_services: Optional[List[str]] = None
    max_participants: Optional[int] = None
    min_participants: Optional[int] = None
    is_active: Optional[bool] = None


class ActivityPackageResponse(ActivityPackageBase):
    """Schema for activity package response"""
    activity_id: UUID
    is_ai_generated: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ActivityPackageListResponse(BaseModel):
    """Schema for list of activity packages"""
    EC: int = Field(0, description="Error code (0 = success)")
    EM: str = Field("Success", description="Error message")
    total: int = Field(..., description="Tổng số hoạt động")
    data: List[ActivityPackageResponse] = Field(..., description="Danh sách hoạt động")
