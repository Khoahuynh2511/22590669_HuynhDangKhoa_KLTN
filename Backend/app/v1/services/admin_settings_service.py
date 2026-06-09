"""
Admin Settings Service
Handles admin configuration settings stored in database
"""
import logging
from typing import Any, Optional
from datetime import datetime, timezone
import psycopg2
from psycopg2.extras import RealDictCursor
from ..core.config import settings

logger = logging.getLogger(__name__)


class AdminSettingsService:
    """Service for managing admin settings"""

    def __init__(self):
        """Initialize AdminSettingsService"""
        self.db_url = settings.DATABASE_URL

    def _get_conn(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    def get_admin_setting(self, setting_key: str, default_value: Any = None) -> Any:
        """
        Get admin setting from database

        Args:
            setting_key: Setting key (e.g., 'ADMIN_RECOMMENDATION_ENABLED')
            default_value: Default value if setting not found

        Returns:
            Setting value (parsed from JSONB) or default_value
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT setting_value FROM admin_settings WHERE setting_key = %s",
                        (setting_key,)
                    )
                    result = cur.fetchone()

            if result:
                value = result.get('setting_value')
                # Parse JSONB value
                if isinstance(value, bool):
                    return value
                elif isinstance(value, str):
                    # Handle string booleans
                    if value.lower() in ('true', 'false'):
                        return value.lower() == 'true'
                    return value
                elif isinstance(value, (int, float)):
                    return value
                else:
                    return value
            else:
                logger.info(f"Setting {setting_key} not found, using default: {default_value}")
                return default_value

        except Exception as e:
            logger.error(f"Error getting admin setting {setting_key}: {str(e)}")
            return default_value

    def set_admin_setting(self, setting_key: str, setting_value: Any, updated_by: Optional[str] = None) -> bool:
        """
        Set admin setting in database

        Args:
            setting_key: Setting key (e.g., 'ADMIN_RECOMMENDATION_ENABLED')
            setting_value: Setting value (will be stored as JSONB)
            updated_by: Optional user ID who made the update

        Returns:
            True if successful, False otherwise
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Check if setting exists
                    cur.execute(
                        "SELECT setting_key FROM admin_settings WHERE setting_key = %s",
                        (setting_key,)
                    )
                    exists = cur.fetchone()

                    now = datetime.now(timezone.utc).isoformat()

                    if exists:
                        # Update existing setting
                        if updated_by:
                            cur.execute(
                                """
                                UPDATE admin_settings
                                SET setting_value = %s, updated_at = %s, updated_by = %s, admin_id = %s
                                WHERE setting_key = %s
                                """,
                                (setting_value, now, updated_by, updated_by, setting_key)
                            )
                        else:
                            cur.execute(
                                """
                                UPDATE admin_settings
                                SET setting_value = %s, updated_at = %s
                                WHERE setting_key = %s
                                """,
                                (setting_value, now, setting_key)
                            )
                    else:
                        # Insert new setting
                        if updated_by:
                            cur.execute(
                                """
                                INSERT INTO admin_settings (setting_key, setting_value, updated_at, updated_by, admin_id)
                                VALUES (%s, %s, %s, %s, %s)
                                """,
                                (setting_key, setting_value, now, updated_by, updated_by)
                            )
                        else:
                            cur.execute(
                                """
                                INSERT INTO admin_settings (setting_key, setting_value, updated_at)
                                VALUES (%s, %s, %s)
                                """,
                                (setting_key, setting_value, now)
                            )

                    conn.commit()

            logger.info(f"✅ Updated admin setting {setting_key} = {setting_value}")
            return True

        except Exception as e:
            logger.error(f"Error setting admin setting {setting_key}: {str(e)}")
            return False


def get_admin_settings_service() -> AdminSettingsService:
    """Dependency to get AdminSettingsService instance"""
    return AdminSettingsService()
