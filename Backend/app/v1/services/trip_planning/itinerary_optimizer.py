"""
Itinerary AI Optimizer
Tối ưu lịch trình đã build: gap-fill slot trống + chấm điểm theo thời tiết (Open-Meteo,
key-free) + cân bằng category + khớp preference. Giữ nguyên activity user đã đặt, chỉ
fill chỗ trống và đề xuất. Trả kèm danh sách giải thích (explanation).

Không phụ thuộc MCP (gọi Open-Meteo trực tiếp) để tránh phụ thuộc runtime.
"""
from __future__ import annotations
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
import psycopg2
from psycopg2.extras import RealDictCursor

from app.v1.core.config import settings

logger = logging.getLogger(__name__)

SLOTS = ["morning", "afternoon", "evening"]
# Category "ngoài trời" bị ảnh hưởng bởi thời tiết xấu.
OUTDOOR_CATEGORIES = {"nature", "adventure", "spiritual"}
# WMO weather code báo mưa.
RAIN_CODES = set(list(range(51, 68)) + list(range(80, 83)) + list(range(95, 100)))

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
UA = "KLTN-TourBooking/1.0 (educational)"


class ItineraryOptimizer:
    """Rule-based AI optimizer (weather + slot-fit + category balance + preference)."""

    def __init__(self):
        self.db_url = settings.DATABASE_URL

    # --------------------------- DB: activity pool ---------------------------
    def _fetch_activities(self, destination: str) -> List[Dict[str, Any]]:
        try:
            with psycopg2.connect(self.db_url, cursor_factory=RealDictCursor) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT activity_id, name, category, time_slot, duration_hours,
                                  price, difficulty, location, destination, image_url
                           FROM activity_packages
                           WHERE is_active = TRUE AND destination ILIKE %s""",
                        (f"%{destination}%",),
                    )
                    return [dict(r) for r in cur.fetchall()]
        except Exception as e:
            logger.error(f"ItineraryOptimizer fetch activities error: {e}")
            return []

    # --------------------------- Weather (Open-Meteo) ------------------------
    async def _fetch_rain_flags(self, destination: str, n_days: int) -> List[bool]:
        """Trả list n_days phần tử: True nếu ngày đó có mưa."""
        try:
            async with httpx.AsyncClient(timeout=15, headers={"User-Agent": UA}) as client:
                geo = await client.get(GEOCODE_URL, params={
                    "name": destination, "count": 1, "language": "vi", "format": "json"})
                results = (geo.json() or {}).get("results") or []
                if not results:
                    return []
                lat, lon = results[0]["latitude"], results[0]["longitude"]

                days = max(1, min(n_days, 7))
                fc = await client.get(FORECAST_URL, params={
                    "latitude": lat, "longitude": lon,
                    "daily": "weather_code,precipitation_probability_max",
                    "timezone": "auto", "forecast_days": days})
                daily = (fc.json() or {}).get("daily") or {}
                codes = daily.get("weather_code") or []
                prob = daily.get("precipitation_probability_max") or []
                flags = []
                for i in range(days):
                    code = codes[i] if i < len(codes) else 0
                    p = prob[i] if i < len(prob) else 0
                    flags.append((code in RAIN_CODES) or (p >= 60))
                return flags
        except Exception as e:
            logger.warning(f"ItineraryOptimizer weather fetch failed (skip weather scoring): {e}")
            return []

    # --------------------------- Helpers -------------------------------------
    @staticmethod
    def _slot_list(slot_val: Any) -> List[Dict[str, Any]]:
        """Chuẩn hóa 1 slot (có thể là None/dict/list) -> list activity dict."""
        if not slot_val:
            return []
        if isinstance(slot_val, list):
            out = []
            for item in slot_val:
                if isinstance(item, dict) and "activity" in item and isinstance(item["activity"], dict):
                    out.append(item["activity"])  # PlacedActivity frontend
                elif isinstance(item, dict):
                    out.append(item)
            return out
        if isinstance(slot_val, dict):
            if "activity" in slot_val and isinstance(slot_val["activity"], dict):
                return [slot_val["activity"]]
            if slot_val.get("activity_id") or slot_val.get("name"):
                return [slot_val]
        return []

    def _score(self, act: Dict[str, Any], slot: str, used_cats: set,
               rain: bool, pref_cats: set) -> int:
        score = 0
        ts = (act.get("time_slot") or "").lower()
        # Slot fit
        if ts == slot or ts == "full_day":
            score += 5
        elif ts and ts in SLOTS:
            score -= 3
        # Weather
        cat = (act.get("category") or "").lower()
        if cat in OUTDOOR_CATEGORIES:
            score += (-5 if rain else 2)
        else:  # indoor
            score += (2 if rain else 0)
        # Preference
        if pref_cats and cat in pref_cats:
            score += 3
        # Variety
        if cat and cat in used_cats:
            score -= 2
        return score

    # --------------------------- Main ----------------------------------------
    async def optimize(
        self,
        itinerary: Dict[str, Any],
        destination: str,
        duration_days: int = 1,
        travel_date: Optional[str] = None,
        preferences: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        prefs = preferences or []
        pref_cats = {p.lower() for p in prefs if p}
        pool = self._fetch_activities(destination)

        days = sorted(itinerary.keys(), key=lambda k: (len(k), k))
        if not days:
            days = [f"day_{i+1}" for i in range(max(1, duration_days))]

        rain_flags = await self._fetch_rain_flags(destination, len(days))

        optimized: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        explanations: List[str] = []
        weather_summary: List[Dict[str, Any]] = []

        for idx, day_key in enumerate(days):
            day = itinerary.get(day_key) or {}
            new_day: Dict[str, List[Dict[str, Any]]] = {}
            used_ids: set = set()
            used_cats: set = set()

            # Giữ activity user đã đặt
            for slot in SLOTS:
                acts = self._slot_list(day.get(slot))
                new_day[slot] = []
                for a in acts:
                    aid = a.get("activity_id")
                    if aid:
                        used_ids.add(aid)
                    cat = (a.get("category") or "").lower()
                    if cat:
                        used_cats.add(cat)
                    new_day[slot].append(a)

            rain = bool(rain_flags[idx]) if idx < len(rain_flags) else False
            weather_summary.append({"day": day_key, "rain": rain})

            # Gap-fill các slot trống
            for slot in SLOTS:
                if new_day[slot]:
                    continue
                candidates = [a for a in pool if a.get("activity_id") not in used_ids]
                if not candidates:
                    continue
                best = max(
                    candidates,
                    key=lambda a: self._score(a, slot, used_cats, rain, pref_cats),
                )
                new_day[slot].append(best)
                used_ids.add(best.get("activity_id"))
                bcat = (best.get("category") or "").lower()
                if bcat:
                    used_cats.add(bcat)
                reason = []
                if rain and bcat not in OUTDOOR_CATEGORIES:
                    reason.append("trong nhà, hợp khi trời mưa")
                elif rain and bcat in OUTDOOR_CATEGORIES:
                    reason.append("ngoài trời (nên dời nếu mưa nặng)")
                if pref_cats and bcat in pref_cats:
                    reason.append("khớp sở thích")
                if not reason:
                    reason.append("điểm phù hợp cao nhất")
                explanations.append(
                    f"Ngày {idx+1} · {slot}: thêm «{best.get('name')}» — {', '.join(reason)}"
                )

            optimized[day_key] = new_day

        return {
            "EC": 0,
            "EM": "Đã tối ưu lịch trình" + (" (có điều chỉnh theo thời tiết)" if weather_summary else ""),
            "data": {
                "itinerary": optimized,
                "explanation": explanations,
                "weather": weather_summary,
            },
        }
