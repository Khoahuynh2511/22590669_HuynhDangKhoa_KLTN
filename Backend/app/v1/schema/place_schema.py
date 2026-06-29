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


# ============================ Feature: Thư viện ảnh (Wikimedia Commons) ============================


class GalleryImage(BaseModel):
    """Một ảnh từ Wikimedia Commons cho một địa điểm."""
    title: str = Field(..., description="Tên file trên Commons (vd: 'Halong Bay.jpg')")
    thumb_url: str = Field(..., description="URL ảnh thu nhỏ (đã resize)")
    full_url: str = Field(..., description="URL ảnh gốc")
    description: Optional[str] = Field(None, description="Mô tả ngắn (nếu có)")
    license: Optional[str] = Field(None, description="Giấy phép rút gọn (vd: CC BY-SA 4.0)")
    license_url: Optional[str] = Field(None, description="URL giấy phép")
    author: Optional[str] = Field(None, description="Tác giả (có thể chứa HTML)")


class PlaceGalleryResponse(BaseModel):
    """Response cho GET /api/v1/places/gallery."""
    EC: int = Field(0, description="Error code")
    EM: str = Field("Success", description="Error message")
    place: str = ""
    total: int = Field(0, description="Số ảnh tìm thấy")
    images: List[GalleryImage] = Field(default_factory=list)


# ============================ Feature: Mùa đẹp nhất (Open-Meteo Archive) ============================


class SeasonMonth(BaseModel):
    """Trung bình khí hậu của 1 tháng (dựa trên dữ liệu lịch sử)."""
    month: int = Field(..., description="1-12")
    name: str = Field(..., description="Tên tháng tiếng Việt (vd: 'Tháng 1')")
    temp: Optional[float] = Field(None, description="Nhiệt độ trung bình (°C)")
    rain: Optional[float] = Field(None, description="Tổng lượng mưa (mm)")


class BestSeasonResponse(BaseModel):
    """Response cho GET /api/v1/places/best-season."""
    EC: int = Field(0, description="Error code")
    EM: str = Field("Success", description="Error message")
    place: str = ""
    monthly: List[SeasonMonth] = Field(default_factory=list, description="12 tháng khí hậu")
    best_months: List[SeasonMonth] = Field(
        default_factory=list, description="Các tháng lý tưởng nhất để đi (đã sắp xếp theo điểm)"
    )
    summary: str = Field("", description="Câu tóm tắt gợi ý mùa")


class FestivalItem(BaseModel):
    """Một lễ hội / sự kiện địa phương (từ Wikidata SPARQL / Wikipedia / dataset tĩnh)."""
    name: str = Field(..., description="Tên lễ hội")
    description: Optional[str] = Field(None, description="Mô tả ngắn")
    start_date: Optional[str] = Field(None, description="Ngày bắt đầu (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="Ngày kết thúc (YYYY-MM-DD)")
    location: Optional[str] = Field(None, description="Địa điểm")
    image_url: Optional[str] = Field(None, description="Ảnh đại diện")
    wikidata_url: Optional[str] = Field(None, description="Link thực thể Wikidata")
    wikipedia_url: Optional[str] = Field(None, description="Link bài Wikipedia")
    month: Optional[int] = Field(None, description="Tháng dương lịch xấp xỉ (1-12)")
    region: Optional[str] = Field(None, description="Miền: north/central/south (rỗng = cả nước)")
    lunar: Optional[str] = Field(None, description="Ghi chú lịch âm (nếu có)")
    country: Optional[str] = Field(None, description="Quốc gia (vd: Việt Nam, Japan); 'world' nếu trộn toàn cầu")
    source: Optional[str] = Field(None, description="Nguồn: curated/wikidata/wikipedia/nager")


class FestivalResponse(BaseModel):
    """Response cho GET /api/v1/places/festivals."""
    EC: int = Field(0, description="Error code")
    EM: str = Field("Success", description="Error message")
    province: str = Field("", description="Tên tỉnh đã lọc (rỗng nếu không lọc)")
    month: Optional[int] = Field(None, description="Tháng đã lọc (1-12, None nếu không lọc)")
    region: str = Field("", description="Miền đã lọc (rỗng nếu không lọc)")
    country: str = Field("", description="Quốc gia đã lọc (rỗng = Việt Nam mặc định; 'world' = toàn cầu)")
    festivals: List[FestivalItem] = Field(default_factory=list, description="Danh sách lễ hội")
    total: int = Field(0, description="Tổng số lễ hội tìm thấy")
