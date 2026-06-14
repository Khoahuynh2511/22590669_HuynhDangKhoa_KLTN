"""
Admin Activity Service - CRUD operations for activity packages
"""
from typing import Dict, Any, Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
from datetime import datetime, timezone
from ..core.config import settings


class AdminActivityService:
    def __init__(self):
        self.db_url = self._resolve_db_url()

    @staticmethod
    def _resolve_db_url() -> str:
        url = settings.DATABASE_URL
        return (
            url.replace("postgresql+asyncpg://", "postgresql://")
            .replace("postgres+asyncpg://", "postgresql://")
        )

    def _get_conn(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    def _normalize(self, rows):
        return [dict(r) for r in rows]

    def get_all_activities(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        destination: Optional[str] = None,
        category: Optional[str] = None,
        searchTerm: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get all activities including inactive ones for admin view"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM activity_packages WHERE 1=1"
                params = []
                conditions = []

                if destination:
                    conditions.append("destination ILIKE %s")
                    params.append(f"%{destination}%")
                if category:
                    conditions.append("category = %s")
                    params.append(category)
                if searchTerm:
                    conditions.append("(name ILIKE %s OR description ILIKE %s OR location ILIKE %s)")
                    params.extend([f"%{searchTerm}%", f"%{searchTerm}%", f"%{searchTerm}%"])

                if conditions:
                    query += " AND " + " AND ".join(conditions)

                query += " ORDER BY created_at DESC"

                if limit is not None:
                    query += " LIMIT %s"
                    params.append(limit)
                if offset is not None:
                    query += " OFFSET %s"
                    params.append(offset)

                cursor.execute(query, params)
                rows = cursor.fetchall()
                activities = self._normalize(rows)

                # Convert UUID and other objects to string
                for act in activities:
                    for key, val in act.items():
                        if isinstance(val, uuid.UUID):
                            act[key] = str(val)
                        elif isinstance(val, (datetime,)):
                            act[key] = val.isoformat()
                        elif isinstance(val, (list,)):
                            act[key] = list(val)
                        elif val is not None and not isinstance(val, (str, int, float, bool, dict)):
                            act[key] = str(val)
                    if act.get("price") is not None:
                        act["price"] = float(act["price"])
                    if act.get("duration_hours") is not None:
                        act["duration_hours"] = float(act["duration_hours"])

                # Get total count
                count_query = "SELECT COUNT(*) as total FROM activity_packages WHERE 1=1"
                count_params = []
                if conditions:
                    count_query += " AND " + " AND ".join(conditions)
                    count_params = params[:len(conditions) if limit is None else -1] # Adjust parameters for count
                    # Wait, let's just re-compile count params to be clean
                    count_params = []
                    if destination:
                        count_params.append(f"%{destination}%")
                    if category:
                        count_params.append(category)
                    if searchTerm:
                        count_params.extend([f"%{searchTerm}%", f"%{searchTerm}%", f"%{searchTerm}%"])

                cursor.execute(count_query, count_params)
                total = cursor.fetchone()['total']

                return {
                    "EC": 0,
                    "EM": "Success",
                    "data": {
                        "activities": activities,
                        "total": total
                    }
                }
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi server: {str(e)}", "data": None}

    def get_activity_by_id(self, activity_id: str) -> Dict[str, Any]:
        """Get detail of one activity package"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM activity_packages WHERE activity_id = %s", (activity_id,))
                rows = cursor.fetchall()
                activities = self._normalize(rows)

                if not activities:
                    return {"EC": 1, "EM": "Không tìm thấy hoạt động", "data": None}

                act = activities[0]
                for key, val in act.items():
                    if isinstance(val, uuid.UUID):
                        act[key] = str(val)
                    elif isinstance(val, (datetime,)):
                        act[key] = val.isoformat()
                    elif isinstance(val, (list,)):
                        act[key] = list(val)
                    elif val is not None and not isinstance(val, (str, int, float, bool, dict)):
                        act[key] = str(val)
                if act.get("price") is not None:
                    act["price"] = float(act["price"])
                if act.get("duration_hours") is not None:
                    act["duration_hours"] = float(act["duration_hours"])

                return {"EC": 0, "EM": "Success", "data": act}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi server: {str(e)}", "data": None}

    def create_activity(self, activity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new activity package"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                # Set default fields if missing
                if "is_ai_generated" not in activity_data:
                    activity_data["is_ai_generated"] = False
                if "is_active" not in activity_data:
                    activity_data["is_active"] = True

                now = datetime.now(timezone.utc)
                activity_data["created_at"] = now
                activity_data["updated_at"] = now

                columns = list(activity_data.keys())
                placeholders = ", ".join(["%s"] * len(columns))
                column_names = ", ".join(columns)
                values = list(activity_data.values())

                # Convert lists to PostgreSQL text array inputs if they are python lists
                for idx, val in enumerate(values):
                    if isinstance(val, list):
                        values[idx] = val # psycopg2 maps python list to postgres array automatically

                query = f"INSERT INTO activity_packages ({column_names}) VALUES ({placeholders}) RETURNING *"
                cursor.execute(query, values)
                conn.commit()

                inserted = dict(cursor.fetchone())
                for key, val in inserted.items():
                    if isinstance(val, uuid.UUID):
                        inserted[key] = str(val)
                    elif isinstance(val, (datetime,)):
                        inserted[key] = val.isoformat()
                    elif isinstance(val, (list,)):
                        inserted[key] = list(val)
                if inserted.get("price") is not None:
                    inserted["price"] = float(inserted["price"])
                if inserted.get("duration_hours") is not None:
                    inserted["duration_hours"] = float(inserted["duration_hours"])

                return {"EC": 0, "EM": "Tạo hoạt động thành công", "data": inserted}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi tạo hoạt động: {str(e)}", "data": None}

    def update_activity(self, activity_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an activity package"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                # Check exists
                cursor.execute("SELECT activity_id FROM activity_packages WHERE activity_id = %s", (activity_id,))
                if not cursor.fetchone():
                    return {"EC": 1, "EM": "Không tìm thấy hoạt động", "data": None}

                update_data["updated_at"] = datetime.now(timezone.utc)

                set_clause = []
                values = []
                for key, val in update_data.items():
                    set_clause.append(f"{key} = %s")
                    values.append(val)

                values.append(activity_id)
                clause_str = ", ".join(set_clause)

                query = f"UPDATE activity_packages SET {clause_str} WHERE activity_id = %s RETURNING *"
                cursor.execute(query, values)
                conn.commit()

                updated = dict(cursor.fetchone())
                for key, val in updated.items():
                    if isinstance(val, uuid.UUID):
                        updated[key] = str(val)
                    elif isinstance(val, (datetime,)):
                        updated[key] = val.isoformat()
                    elif isinstance(val, (list,)):
                        updated[key] = list(val)
                if updated.get("price") is not None:
                    updated["price"] = float(updated["price"])
                if updated.get("duration_hours") is not None:
                    updated["duration_hours"] = float(updated["duration_hours"])

                return {"EC": 0, "EM": "Cập nhật hoạt động thành công", "data": updated}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi cập nhật: {str(e)}", "data": None}

    def delete_activity(self, activity_id: str) -> Dict[str, Any]:
        """Soft delete activity package by setting is_active = false"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                # Check exists
                cursor.execute("SELECT activity_id FROM activity_packages WHERE activity_id = %s", (activity_id,))
                if not cursor.fetchone():
                    return {"EC": 1, "EM": "Không tìm thấy hoạt động", "data": None}

                cursor.execute(
                    "UPDATE activity_packages SET is_active = false, updated_at = %s WHERE activity_id = %s",
                    (datetime.now(timezone.utc), activity_id)
                )
                conn.commit()

                return {"EC": 0, "EM": "Xóa hoạt động thành công", "data": None}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi xóa hoạt động: {str(e)}", "data": None}


def get_admin_activity_service() -> AdminActivityService:
    return AdminActivityService()
