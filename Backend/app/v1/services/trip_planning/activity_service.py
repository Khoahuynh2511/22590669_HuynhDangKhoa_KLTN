"""
Activity Package Service
Reads activity packages from Render PostgreSQL (DATABASE_URL).
Uses psycopg2 directly — same DB as the seed script.
"""
import logging
import os
import re
import unicodedata
from typing import List, Dict, Any, Optional

import psycopg2

from app.v1.core.config import settings

logger = logging.getLogger(__name__)

KNOWN_DESTINATIONS = [
    "Đà Lạt",
    "Hội An",
    "Nha Trang",
    "Đà Nẵng",
    "Phú Quốc",
    "Sapa",
    "Huế",
    "Vũng Tàu",
]


def _remove_diacritics(text: str) -> str:
    """Remove Vietnamese diacritics for matching."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFD", text)
    stripped = re.sub(r"[̀-ͯˀ-˟]", "", normalized)
    stripped = stripped.replace("đ", "d").replace("Đ", "D")
    return stripped.strip()


def normalize_destination(name: str) -> str:
    """Strip duration suffix and map to a canonical destination name."""
    if not name:
        return name
    text = name.strip()
    text = re.sub(r"\s+\d+\s*ngày\s*$", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"\s+\d+\s*days?\s*$", "", text, flags=re.IGNORECASE).strip()
    text_clean = _remove_diacritics(text.lower())

    for known in KNOWN_DESTINATIONS:
        known_clean = _remove_diacritics(known.lower())
        if known_clean in text_clean or text_clean in known_clean:
            return known
    return text


def _destination_matches(query: str, act_dest: str) -> bool:
    """Match user destination against DB destination (bidirectional, diacritics-safe)."""
    if not query or not act_dest:
        return False
    query_norm = normalize_destination(query)
    query_lower = query_norm.lower().strip()
    act_lower = act_dest.lower().strip()
    query_clean = _remove_diacritics(query_lower)
    act_clean = _remove_diacritics(act_lower)
    return (
        query_lower in act_lower
        or act_lower in query_lower
        or query_clean in act_clean
        or act_clean in query_clean
    )


def _to_float(value: Any, default: float = 0.0) -> float:
    """Coerce DB numeric values that may arrive as str/Decimal."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return default


def _normalize_activity_row(activity: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure numeric fields are usable in comparisons and math."""
    activity["price"] = _to_float(activity.get("price"))
    if activity.get("duration_hours") is not None:
        activity["duration_hours"] = _to_float(activity.get("duration_hours"))
    return activity


class ActivityService:
    """Fetch activity packages from Render PostgreSQL."""

    def __init__(self):
        self.db_url = self._resolve_db_url()

    @staticmethod
    def _resolve_db_url() -> str:
        url = settings.DATABASE_URL or os.getenv("DATABASE_URL", "")
        return (
            url.replace("postgresql+asyncpg://", "postgresql://")
            .replace("postgres+asyncpg://", "postgresql://")
        )

    def _get_conn(self):
        if not self.db_url:
            raise ValueError("DATABASE_URL not configured")
        return psycopg2.connect(self.db_url)

    def search_activities(
        self,
        destination: str,
        time_slot: Optional[str] = None,
        category: Optional[str] = None,
        budget_level: str = "moderate",
        preferences: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Search activity packages by destination and optional filters.
        Uses diacritics-insensitive matching via Python fallback.
        """
        if not destination:
            return []

        destination = normalize_destination(destination)

        conn = None
        try:
            conn = self._get_conn()
            conn.autocommit = True
            cur = conn.cursor()

            # Fetch all active activities (Python-side filtering for Unicode matching)
            query = """
                SELECT activity_id, name, description, destination, time_slot, category,
                       duration_hours, price, difficulty, location, image_url,
                       gallery_urls, included_services, max_participants, min_participants,
                       is_ai_generated
                FROM activity_packages
                WHERE is_active = TRUE
                ORDER BY price ASC
            """
            cur.execute(query)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

            all_activities = []
            for row in rows:
                activity = dict(zip(columns, row))
                for key, val in activity.items():
                    if val is not None and not isinstance(val, (str, int, float, bool, list, dict)):
                        activity[key] = str(val)
                all_activities.append(_normalize_activity_row(activity))

            # Python-side destination matching (handles Vietnamese diacritics)
            activities = []
            for act in all_activities:
                act_dest = act.get("destination") or ""
                if not _destination_matches(destination, act_dest):
                    continue
                if time_slot and act.get("time_slot") != time_slot:
                    continue
                if category and act.get("category") != category:
                    continue
                activities.append(act)

            # Rank by preferences
            if preferences and activities:
                pref_set = set(p.lower() for p in preferences)
                budget_prices = {"economy": 150000, "moderate": 300000, "luxury": 600000}
                budget_price = budget_prices.get(budget_level, 300000)

                for act in activities:
                    score = 0
                    if act.get("category") and act["category"].lower() in pref_set:
                        score += 2
                    if _to_float(act.get("price")) <= budget_price:
                        score += 1
                    act["_rank_score"] = score

                activities.sort(key=lambda x: x.get("_rank_score", 0), reverse=True)

            activities = activities[:limit]
            logger.info(f"Found {len(activities)} activities for '{destination}'")
            return activities

        except Exception as e:
            logger.error(f"Error searching activities: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
        finally:
            if conn:
                conn.close()

    def get_activities_by_slot(
        self,
        destination: str,
        time_slot: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Get activities for a specific time slot."""
        return self.search_activities(
            destination=destination,
            time_slot=time_slot,
            limit=limit,
        )

    def get_all_for_destination(
        self,
        destination: str,
        budget_level: str = "moderate",
        preferences: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Get all active activities for a destination, ranked by preferences."""
        return self.search_activities(
            destination=destination,
            budget_level=budget_level,
            preferences=preferences,
            limit=50,
        )


# Singleton
activity_service = ActivityService()
