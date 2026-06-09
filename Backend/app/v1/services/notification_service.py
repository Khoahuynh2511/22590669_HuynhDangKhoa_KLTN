"""
Notification Service
Handles user notifications for bookings, tours, payments
"""
import logging
from typing import Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from ..core.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing user notifications"""

    def __init__(self):
        """Initialize NotificationService"""
        self.db_url = settings.DATABASE_URL

    def _get_conn(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    def _normalize(self, rows):
        return [dict(r) for r in rows]

    def create_notification(
        self,
        user_id: str,
        type: str,
        title: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new notification for a user

        Args:
            user_id: UUID of the user
            type: Notification type ('tour_cancelled', 'booking_cancelled', etc)
            title: Notification title
            message: Notification message
            metadata: Optional metadata (package_id, booking_id, etc)

        Returns:
            Dict with EC, EM, and data
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO notifications (user_id, type, title, message, metadata, is_read)
                        VALUES (%s, %s, %s, %s, %s, FALSE)
                        RETURNING *
                        """,
                        (user_id, type, title, message, metadata or {})
                    )
                    result = cur.fetchone()
                    conn.commit()

            if not result:
                return {
                    "EC": 1,
                    "EM": "Failed to create notification",
                    "data": None
                }

            logger.info(f"Created notification for user {user_id}: {type}")

            return {
                "EC": 0,
                "EM": "Notification created successfully",
                "data": dict(result)
            }

        except Exception as e:
            logger.error(f"Error creating notification: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error creating notification: {str(e)}",
                "data": None
            }

    def get_user_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: Optional[int] = 50,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get notifications for a user

        Args:
            user_id: UUID of the user
            unread_only: If True, only return unread notifications
            limit: Maximum number of notifications to return
            offset: Number of records to skip

        Returns:
            Dict with EC, EM, data, and total
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Build query
                    conditions = ["user_id = %s"]
                    params = [user_id]

                    if unread_only:
                        conditions.append("is_read = FALSE")

                    where_clause = " AND ".join(conditions)

                    # Get total count
                    cur.execute(
                        f"SELECT COUNT(*) as total FROM notifications WHERE {where_clause}",
                        params
                    )
                    total_result = cur.fetchone()
                    total = total_result.get('total', 0) if total_result else 0

                    # Get notifications
                    sql = f"""
                        SELECT * FROM notifications
                        WHERE {where_clause}
                        ORDER BY created_at DESC
                    """
                    if limit:
                        sql += " LIMIT %s"
                        params.append(limit)
                    if offset:
                        sql += " OFFSET %s"
                        params.append(offset)

                    cur.execute(sql, params)
                    notifications = self._normalize(cur.fetchall())

            return {
                "EC": 0,
                "EM": "Success",
                "data": notifications,
                "total": total
            }

        except Exception as e:
            logger.error(f"Error getting notifications for user {user_id}: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error retrieving notifications: {str(e)}",
                "data": None,
                "total": 0
            }

    def mark_as_read(self, notification_id: str) -> Dict[str, Any]:
        """
        Mark a notification as read

        Args:
            notification_id: UUID of the notification

        Returns:
            Dict with EC and EM
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE notifications SET is_read = TRUE WHERE notification_id = %s RETURNING *",
                        (notification_id,)
                    )
                    result = cur.fetchone()
                    conn.commit()

            if not result:
                return {
                    "EC": 1,
                    "EM": "Notification not found"
                }

            return {
                "EC": 0,
                "EM": "Notification marked as read"
            }

        except Exception as e:
            logger.error(f"Error marking notification as read: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error: {str(e)}"
            }

    def mark_all_as_read(self, user_id: str) -> Dict[str, Any]:
        """
        Mark all notifications as read for a user

        Args:
            user_id: UUID of the user

        Returns:
            Dict with EC, EM, and updated count
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE notifications
                        SET is_read = TRUE
                        WHERE user_id = %s AND is_read = FALSE
                        RETURNING *
                        """,
                        (user_id,)
                    )
                    results = self._normalize(cur.fetchall())
                    conn.commit()

            updated_count = len(results)

            return {
                "EC": 0,
                "EM": f"Marked {updated_count} notifications as read",
                "updated": updated_count
            }

        except Exception as e:
            logger.error(f"Error marking all notifications as read: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error: {str(e)}",
                "updated": 0
            }

    def get_unread_count(self, user_id: str) -> Dict[str, Any]:
        """
        Get count of unread notifications for a user

        Args:
            user_id: UUID of the user

        Returns:
            Dict with EC, EM, and count
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT COUNT(*) as count FROM notifications WHERE user_id = %s AND is_read = FALSE",
                        (user_id,)
                    )
                    result = cur.fetchone()
                    count = result.get('count', 0) if result else 0

            return {
                "EC": 0,
                "EM": "Success",
                "count": count
            }

        except Exception as e:
            logger.error(f"Error getting unread count: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error: {str(e)}",
                "count": 0
            }


def get_notification_service() -> NotificationService:
    """Dependency to get NotificationService instance"""
    return NotificationService()
