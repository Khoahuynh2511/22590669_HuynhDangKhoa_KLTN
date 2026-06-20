"""
Place Collection Service
Quản lý "Bộ sưu tập" của user:
- Wishlist: các điểm đến (worldwide) user muốn đến (bảng user_place_saves).
- Visited: reuse visited_provinces (không trùng lặp storage) qua get_combined_collection.
Pattern theo visited_province_service.py (psycopg2 trực tiếp + async wrapper + EC/EM).
"""
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set

import psycopg2
from psycopg2.extras import RealDictCursor

from ..core.config import settings

logger = logging.getLogger(__name__)


class PlaceCollectionService:
    """Service quản lý wishlist địa điểm của user."""

    def __init__(self, supabase_client: Any | None = None):
        self.supabase = supabase_client

    def _pg_conn(self):
        return psycopg2.connect(settings.DATABASE_URL, cursor_factory=RealDictCursor)

    # ---------- serialization helpers (giống VisitedProvinceService) ----------
    @staticmethod
    def _serialize_value(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        if hasattr(value, "hex"):  # UUID
            return str(value)
        return value

    @classmethod
    def _serialize_row(cls, row: Dict[str, Any]) -> Dict[str, Any]:
        return {key: cls._serialize_value(value) for key, value in dict(row).items()}

    @classmethod
    def _serialize_rows(cls, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [cls._serialize_row(row) for row in rows]

    # ----------------------------- read ---------------------------------
    async def list_user_saves(self, user_id: str) -> Dict[str, Any]:
        """Danh sách place đã lưu (wishlist) của user."""
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT save_id, user_id, place_name, place_display_name,
                               latitude, longitude, category, image_url, description,
                               wikipedia_url, osm_id, source, created_at
                        FROM user_place_saves
                        WHERE user_id = %s
                        ORDER BY created_at DESC
                        """,
                        (user_id,),
                    )
                    saves = self._serialize_rows(cur.fetchall())

            return {
                "EC": 0,
                "EM": "Successfully retrieved saved places",
                "total": len(saves),
                "saves": saves,
            }
        except Exception as e:
            logger.error("Error listing user saves: %s", e)
            return {"EC": 1, "EM": f"Error retrieving saved places: {e}", "total": 0, "saves": []}

    async def get_saved_osm_ids(self, user_id: str) -> Set[int]:
        """Trả về tập hợp các osm_id user đã lưu (dùng để annotate suggest)."""
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT osm_id FROM user_place_saves WHERE user_id = %s",
                        (user_id,),
                    )
                    rows = cur.fetchall()
            return {int(r["osm_id"]) for r in rows if r.get("osm_id") is not None}
        except Exception as e:
            logger.error("Error getting saved osm ids: %s", e)
            return set()

    async def get_combined_collection(self, user_id: str) -> Dict[str, Any]:
        """
        Gộp wishlist (user_place_saves) + nơi đã đến (visited_provinces JOIN provinces).
        Không trùng lặp storage: visited vẫn chỉ nằm ở bảng visited_provinces.
        """
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT save_id, user_id, place_name, place_display_name,
                               latitude, longitude, category, image_url, description,
                               wikipedia_url, osm_id, source, created_at
                        FROM user_place_saves
                        WHERE user_id = %s
                        ORDER BY created_at DESC
                        """,
                        (user_id,),
                    )
                    wishlist = self._serialize_rows(cur.fetchall())

                    cur.execute(
                        """
                        SELECT vp.visit_id, vp.user_id, vp.province_id, vp.visited_at, vp.visit_source,
                               p.province_code, p.province_name, p.province_name_en,
                               p.region, p.latitude, p.longitude
                        FROM visited_provinces vp
                        JOIN provinces p ON p.province_id = vp.province_id
                        WHERE vp.user_id = %s
                        ORDER BY vp.visited_at DESC
                        """,
                        (user_id,),
                    )
                    visited = self._serialize_rows(cur.fetchall())

            return {
                "EC": 0,
                "EM": "Successfully retrieved collection",
                "total_wishlist": len(wishlist),
                "total_visited": len(visited),
                "wishlist": wishlist,
                "visited_provinces": visited,
            }
        except Exception as e:
            logger.error("Error getting combined collection: %s", e)
            return {
                "EC": 1,
                "EM": f"Error retrieving collection: {e}",
                "total_wishlist": 0,
                "total_visited": 0,
                "wishlist": [],
                "visited_provinces": [],
            }

    # ----------------------------- write --------------------------------
    async def add_save(self, user_id: str, place: Dict[str, Any]) -> Dict[str, Any]:
        """
        Lưu 1 place vào wishlist. Idempotent (đã tồn tại thì update timestamp).
        `place` chứa các trường từ SavePlaceRequest.
        """
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO user_place_saves
                            (user_id, place_name, place_display_name, latitude, longitude,
                             category, image_url, description, wikipedia_url, osm_id, source)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'manual')
                        ON CONFLICT (user_id, osm_id) DO UPDATE
                            SET place_display_name = EXCLUDED.place_display_name,
                                image_url = COALESCE(EXCLUDED.image_url, user_place_saves.image_url),
                                description = COALESCE(EXCLUDED.description, user_place_saves.description),
                                created_at = NOW()
                        RETURNING save_id
                        """,
                        (
                            user_id,
                            place.get("place_name"),
                            place.get("place_display_name") or place.get("place_name"),
                            place.get("latitude"),
                            place.get("longitude"),
                            place.get("category") or "attraction",
                            place.get("image_url"),
                            place.get("description"),
                            place.get("wikipedia_url"),
                            place.get("osm_id"),
                        ),
                    )
                    cur.fetchone()
                    conn.commit()

            return {"EC": 0, "EM": "Place saved", "is_saved": True}
        except Exception as e:
            logger.error("Error adding place save: %s", e)
            return {"EC": 1, "EM": f"Error saving place: {e}", "is_saved": False}

    async def remove_save(self, user_id: str, save_id: str) -> Dict[str, Any]:
        """Bỏ lưu 1 place khỏi wishlist."""
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        DELETE FROM user_place_saves
                        WHERE user_id = %s AND save_id = %s
                        RETURNING save_id
                        """,
                        (user_id, save_id),
                    )
                    row = cur.fetchone()
                    conn.commit()
                    if not row:
                        return {"EC": 1, "EM": "Save not found", "is_saved": True}
            return {"EC": 0, "EM": "Place removed", "is_saved": False}
        except Exception as e:
            logger.error("Error removing place save: %s", e)
            return {"EC": 1, "EM": f"Error removing place: {e}", "is_saved": True}

    async def check_saved(self, user_id: str, osm_id: int) -> Dict[str, Any]:
        """Kiểm tra user đã lưu 1 OSM entity chưa."""
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT EXISTS(
                            SELECT 1 FROM user_place_saves
                            WHERE user_id = %s AND osm_id = %s
                        ) AS saved
                        """,
                        (user_id, osm_id),
                    )
                    row = cur.fetchone()
            is_saved = bool(row.get("saved")) if row else False
            return {"EC": 0, "EM": "Check successful", "is_saved": is_saved}
        except Exception as e:
            logger.error("Error checking saved status: %s", e)
            return {"EC": 1, "EM": f"Error checking saved status: {e}", "is_saved": False}
