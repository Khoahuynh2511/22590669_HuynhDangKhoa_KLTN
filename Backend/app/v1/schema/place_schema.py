"""
Place Schemas
Pydantic models cho:
- Feature D: API gợi ý điểm đến open-source (Nominatim + Overpass + Wikimedia).
- Feature E: Bộ sưu tập điểm đến của user (wishlist) + gallery nơi đã đến.
Pattern theo visited_province_schema.py (EC/EM convention).
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ============================ Feature D: Place Suggestions ============================


class GeocodedLocation(BaseModel):
    """Kết quả geocode từ Nominatim."""
    lat: float
    lon: float
    display_name: str
    osm_type: Optional[str] = None
    osm_id: Optional[int] = None


class PlaceSuggestionItem(BaseModel):
    """Một điểm đến / attraction gợi ý."""
    name: str
    category: str = Field(..., description="Nhóm OSM (attraction, museum, historic, park...)")
    lat: float
    lng: float
    description: Optional[str] = None
    image_url: Optional[str] = None
    wikipedia_url: Optional[str] = None
    osm_id: int
    osm_type: str
    distance_km: float = 0.0
    saved_by_user: bool = False


class PlaceSuggestionResponse(BaseModel):
    """Response cho GET /api/v1/places/suggest."""
    EC: int = Field(0, description="Error code (0 = success)")
    EM: str = Field("Success", description="Error message")
    query: str = ""
    location: Optional[GeocodedLocation] = None
    places: List[PlaceSuggestionItem] = Field(default_factory=list)
    total: int = Field(0, description="Tổng số địa điểm tìm thấy trong bán kính (phục vụ phân trang)")
    offset: int = Field(0, description="Vị trí bắt đầu của trang hiện tại")


class GeocodeResponse(BaseModel):
    """Response cho GET /api/v1/places/geocode."""
    EC: int = Field(0, description="Error code")
    EM: str = Field("Success", description="Error message")
    location: Optional[GeocodedLocation] = None


# ============================ Feature E: Place Collection ============================


class SavePlaceRequest(BaseModel):
    """Body cho POST /api/v1/place-collections/ — lưu 1 place vào wishlist."""
    place_name: str
    place_display_name: str
    latitude: float
    longitude: float
    category: str = "attraction"
    image_url: Optional[str] = None
    description: Optional[str] = None
    wikipedia_url: Optional[str] = None
    osm_id: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "place_name": "Eiffel Tower",
                "place_display_name": "Eiffel Tower, Paris, France",
                "latitude": 48.8584,
                "longitude": 2.2945,
                "category": "attraction",
                "osm_id": 123456789,
            }
        }
    )


class SavedPlaceItem(BaseModel):
    """Một place trong wishlist của user."""
    save_id: str
    user_id: str
    place_name: str
    place_display_name: str
    latitude: float
    longitude: float
    category: str
    image_url: Optional[str] = None
    description: Optional[str] = None
    wikipedia_url: Optional[str] = None
    osm_id: int
    source: str = "manual"
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SavePlaceResponse(BaseModel):
    """Response cho POST/DELETE place-collections."""
    EC: int = Field(0, description="Error code")
    EM: str = Field("Success", description="Error message")
    is_saved: bool = Field(..., description="True nếu đang lưu, False nếu đã bỏ")


class PlaceExistsResponse(BaseModel):
    """Response cho GET /place-collections/exists."""
    EC: int = Field(0, description="Error code")
    EM: str = Field("Success", description="Error message")
    is_saved: bool = False


class PlaceCollectionResponse(BaseModel):
    """Response cho GET /place-collections/ — wishlist của user."""
    EC: int = Field(0, description="Error code")
    EM: str = Field("Success", description="Error message")
    total: int = Field(0, description="Tổng số place đã lưu")
    wishlist: List[SavedPlaceItem] = Field(default_factory=list)


class CombinedCollectionResponse(BaseModel):
    """
    Response cho GET /place-collections/combined.
    Gộp wishlist (user_place_saves) + nơi đã đến (visited_provinces).
    """
    EC: int = Field(0, description="Error code")
    EM: str = Field("Success", description="Error message")
    total_wishlist: int = Field(0, description="Số place trong wishlist")
    total_visited: int = Field(0, description="Số tỉnh đã check-in")
    wishlist: List[SavedPlaceItem] = Field(default_factory=list)
    visited_provinces: List[dict] = Field(default_factory=list)
