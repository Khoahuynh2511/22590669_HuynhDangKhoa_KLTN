"""
Hotel Tools Schema
Input schemas for hotel-related MCP tools
"""
from pydantic import BaseModel, Field


class SearchHotelsInput(BaseModel):
    """Input schema for search_hotels tool"""
    location: str = Field(default="", description="Dia diem tim kiem (vd: 'Bandung', 'Bali', 'Garut')")
    min_price: float = Field(default=0, ge=0, description="Gia toi thieu (VND)")
    max_price: float = Field(default=0, ge=0, description="Gia toi da (VND, 0 = khong gioi han)")
    limit: int = Field(default=5, ge=1, le=20, description="So ket qua toi da (1-20)")


class BookHotelInput(BaseModel):
    """Input schema for book_hotel tool"""
    hotel_id: str = Field(..., description="ID khach san")
    guest_name: str = Field(..., description="Ho ten khach")
    guest_phone: str = Field(..., description="So dien thoai")
    guest_email: str = Field(..., description="Email")
    check_in: str = Field(..., description="Ngay nhan phong (YYYY-MM-DD)")
    check_out: str = Field(..., description="Ngay tra phong (YYYY-MM-DD)")
    num_rooms: int = Field(default=1, ge=1, description="So phong")
    num_guests: int = Field(default=1, ge=1, description="So khach")
