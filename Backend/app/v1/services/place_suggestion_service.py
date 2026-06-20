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
import time
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote as urlquote

import httpx

from ..core.config import settings

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
