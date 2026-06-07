"""
Favorite Tour Service
Handles favorite tour operations (like/heart feature).
"""
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List

import psycopg2
from psycopg2.extras import RealDictCursor

from ..core.config import settings

logger = logging.getLogger(__name__)


class FavoriteTourService:
    """Service for managing favorite tours."""

    def __init__(self, supabase_client: Any | None = None):
        """
        Initialize FavoriteTourService.

        The supabase_client argument is kept for dependency compatibility with
        older endpoint/service constructors. Favorites use PostgreSQL directly.
        """
        self.supabase = supabase_client

    def _pg_conn(self):
        return psycopg2.connect(settings.DATABASE_URL, cursor_factory=RealDictCursor)

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        if hasattr(value, "hex"):
            return str(value)
        return value

    @classmethod
    def _serialize_row(cls, row: Dict[str, Any]) -> Dict[str, Any]:
        return {key: cls._serialize_value(value) for key, value in dict(row).items()}

    @classmethod
    def _serialize_rows(cls, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [cls._serialize_row(row) for row in rows]

    async def add_favorite(self, user_id: str, package_id: str) -> Dict[str, Any]:
        """
        Add a tour package to user's favorites.

        Returns:
            Dict with EC, EM, and is_favorite status.
        """
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO favorite_tours (user_id, package_id, created_at)
                        VALUES (%s, %s, NOW())
                        ON CONFLICT (user_id, package_id) DO NOTHING
                        RETURNING favorite_id
                        """,
                        (user_id, package_id),
                    )
                    row = cur.fetchone()
                    conn.commit()

            if not row:
                return {
                    "EC": 1,
                    "EM": "Tour is already in favorites",
                    "is_favorite": True,
                }

            logger.info("Added favorite: user=%s, package=%s", user_id, package_id)
            return {
                "EC": 0,
                "EM": "Tour added to favorites",
                "is_favorite": True,
            }

        except Exception as e:
            logger.error("Error adding favorite: %s", e)
            return {
                "EC": 3,
                "EM": f"Error adding favorite: {e}",
                "is_favorite": False,
            }

    async def remove_favorite(self, user_id: str, package_id: str) -> Dict[str, Any]:
        """
        Remove a tour package from user's favorites.

        Returns:
            Dict with EC, EM, and is_favorite status.
        """
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        DELETE FROM favorite_tours
                        WHERE user_id = %s AND package_id = %s
                        RETURNING favorite_id
                        """,
                        (user_id, package_id),
                    )
                    row = cur.fetchone()
                    conn.commit()

            if not row:
                return {
                    "EC": 0,
                    "EM": "Tour is not in favorites",
                    "is_favorite": False,
                }

            logger.info("Removed favorite: user=%s, package=%s", user_id, package_id)
            return {
                "EC": 0,
                "EM": "Tour removed from favorites",
                "is_favorite": False,
            }

        except Exception as e:
            logger.error("Error removing favorite: %s", e)
            return {
                "EC": 1,
                "EM": f"Error removing favorite: {e}",
                "is_favorite": False,
            }

    async def is_favorite(self, user_id: str, package_id: str) -> Dict[str, Any]:
        """
        Check if a tour package is favorited by the user.

        Returns:
            Dict with EC, EM, and is_favorite status.
        """
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT 1
                        FROM favorite_tours
                        WHERE user_id = %s AND package_id = %s
                        LIMIT 1
                        """,
                        (user_id, package_id),
                    )
                    row = cur.fetchone()

            return {
                "EC": 0,
                "EM": "Success",
                "is_favorite": row is not None,
            }

        except Exception as e:
            logger.error("Error checking favorite status: %s", e)
            return {
                "EC": 1,
                "EM": f"Error checking favorite status: {e}",
                "is_favorite": False,
            }

    async def get_user_favorites(self, user_id: str) -> Dict[str, Any]:
        """
        Get all favorite tours for a user with full tour package details.

        Returns:
            Dict with EC, EM, total, and packages list.
        """
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT
                            tp.*,
                            ft.created_at AS favorited_at
                        FROM favorite_tours ft
                        JOIN tour_packages tp ON tp.package_id = ft.package_id
                        WHERE ft.user_id = %s
                        ORDER BY ft.created_at DESC
                        """,
                        (user_id,),
                    )
                    packages = self._serialize_rows(cur.fetchall())

            if not packages:
                return {
                    "EC": 0,
                    "EM": "No favorite tours found",
                    "total": 0,
                    "packages": [],
                }

            logger.info(
                "Retrieved %s favorite tours for user %s",
                len(packages),
                user_id,
            )
            return {
                "EC": 0,
                "EM": "Successfully retrieved favorite tours",
                "total": len(packages),
                "packages": packages,
            }

        except Exception as e:
            logger.error("Error getting user favorites: %s", e)
            return {
                "EC": 1,
                "EM": f"Error retrieving favorite tours: {e}",
                "total": 0,
                "packages": [],
            }
