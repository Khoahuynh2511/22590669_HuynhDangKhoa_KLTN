"""
Place Suggestion Service
Gợi ý điểm đến / attraction du lịch TOÀN CẦU dùng stack open-source (không cần API key):
- Nominatim (OpenStreetMap): forward geocoding (tên địa điểm -> tọa độ).
- Overpass API: truy vấn POI du lịch (tourism/historic/leisure) trong bounding box.
- Wikimedia REST API: mô tả + ảnh thumbnail cho từng địa điểm.

Backend proxy để tuân thủ OSM usage policy (User-Agent + giới hạn tần suất qua cache)
và tránh CORS từ frontend. Pattern theo weather_tools.py (httpx async + try/except).
"""
import logging
import math
import re
import time
import asyncio
import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote as urlquote

import httpx

from ..core.config import settings
from .vn_festivals_data import filter_static_festivals
from .world_festivals_data import filter_static_world_festivals
from .world_countries_data import resolve_country

logger = logging.getLogger(__name__)

# Cache cấp module (persist giữa các request vì service được tạo mới mỗi request).
# {cache_key: (timestamp_seconds, data)}
_CACHE: Dict[str, Tuple[float, Any]] = {}

# Overpass mirrors (dự phòng nếu server chính chậm/cúp).
_OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def _now() -> float:
    return time.monotonic()


def _strip_diacritics(text: str) -> str:
    """Bỏ dấu tiếng Việt để so khớp tên tỉnh linh hoạt (vd: 'Hà Nội' -> 'ha noi')."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    stripped = stripped.replace("đ", "d").replace("Đ", "d")
    return re.sub(r"\s+", " ", stripped).strip().lower()


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Khoảng cách lớn vòng tròn lớn giữa 2 tọa độ (km)."""
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _bbox_around(lat: float, lng: float, radius_km: float) -> Tuple[float, float, float, float]:
    """Tính (south, west, north, east) từ tâm + bán kính."""
    lat_delta = radius_km / 111.0
    lon_delta = radius_km / (111.0 * max(math.cos(math.radians(lat)), 1e-6))
    return (lat - lat_delta, lng - lon_delta, lat + lat_delta, lng + lon_delta)


