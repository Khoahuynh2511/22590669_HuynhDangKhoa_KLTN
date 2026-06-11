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

logger = logging.getLogger(__name__)


def _remove_diacritics(text: str) -> str:
    """Remove Vietnamese diacritics for matching."""
    if not text:
        return ""
    normalized = unicodedata.normalize('NFD', text)
    stripped = re.sub(r'[̀-ͯˀ-˟]', '', normalized)
    stripped = stripped.replace('đ', 'd').replace('Đ', 'D')
    return stripped.strip()


class ActivityService:
    """Fetch activity packages from Render PostgreSQL."""

    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        if not self.db_url:
            logger.warning("DATABASE_URL not set")

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
                all_activities.append(activity)

            # Python-side destination matching (handles Vietnamese diacritics)
            dest_lower = destination.lower().strip()
            dest_clean = _remove_diacritics(dest_lower)

            activities = []
            for act in all_activities:
                act_dest = (act.get("destination") or "").lower()
                act_dest_clean = _remove_diacritics(act_dest)

                # Match if: original contains query, or stripped contains stripped query
                if dest_lower in act_dest or dest_clean in act_dest_clean:
                    # Apply optional filters
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
                    if act.get("price", 0) <= budget_price:
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
