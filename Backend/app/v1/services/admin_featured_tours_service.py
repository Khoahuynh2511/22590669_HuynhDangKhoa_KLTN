"""
Admin Featured Tours Service
Handles featured tour packages management
"""
import logging
from typing import List, Dict, Any
from uuid import UUID
import psycopg2
from psycopg2.extras import RealDictCursor
from ..core.config import settings

logger = logging.getLogger(__name__)


class AdminFeaturedToursService:
    """Service for managing featured tours"""

    def __init__(self):
        """Initialize AdminFeaturedToursService"""
        self.db_url = settings.DATABASE_URL

    def _get_conn(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    def _normalize(self, rows):
        return [dict(r) for r in rows]

    def get_featured_tours(self) -> List[Dict[str, Any]]:
        """
        Get all featured tours (is_featured=TRUE and is_active=TRUE)

        Returns:
            List of featured tour packages
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT * FROM tour_packages
                        WHERE is_featured = TRUE AND is_active = TRUE
                        ORDER BY created_at DESC
                        """
                    )
                    featured_tours = self._normalize(cur.fetchall())

            logger.info(f"📌 Found {len(featured_tours)} featured tours")
            return featured_tours

        except Exception as e:
            logger.error(f"Error fetching featured tours: {str(e)}")
            return []

    def update_featured_tours(self, tour_package_ids: List[UUID]) -> Dict[str, Any]:
        """
        Update featured tours: set is_featured=FALSE for all, then TRUE for specified IDs

        Args:
            tour_package_ids: List of package IDs to set as featured

        Returns:
            Dict with success status and message
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Step 1: Validate all IDs exist and are active
                    valid_ids = []
                    for pkg_id in tour_package_ids:
                        cur.execute(
                            "SELECT package_id, is_active FROM tour_packages WHERE package_id = %s",
                            (str(pkg_id),)
                        )
                        result = cur.fetchone()
                        if result:
                            if result.get('is_active'):
                                valid_ids.append(str(pkg_id))
                            else:
                                logger.warning(f"Package {pkg_id} is inactive, skipping")
                        else:
                            logger.warning(f"Package {pkg_id} not found, skipping")

                    if not valid_ids:
                        return {
                            "success": False,
                            "message": "No valid package IDs provided",
                            "updated": 0
                        }

                    # Step 2: Set is_featured=FALSE for all
                    cur.execute("UPDATE tour_packages SET is_featured = FALSE")

                    # Step 3: Set is_featured=TRUE for specified IDs
                    for pkg_id in valid_ids:
                        cur.execute(
                            "UPDATE tour_packages SET is_featured = TRUE WHERE package_id = %s",
                            (pkg_id,)
                        )

                    conn.commit()

            logger.info(f"✅ Updated {len(valid_ids)} featured tours")

            return {
                "success": True,
                "message": f"Successfully updated {len(valid_ids)} featured tours",
                "updated": len(valid_ids),
                "valid_ids": valid_ids,
                "invalid_ids": [str(pid) for pid in tour_package_ids if str(pid) not in valid_ids]
            }

        except Exception as e:
            logger.error(f"Error updating featured tours: {str(e)}")
            return {
                "success": False,
                "message": f"Error updating featured tours: {str(e)}",
                "updated": 0
            }


def get_admin_featured_tours_service() -> AdminFeaturedToursService:
    """Dependency to get AdminFeaturedToursService instance"""
    return AdminFeaturedToursService()