class PlaceSuggestionService:
    """Service gợi ý địa điểm du lịch toàn cầu (open-source, key-free)."""

    def _user_agent(self) -> str:
        return f"UITravel/1.0 ({settings.OSM_CONTACT_EMAIL})"

    # ----------------------------- cache helpers -----------------------------
    def _cache_get(self, key: str) -> Optional[Any]:
        entry = _CACHE.get(key)
        if not entry:
            return None
        ts, data = entry
        if _now() - ts > settings.PLACE_CACHE_TTL_SECONDS:
            _CACHE.pop(key, None)
            return None
        return data

    def _cache_set(self, key: str, data: Any) -> None:
        _CACHE[key] = (_now(), data)

    # ----------------------------- Geocoding (fallback chain) -----------------
    async def geocode_place(self, query: str) -> Dict[str, Any]:
        """
        Forward geocoding: tên địa điểm -> lat/lng + display_name.
        Chain: Photon (OSM) -> Open-Meteo -> Nominatim. Trả {} nếu tất cả fail.
        (Nominatim public hay chặn 403 nên để cuối.)
        """
        q = (query or "").strip()
        if not q:
            return {}
        cache_key = f"geo:{q.lower()}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        for fn in (self._geocode_photon, self._geocode_open_meteo, self._geocode_nominatim):
            try:
                result = await fn(q)
                if result:
                    self._cache_set(cache_key, result)
                    return result
            except Exception as e:
                logger.warning("Geocoder %s failed for '%s': %s", fn.__name__, q, e)
                continue
        return {}

    async def _geocode_photon(self, q: str) -> Dict[str, Any]:
        """Photon (Komoot) - OSM-based, khá cho phép, không cần key."""
        async with httpx.AsyncClient(
            timeout=settings.PLACE_REQUEST_TIMEOUT, headers={"User-Agent": self._user_agent()}
        ) as client:
            resp = await client.get(settings.PHOTON_BASE_URL, params={"q": q, "limit": 1})
            resp.raise_for_status()
            data = resp.json()
        feats = data.get("features") or []
        if not feats:
            return {}
        f = feats[0]
        coords = (f.get("geometry") or {}).get("coordinates") or []
        if len(coords) < 2:
            return {}
        lon, lat = coords[0], coords[1]
        p = f.get("properties") or {}
        parts = [p.get("name"), p.get("city"), p.get("state"), p.get("country")]
        display = ", ".join([x for x in parts if x]) or q
        osm_type_map = {"N": "node", "W": "way", "R": "relation"}
        return {
            "lat": float(lat),
            "lon": float(lon),
            "display_name": display,
            "osm_type": osm_type_map.get(p.get("osm_type"), p.get("osm_type")),
            "osm_id": int(p["osm_id"]) if p.get("osm_id") else None,
        }

    async def _geocode_open_meteo(self, q: str) -> Dict[str, Any]:
        """Open-Meteo geocoding - rất ổn định, không cần key (không có osm_id)."""
        async with httpx.AsyncClient(
            timeout=settings.PLACE_REQUEST_TIMEOUT, headers={"User-Agent": self._user_agent()}
        ) as client:
            resp = await client.get(
                settings.OPEN_METEO_GEOCODE_URL,
                params={"name": q, "count": 1, "language": "vi", "format": "json"},
            )
            resp.raise_for_status()
            data = resp.json()
        results = data.get("results") or []
        if not results:
            return {}
        item = results[0]
        parts = [item.get("name"), item.get("admin1"), item.get("country")]
        display = ", ".join([x for x in parts if x]) or q
        return {
            "lat": float(item["latitude"]),
            "lon": float(item["longitude"]),
            "display_name": display,
            "osm_type": None,
            "osm_id": None,
        }

    async def _geocode_nominatim(self, q: str) -> Dict[str, Any]:
        """Nominatim (OSM) - fallback cuối (public instance hay chặn 403)."""
        async with httpx.AsyncClient(
            timeout=settings.PLACE_REQUEST_TIMEOUT, headers={"User-Agent": self._user_agent()}
        ) as client:
            resp = await client.get(
                f"{settings.NOMINATIM_BASE_URL}/search",
                params={"q": q, "format": "json", "limit": 1, "addressdetails": 0, "accept-language": "vi,en"},
            )
            resp.raise_for_status()
            data = resp.json()
        if not data:
            return {}
        r = data[0]
        return {
            "lat": float(r.get("lat")),
            "lon": float(r.get("lon")),
            "display_name": r.get("display_name", q),
            "osm_type": r.get("osm_type"),
            "osm_id": int(r["osm_id"]) if r.get("osm_id") else None,
        }

    # ----------------------------- Overpass ----------------------------------
    async def get_tourist_attractions(
        self, client: httpx.AsyncClient, lat: float, lng: float, radius_km: float = 10.0
    ) -> List[Dict[str, Any]]:
        """Truy vấn POI du lịch trong bounding box qua Overpass API."""
        south, west, north, east = _bbox_around(lat, lng, radius_km)
        # Làm tròn để tăng cache hit khi các query gần nhau.
        cache_key = f"ovp:{round(lat, 3)}:{round(lng, 3)}:{round(radius_km, 1)}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        bbox = f"{south},{west},{north},{east}"
        # POI du lịch: attractions, museum, viewpoint, gallery, artwork + historic + leisure park/garden.
        overpass_query = f"""
[out:json][timeout:25];
(
  nwr["tourism"~"attraction|museum|viewpoint|gallery|artwork|theme_park|zoo"]({bbox});
  nwr["historic"~"monument|castle|ruins|archaeological_site|memorial"]({bbox});
  nwr["leisure"~"park|garden|nature_reserve"]({bbox});
);
out center tags;
"""
        headers = {"User-Agent": self._user_agent(), "Content-Type": "text/plain; charset=utf-8"}
        last_err = None
        for endpoint in _OVERPASS_ENDPOINTS:
            try:
                resp = await client.post(
                    endpoint, content=overpass_query, headers=headers, timeout=settings.OVERPASS_TIMEOUT
                )
                resp.raise_for_status()
                data = resp.json()
                return self._parse_overpass(data, lat, lng, cache_key)
            except Exception as e:
                last_err = e
                logger.warning("Overpass endpoint %s failed: %s", endpoint, e)
                continue
        logger.error("All Overpass endpoints failed: %s", last_err)
        return []

    def _parse_overpass(
        self, data: Dict[str, Any], center_lat: float, center_lng: float, cache_key: str
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for el in data.get("elements", []):
            tags = el.get("tags") or {}
            # Tọa độ: node có lat/lon trực tiếp; way/relation dùng center.
            if "center" in el:
                lat = el["center"].get("lat")
                lng = el["center"].get("lon")
            else:
                lat = el.get("lat")
                lng = el.get("lon")
            if lat is None or lng is None:
                continue
            # Ưu tiên tên tiếng Việt, rồi tên gốc, rồi tiếng Anh. Bỏ qua POI không tên.
            name = tags.get("name:vi") or tags.get("name") or tags.get("name:en")
            if not name:
                continue
            category = self._derive_category(tags)
            results.append(
                {
                    "name": name,
                    "category": category,
                    "lat": float(lat),
                    "lng": float(lng),
                    "osm_id": int(el.get("id", 0)),
                    "osm_type": el.get("type", "node"),
                    "distance_km": round(_haversine_km(center_lat, center_lng, float(lat), float(lng)), 2),
                    "tags": tags,
                }
            )
        # Sắp xếp theo khoảng cách, khử trùng theo osm_id.
        seen = set()
        deduped = []
        for r in sorted(results, key=lambda x: x["distance_km"]):
            if r["osm_id"] in seen:
                continue
            seen.add(r["osm_id"])
            deduped.append(r)
        self._cache_set(cache_key, deduped)
        return deduped

    @staticmethod
    def _derive_category(tags: Dict[str, Any]) -> str:
        if tags.get("tourism") == "museum":
            return "museum"
        if tags.get("tourism") == "viewpoint":
            return "viewpoint"
        if tags.get("tourism") in ("theme_park", "zoo"):
            return "theme_park"
        if tags.get("historic"):
            return "historic"
        if tags.get("leisure"):
            return "park"
        return "attraction"

    # ----------------------------- Wikimedia ---------------------------------
    async def enrich_place_with_wikipedia(
        self, client: httpx.AsyncClient, place_name: str, tags: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Lấy mô tả + ảnh thumbnail từ Wikimedia REST API (fallback mềm)."""
        # Ưu tiên title từ tag wikipedia/wikidata.
        title = self._wikipedia_title(tags) or place_name.replace(" ", "_")
        if not title:
            return {"description": None, "image_url": None, "wikipedia_url": None}
        cache_key = f"wiki:{title.lower()}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        url = f"{settings.WIKIPEDIA_REST_URL}/page/summary/{urlquote(title, safe='_')}"
        try:
            resp = await client.get(url, headers={"User-Agent": self._user_agent()})
            if resp.status_code == 404:
                empty = {"description": None, "image_url": None, "wikipedia_url": None}
                self._cache_set(cache_key, empty)
                return empty
            resp.raise_for_status()
            data = resp.json()
            result = {
                "description": data.get("extract"),
                "image_url": (data.get("thumbnail") or {}).get("source")
                if data.get("thumbnail")
                else data.get("originalimage", {}).get("source"),
                "wikipedia_url": (data.get("content_urls") or {}).get("desktop", {}).get("page"),
            }
            self._cache_set(cache_key, result)
            return result
        except Exception as e:
            logger.warning("Wikimedia enrich failed for '%s': %s", title, e)
            return {"description": None, "image_url": None, "wikipedia_url": None}

    @staticmethod
    def _wikipedia_title(tags: Dict[str, Any]) -> Optional[str]:
        wp = tags.get("wikipedia")
        if wp:
            # Định dạng "en:Title Here" hoặc "Title Here" -> lấy phần title.
            if ":" in wp:
                _lang, title = wp.split(":", 1)
            else:
                title = wp
            return title.strip().replace(" ", "_")
        return None

    # ----------------------------- Wikimedia Commons (gallery) ---------------
    async def get_place_gallery(self, place_name: str, limit: int = 12) -> Dict[str, Any]:
        """
        Tìm ảnh của một địa điểm trên Wikimedia Commons (ảnh CC, không cần key).
        Dùng generator=search trong namespace File (6) + imageinfo (thumb + license).
        Trả dict EC/EM + images[]. Cache theo (place, limit) để tiết kiệm request.
        """
        q = (place_name or "").strip()
        if not q:
            return {"EC": 1, "EM": "Vui lòng nhập tên địa điểm", "place": q, "total": 0, "images": []}

        cache_key = f"gallery:{q.lower()}:{limit}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": q,
            "gsrnamespace": 6,  # File namespace
            "gsrlimit": min(max(limit, 1), 24),
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": 1024,
            "redirects": 1,
        }
        try:
            async with httpx.AsyncClient(
                timeout=settings.PLACE_REQUEST_TIMEOUT, headers={"User-Agent": self._user_agent()}
            ) as client:
                resp = await client.get(settings.WIKIMEDIA_COMMONS_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.warning("Commons gallery failed for '%s': %s", q, e)
            result = {"EC": 0, "EM": "Không lấy được ảnh (Commons lỗi)", "place": q, "total": 0, "images": []}
            self._cache_set(cache_key, result)
            return result

        pages = (data.get("query") or {}).get("pages") or {}
        allowed_ext = (".jpg", ".jpeg", ".png", ".webp", ".gif")
        images: List[Dict[str, Any]] = []
        # pages là dict {pageid: {...}} -> duyệt giá trị.
        for page in pages.values():
            title = page.get("title") or ""
            if not title.lower().endswith(allowed_ext):
                continue
            info_list = page.get("imageinfo") or []
            if not info_list:
                continue
            info = info_list[0]
            thumb = info.get("thumburl") or info.get("url")
            full = info.get("url")
            if not thumb or not full:
                continue
            ext = info.get("extmetadata") or {}
            images.append(
                {
                    "title": title,
                    "thumb_url": thumb,
                    "full_url": full,
                    "description": self._strip_html((ext.get("ImageDescription") or {}).get("value")),
                    "license": (ext.get("LicenseShortName") or {}).get("value"),
                    "license_url": (ext.get("UsageTerms") or {}).get("value"),
                    "author": self._strip_html((ext.get("Artist") or {}).get("value")),
                }
            )
            if len(images) >= limit:
                break

        result = {"EC": 0, "EM": "Success", "place": q, "total": len(images), "images": images}
        self._cache_set(cache_key, result)
        return result

    @staticmethod
    def _strip_html(value: Optional[Any]) -> Optional[str]:
        """ Commons extmetadata thường chứa HTML thô -> lọc thẻ + giới hạn độ dài. """
        if not value:
            return None
        text = re.sub(r"<[^>]+>", "", str(value)).replace("&nbsp;", " ").strip()
        return text[:300] or None

    # ----------------------------- Open-Meteo Archive (best season) ---------
    _MONTH_NAMES_VI = [
        "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6",
        "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12",
    ]

    async def get_best_season(self, lat: float, lng: float, place_name: str = "") -> Dict[str, Any]:
        """
        Gợi ý "mùa đẹp nhất" dựa trên khí hậu lịch sử (Open-Meteo Archive, không cần key).
        Archive API chỉ trả dữ liệu NGÀY -> lấy cả năm 2023 rồi gom thành trung bình/tổng
        theo tháng (nhiệt độ + mưa), chấm điểm từng tháng (ưa ~25°C + ít mưa), trả top tháng
        + 12 tháng để FE vẽ biểu đồ.
        """
        try:
            lat_f = float(lat)
            lng_f = float(lng)
        except (TypeError, ValueError):
            return {
                "EC": 1, "EM": "Tọa độ không hợp lệ", "place": place_name,
                "monthly": [], "best_months": [], "summary": "",
            }

        cache_key = f"season:{round(lat_f, 2)}:{round(lng_f, 2)}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            # Cache theo tọa độ; ghi đè nhãn `place` theo request hiện tại.
            return {**cached, "place": place_name}

        params = {
            "latitude": lat_f,
            "longitude": lng_f,
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            # Archive API chỉ hỗ trợ `daily` (không có `monthly`) -> gom theo tháng sau.
            "daily": "temperature_2m_mean,precipitation_sum",
            "timezone": "auto",
        }
        try:
            async with httpx.AsyncClient(
                timeout=settings.PLACE_REQUEST_TIMEOUT, headers={"User-Agent": self._user_agent()}
            ) as client:
                resp = await client.get(settings.OPEN_METEO_ARCHIVE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.warning("Open-Meteo archive failed for (%s,%s): %s", lat_f, lng_f, e)
            return {
                "EC": 0, "EM": "Không lấy được dữ liệu khí hậu", "place": place_name,
                "monthly": [], "best_months": [], "summary": "",
            }

        # Archive API trả về dữ liệu NGÀY (365) -> gom thành trung bình/tổng theo tháng.
        daily_block = data.get("daily") or {}
        times = daily_block.get("time") or []
        daily_temps = daily_block.get("temperature_2m_mean") or []
        daily_rains = daily_block.get("precipitation_sum") or []

        sum_t: Dict[int, float] = {}
        cnt_t: Dict[int, int] = {}
        sum_r: Dict[int, float] = {}
        for i, day in enumerate(times):
            try:
                month = int(str(day)[5:7])  # "2023-03-15" -> 3
            except (ValueError, IndexError):
                continue
            if not 1 <= month <= 12:
                continue
            t = daily_temps[i] if i < len(daily_temps) else None
            r = daily_rains[i] if i < len(daily_rains) else None
            if t is not None:
                sum_t[month] = sum_t.get(month, 0.0) + float(t)
                cnt_t[month] = cnt_t.get(month, 0) + 1
            if r is not None:
                sum_r[month] = sum_r.get(month, 0.0) + float(r)

        monthly: List[Dict[str, Any]] = []
        scored: List[tuple] = []  # (score, month_index)
        for i in range(12):
            month = i + 1
            t = round(sum_t[month] / cnt_t[month], 1) if cnt_t.get(month) else None
            r = round(sum_r[month], 1) if month in sum_r else None
            monthly.append(
                {
                    "month": month,
                    "name": self._MONTH_NAMES_VI[i],
                    "temp": t,
                    "rain": r,
                }
            )
            if t is not None and r is not None:
                # Ưu tiên nhiệt độ dễ chịu (~25°C) + ít mưa; phạt nóng/lạnh quá mức.
                score = 100 - abs(t - 25.0) * 3.0 - r * 1.5
                scored.append((score, i))

        scored.sort(key=lambda x: x[0], reverse=True)
        best_idx = sorted(i for _, i in scored[:3])  # theo thứ tự lịch cho hiển thị
        best_months = [monthly[i] for i in best_idx]

        result = {
            "EC": 0,
            "EM": "Success",
            "place": place_name,
            "monthly": monthly,
            "best_months": best_months,
            "summary": self._build_season_summary(best_months),
        }
        self._cache_set(cache_key, result)
        return result

    @staticmethod
    def _build_season_summary(best_months: List[Dict[str, Any]]) -> str:
        if not best_months:
            return "Chưa có đủ dữ liệu khí hậu để gợi ý mùa lý tưởng."
        names = ", ".join(m["name"] for m in best_months)
        return f"Mùa lý tưởng để đến đây khoảng {names} — thời tiết dễ chịu, ít mưa."

    # ----------------------------- orchestrator ------------------------------
    async def suggest_places(
        self, query: str, limit: int = 10, radius_km: float = 10.0, offset: int = 0
    ) -> Dict[str, Any]:
        """
        Pipeline: geocode query -> Overpass POI -> enrich Wikimedia -> trả list.
        Hỗ trợ phân trang qua `offset`: Overpass trả toàn bộ POI trong bbox (đã cache
        theo lat/lng/radius), nên các trang sau chỉ enrich thêm mà không gọi lại Overpass.
        Trả về dict theo convention EC/EM, kèm `total` (tổng số POI) và `offset`.
        """
        q = (query or "").strip()
        if not q:
            return {
                "EC": 1,
                "EM": "Vui lòng nhập tên địa điểm",
                "query": q,
                "location": None,
                "places": [],
                "total": 0,
                "offset": offset,
            }

        location = await self.geocode_place(q)
        if not location:
            return {
                "EC": 1,
                "EM": f"Không tìm thấy địa điểm '{q}'",
                "query": q,
                "location": None,
                "places": [],
                "total": 0,
                "offset": offset,
            }

        async with httpx.AsyncClient(timeout=settings.PLACE_REQUEST_TIMEOUT) as client:
            attractions = await self.get_tourist_attractions(
                client, location["lat"], location["lon"], radius_km=radius_km
            )
            total = len(attractions)
            page = attractions[offset : offset + limit]
            # Enrich song song để nhanh hơn.
            enriched_details = []
            for item in page:
                enriched_details.append(
                    await self.enrich_place_with_wikipedia(client, item["name"], item.get("tags", {}))
                )

        places = []
        for item, extra in zip(page, enriched_details):
            places.append(
                {
                    "name": item["name"],
                    "category": item["category"],
                    "lat": item["lat"],
                    "lng": item["lng"],
                    "description": extra.get("description"),
                    "image_url": extra.get("image_url"),
                    "wikipedia_url": extra.get("wikipedia_url"),
                    "osm_id": item["osm_id"],
                    "osm_type": item["osm_type"],
                    "distance_km": item["distance_km"],
                    "saved_by_user": False,  # router sẽ set nếu user login
                }
            )

        return {
            "EC": 0,
            "EM": "Success",
            "query": q,
            "location": location,
            "places": places,
            "total": total,
            "offset": offset,
        }

    # ----------------------------- Wikidata SPARQL (festivals) --------------
    async def get_local_festivals(
        self,
        province_name: Optional[str] = None,
        month: Optional[int] = None,
        region: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        country: Optional[str] = None,
        country_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Lễ hội / sự kiện — TOÀN CẦU, kết hợp các nguồn open-source (key-free):
          1) Dataset tĩnh (curated VN + world): nguồn chính, đủ dữ liệu hiển thị.
          2) [TẮT] Wikidata SPARQL — hay bị rate-limit (429)/outage.
          3) Nager.Date: ngày nghỉ pháp định có ngày chính xác (cho 1 nước cụ thể).
          4) Wikipedia action API: enrich mô tả/ảnh (chỉ VN browse-all).
        `country`/`country_code`:
          - để trống          -> Việt Nam (mặc định, backward-compatible).
          - "world"/"toàn cầu" -> toàn thế giới (bỏ filter quốc gia ở SPARQL).
          - tên/mã ISO2       -> một nước cụ thể (vd "Nhật Bản", "JP", "Thailand").
        Lọc thêm theo `month` (1-12), `region` (north/central/south — chỉ VN) và
        `province_name` (best-effort, bỏ dấu). KHÔNG ném lỗi — luôn trả list.
        """
        resolved = resolve_country(country=country, country_code=country_code)
        if resolved.get("mode") == "unknown":
            return {
                "EC": 1,
                "EM": (f"Không nhận diện được quốc gia '{resolved.get('raw', '')}'. "
                       "Dùng mã ISO2 (vd: JP, TH) hoặc tên tiếng Việt/Anh."),
                "province": (province_name or ""),
                "month": month,
                "region": (region or ""),
                "country": (country or ""),
                "festivals": [],
                "total": 0,
            }

        mode = resolved["mode"]
        is_vn = mode == "vn"
        is_world = mode == "world"
        country_label = "" if is_world else (resolved.get("vi") or resolved.get("en") or "")
        country_qid = None if is_world else resolved.get("qid")  # VN -> "Q881"
        iso2 = None if is_world else resolved.get("iso2")  # VN -> "VN"

        prov = (province_name or "").strip()
        reg = (region or "").strip()
        cache_key = f"festivals:{mode}:{resolved.get('iso2', '')}:{prov.lower()}:{reg}:{month if month else 'all'}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        prov_norm = _strip_diacritics(prov)
        browse_all = not prov_norm and not reg and not month
        seen: set = set()
        festivals: List[Dict[str, Any]] = []

        def _add(items: List[Dict[str, Any]]) -> None:
            for f in items or []:
                key = (f.get("name") or "").strip().lower()
                if key and key not in seen:
                    seen.add(key)
                    # Bảo đảm mỗi item đều có nhãn country (static/wiki chưa set).
                    f.setdefault("country", country_label if not is_world else (f.get("country") or ""))
                    festivals.append(f)

        # (1) Dataset tĩnh VN — chỉ cho Việt Nam (và world như tập con curated).
        if is_vn or is_world:
            _add(filter_static_festivals(month=month, province_norm=prov_norm, region=reg))

        # (1b) Dataset tĩnh THẾ GIỚI — lưới an toàn khi Wikidata SPARQL bị rate-limit (429).
        #     Chỉ nạp khi KHÔNG phải VN (tránh trùng với curated VN).
        if not is_vn:
            _add(filter_static_world_festivals(month=month, country_iso2=iso2, is_world=is_world))

        # (2) Wikidata SPARQL đã TẮT — endpoint hay rate-limit (429)/outage.
        #     Dataset tĩnh (curated VN + world) là nguồn chính, đủ để hiển thị.
        # Bật lại nếu cần: _add(self._apply_festival_filters(
        #     await self._sparql_festivals(country_qid=country_qid), month, prov_norm))

        # (3) Nager.Date — public holidays có ngày chính xác (chỉ khi chọn 1 nước cụ thể).
        if iso2:
            _add(self._apply_festival_filters(
                await self._nager_public_holidays(iso2, country_label, month=month), month, prov_norm
            ))

        # (4) Wikipedia action API — chỉ enrich cho VN browse-all (category VN).
        if browse_all and is_vn:
            _add(await self._fetch_festivals_from_wikipedia())

        result = {
            "EC": 0,
            "EM": "Success",
            "province": prov,
            "month": month,
            "region": reg,
            "country": "world" if is_world else country_label,
            "festivals": festivals,
            "total": len(festivals),
        }
        self._cache_set(cache_key, result)
        return result

    @staticmethod
    def _apply_festival_filters(
        items: List[Dict[str, Any]], month: Optional[int], prov_norm: str
    ) -> List[Dict[str, Any]]:
        """Lọc danh sách lễ hội theo tháng (từ start_date) và tỉnh (đã strip dấu)."""
        out: List[Dict[str, Any]] = []
        for f in items or []:
            if month:
                sd = (f.get("start_date") or "")[:10]
                if not sd:
                    continue
                try:
                    if int(sd[5:7]) != int(month):
                        continue
                except (ValueError, IndexError):
                    continue
            if prov_norm:
                hay = _strip_diacritics(f.get("location") or "") + " " + _strip_diacritics(f.get("name") or "")
                if prov_norm not in hay:
                    continue
            out.append(f)
        return out

    async def _sparql_festivals(
        self, country_qid: Optional[str] = None, limit: int = 300
    ) -> List[Dict[str, Any]]:
        """
        Lấy lễ hội từ Wikidata SPARQL (open-source, CC0, key-free).
        - `country_qid` (vd "Q881" VN): lọc theo một quốc gia (P17 trực tiếp hoặc qua
          P131/P276 nằm trong nước đó).
        - `country_qid=None`: TOÀN CẦU (không lọc quốc gia) — dùng cho chế độ "world".
        Trả [] nếu lỗi/rate-limit (không ném). `?country` luôn được chọn để gán nhãn nước.
        """
        if country_qid:
            # BIND ?country để label service tự sinh ?countryLabel cho mọi kết quả.
            country_block = (
                f"BIND(wd:{country_qid} AS ?country)\n"
                "          {\n"
                "            ?item wdt:P17 ?country .\n"
                "          } UNION {\n"
                "            ?item wdt:P131 ?loc . ?loc wdt:P17 ?country .\n"
                "          } UNION {\n"
                "            ?item wdt:P276 ?loc . ?loc wdt:P17 ?country .\n"
                "          }"
            )
        else:
            country_block = (
                "OPTIONAL { ?item wdt:P17 ?country . }\n"
                "          OPTIONAL { ?item wdt:P131 ?loc . }\n"
                "          OPTIONAL { ?item wdt:P276 ?loc . }"
            )
        sparql = (
            """
        SELECT ?item ?itemLabel ?itemDescription ?start ?end ?locLabel ?countryLabel ?img WHERE {
          ?item wdt:P31/wdt:P279* wd:Q1322410 .
          __COUNTRY_BLOCK__
          OPTIONAL { ?item wdt:P580 ?start . }
          OPTIONAL { ?item wdt:P582 ?end . }
          OPTIONAL { ?item wdt:P18 ?img . }
          SERVICE wikibase:label { bd:serviceParam wikibase:language "vi,en". }
        }
        LIMIT __LIMIT__
        """
            .replace("__COUNTRY_BLOCK__", country_block)
            .replace("__LIMIT__", str(limit))
        )
        try:
            async with httpx.AsyncClient(
                timeout=settings.WIKIDATA_REQUEST_TIMEOUT,
                headers={
                    "User-Agent": self._user_agent(),
                    "Accept": "application/sparql-results+json",
                },
            ) as client:
                resp = await client.get(
                    settings.WIKIDATA_SPARQL_URL, params={"query": sparql, "format": "json"}
                )
                # 429 = rate-limit (WDQS hay ép "1 req/min" trong đợt outage): KHÔNG retry —
                # 3s < 60s nên retry vô ích. Fail-fast về nguồn thay thế (curated/Nager),
                # kết quả tốt sẽ được cache 7 ngày nên traffic lặp lại không tốn thêm.
                if resp.status_code == 429:
                    logger.info(
                        "Wikidata SPARQL rate-limited (429) — tạm dùng nguồn thay thế (WDQS có thể đang outage)."
                    )
                    return []
                # 5xx = lỗi tạm thời của server -> thử lại 1 lần theo Retry-After (max ~5s).
                if 500 <= resp.status_code <= 599 and resp.status_code != 501:
                    wait = 3
                    try:
                        wait = max(1, min(int(resp.headers.get("Retry-After", "3")), 5))
                    except (TypeError, ValueError):
                        pass
                    await asyncio.sleep(wait)
                    resp = await client.get(
                        settings.WIKIDATA_SPARQL_URL, params={"query": sparql, "format": "json"}
                    )
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.warning("Wikidata SPARQL failed: %s", e)
            return []

        out: List[Dict[str, Any]] = []
        for b in data.get("results", {}).get("bindings", []):
            name = (b.get("itemLabel") or {}).get("value", "")
            if not name:
                continue
            start_raw = (b.get("start") or {}).get("value", "")
            end_raw = (b.get("end") or {}).get("value", "")
            country_label = (b.get("countryLabel") or {}).get("value") or None
            out.append({
                "name": name,
                "description": (b.get("itemDescription") or {}).get("value"),
                "start_date": start_raw[:10] if start_raw else None,
                "end_date": end_raw[:10] if end_raw else None,
                "location": (b.get("locLabel") or {}).get("value") or None,
                "image_url": (b.get("img") or {}).get("value"),
                "wikidata_url": (b.get("item") or {}).get("value"),
                "country": country_label,
                "source": "wikidata",
            })
        return out

    async def _nager_public_holidays(
        self, country_code: str, country_label: str, month: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Lấy ngày nghỉ pháp định của một nước từ Nager.Date (MIT, không cần key).
        Bổ sung loại dữ liệu mà SPARQL/Wikipedia yếu: public holidays có NGÀY chính xác
        theo Dương lịch (năm hiện tại). Trả [] nếu lỗi (không ném).
        """
        year = datetime.now().year
        iso2 = (country_code or "").strip().upper()
        if len(iso2) != 2:
            return []
        cache_key = f"nager:{iso2}:{year}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            holidays = cached
        else:
            url = f"{settings.NAGER_DATE_BASE_URL}/api/v3/PublicHolidays/{year}/{iso2}"
            try:
                async with httpx.AsyncClient(
                    timeout=settings.NAGER_REQUEST_TIMEOUT,
                    headers={"User-Agent": self._user_agent()},
                ) as client:
                    resp = await client.get(url)
                    # 204 / body rỗng = Nager chưa có dữ liệu cho nước+năm này (vd TH 2026) -> không phải lỗi.
                    if resp.status_code == 204 or not resp.content:
                        holidays = []
                    else:
                        resp.raise_for_status()
                        holidays = resp.json()
                self._cache_set(cache_key, holidays)
            except Exception as e:
                logger.warning("Nager.Date failed for %s/%s: %s", iso2, year, e)
                return []

        out: List[Dict[str, Any]] = []
        for h in holidays or []:
            date = (h.get("date") or "")[:10]
            if not date:
                continue
            try:
                h_month = int(date[5:7])
            except (ValueError, IndexError):
                continue
            if month and h_month != int(month):
                continue
            types = ", ".join(h.get("types") or [])
            out.append({
                "name": h.get("localName") or h.get("name") or "Public holiday",
                "description": (f"Ngày lễ công cộng ({types})" if types else "Ngày lễ công cộng"),
                "start_date": date,
                "end_date": None,
                "location": country_label,
                "image_url": None,
                "wikidata_url": None,
                "wikipedia_url": None,
                "lunar": None,
                "region": "",
                "month": h_month,
                "country": country_label,
                "source": "nager",
            })
        return out


    async def _fetch_festivals_from_wikipedia(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Lấy lễ hội VN qua Wikipedia action API (MediaWiki) — open-source, key-free,
        hạ tầng RIÊNG với Wikidata SPARQL nên không bị outage của WDQS.
        Lấy các trang trong chuyên mục "Lễ hội Việt Nam" kèm mô tả ngắn + ảnh thumb.
        """
        params = {
            "action": "query",
            "generator": "categorymembers",
            "gcmtitle": "Category:Lễ_hội_Việt_Nam",
            "gcmtype": "page",
            "gcmlimit": str(limit),
            "prop": "extracts|pageimages|description",
            "exintro": "1",
            "explaintext": "1",
            "exsentences": "2",
            "exlimit": "max",
            "pithumbsize": "240",
            "format": "json",
            "redirects": "1",
        }
        try:
            async with httpx.AsyncClient(
                timeout=settings.WIKIDATA_REQUEST_TIMEOUT,
                headers={"User-Agent": self._user_agent()},
            ) as client:
                resp = await client.get("https://vi.wikipedia.org/w/api.php", params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.warning("Wikipedia festival API failed: %s", e)
            return []

        pages = (data.get("query") or {}).get("pages") or {}
        out: List[Dict[str, Any]] = []
        for p in pages.values():
            title = (p.get("title") or "").strip()
            if not title:
                continue
            thumb = (p.get("thumbnail") or {}).get("source")
            extract = (p.get("extract") or "").strip()
            out.append({
                "name": title,
                "description": extract or None,
                "start_date": None,
                "end_date": None,
                "location": None,
                "image_url": thumb,
                "wikidata_url": None,
                "wikipedia_url": f"https://vi.wikipedia.org/wiki/{urlquote(title)}",
                "source": "wikipedia",
            })
        return out
