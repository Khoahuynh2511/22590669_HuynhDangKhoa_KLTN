"""
Admin Bus Service - CRUD cho quản lý chuyến xe khách
"""
from typing import Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
from ..core.config import settings


class AdminBusService:
    def __init__(self):
        self.db_url = settings.DATABASE_URL

    def _get_conn(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    def _normalize(self, rows):
        return [dict(r) for r in rows]

    def get_all_buses(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        status: Optional[str] = None,
        company_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Lấy danh sách chuyến xe"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                # Build base query
                query = "SELECT * FROM buses"
                params = []
                conditions = []

                # Add filters
                if status:
                    conditions.append("status = %s")
                    params.append(status)
                if company_id:
                    conditions.append("company_id = %s")
                    params.append(company_id)

                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

                # Add ordering
                query += " ORDER BY created_at DESC"

                # Add limit and offset
                if limit:
                    query += " LIMIT %s"
                    params.append(limit)
                if offset:
                    query += " OFFSET %s"
                    params.append(offset)

                cursor.execute(query, params)
                buses = self._normalize(cursor.fetchall())

                # Get total count
                count_query = "SELECT COUNT(*) as total FROM buses"
                count_params = []
                count_conditions = []

                if status:
                    count_conditions.append("status = %s")
                    count_params.append(status)
                if company_id:
                    count_conditions.append("company_id = %s")
                    count_params.append(company_id)

                if count_conditions:
                    count_query += " WHERE " + " AND ".join(count_conditions)

                cursor.execute(count_query, count_params)
                total = cursor.fetchone()['total']

                return {
                    "EC": 0,
                    "EM": "Success",
                    "data": {
                        "buses": buses,
                        "total": total
                    }
                }
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi server: {str(e)}", "data": None}

    def get_bus_by_id(self, bus_id: str) -> Dict[str, Any]:
        """Lấy chi tiết 1 chuyến xe"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM buses WHERE bus_id = %s", (bus_id,))
                buses = self._normalize(cursor.fetchall())

                if not buses:
                    return {"EC": 1, "EM": "Không tìm thấy chuyến xe", "data": None}

                # Convert UUID fields to string
                bus = buses[0]
                for key, value in bus.items():
                    if isinstance(value, uuid.UUID):
                        bus[key] = str(value)

                return {"EC": 0, "EM": "Success", "data": bus}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi server: {str(e)}", "data": None}

    def create_bus(self, bus_data: Dict[str, Any]) -> Dict[str, Any]:
        """Tạo chuyến xe mới"""
        try:
            # Generate bus_id if not provided
            if "bus_id" not in bus_data:
                bus_data["bus_id"] = f"BS-{uuid.uuid4().hex[:8].upper()}"

            with self._get_conn() as conn:
                cursor = conn.cursor()

                # Build INSERT query
                columns = bus_data.keys()
                placeholders = ", ".join(["%s"] * len(columns))
                column_names = ", ".join(columns)
                values = list(bus_data.values())

                query = f"INSERT INTO buses ({column_names}) VALUES ({placeholders}) RETURNING *"
                cursor.execute(query, values)
                conn.commit()

                bus = dict(cursor.fetchone())

                # Convert UUID fields to string
                for key, value in bus.items():
                    if isinstance(value, uuid.UUID):
                        bus[key] = str(value)

                return {"EC": 0, "EM": "Tạo chuyến xe thành công", "data": bus}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi tạo chuyến xe: {str(e)}", "data": None}

    def update_bus(self, bus_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cập nhật chuyến xe"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                # Check exists
                cursor.execute("SELECT bus_id FROM buses WHERE bus_id = %s", (bus_id,))
                if not cursor.fetchone():
                    return {"EC": 1, "EM": "Không tìm thấy chuyến xe", "data": None}

                # Build UPDATE query
                set_clause = ", ".join([f"{key} = %s" for key in update_data.keys()])
                values = list(update_data.values())
                values.append(bus_id)

                query = f"UPDATE buses SET {set_clause} WHERE bus_id = %s RETURNING *"
                cursor.execute(query, values)
                conn.commit()

                bus = dict(cursor.fetchone())

                # Convert UUID fields to string
                for key, value in bus.items():
                    if isinstance(value, uuid.UUID):
                        bus[key] = str(value)

                return {"EC": 0, "EM": "Cập nhật thành công", "data": bus}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi cập nhật: {str(e)}", "data": None}

    def delete_bus(self, bus_id: str) -> Dict[str, Any]:
        """Xóa chuyến xe (soft delete)"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                # Check exists
                cursor.execute("SELECT bus_id FROM buses WHERE bus_id = %s", (bus_id,))
                if not cursor.fetchone():
                    return {"EC": 1, "EM": "Không tìm thấy chuyến xe", "data": None}

                cursor.execute("UPDATE buses SET is_active = false WHERE bus_id = %s", (bus_id,))
                conn.commit()

                return {"EC": 0, "EM": "Xóa chuyến xe thành công", "data": None}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi xóa: {str(e)}", "data": None}

    def update_bus_status(self, bus_id: str, status: str) -> Dict[str, Any]:
        """Cập nhật trạng thái chuyến xe"""
        valid_statuses = ["scheduled", "boarding", "departed", "arrived", "cancelled"]
        if status not in valid_statuses:
            return {"EC": 1, "EM": f"Trạng thái không hợp lệ. Hợp lệ: {', '.join(valid_statuses)}", "data": None}

        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                # Check exists
                cursor.execute("SELECT bus_id FROM buses WHERE bus_id = %s", (bus_id,))
                if not cursor.fetchone():
                    return {"EC": 1, "EM": "Không tìm thấy chuyến xe", "data": None}

                cursor.execute(
                    "UPDATE buses SET status = %s WHERE bus_id = %s RETURNING *",
                    (status, bus_id)
                )
                conn.commit()

                bus = dict(cursor.fetchone())

                # Convert UUID fields to string
                for key, value in bus.items():
                    if isinstance(value, uuid.UUID):
                        bus[key] = str(value)

                return {"EC": 0, "EM": "Cập nhật trạng thái thành công", "data": bus}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi cập nhật: {str(e)}", "data": None}

    def get_bus_companies(self) -> Dict[str, Any]:
        """Lấy danh sách hãng xe"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM bus_companies WHERE is_active = true")
                companies = self._normalize(cursor.fetchall())

                # Convert UUID fields to string
                for company in companies:
                    for key, value in company.items():
                        if isinstance(value, uuid.UUID):
                            company[key] = str(value)

                return {"EC": 0, "EM": "Success", "data": companies}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi server: {str(e)}", "data": None}

    def get_bus_stations(self) -> Dict[str, Any]:
        """Lấy danh sách bến xe"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM bus_stations WHERE is_active = true")
                stations = self._normalize(cursor.fetchall())

                # Convert UUID fields to string
                for station in stations:
                    for key, value in station.items():
                        if isinstance(value, uuid.UUID):
                            station[key] = str(value)

                return {"EC": 0, "EM": "Success", "data": stations}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi server: {str(e)}", "data": None}


def get_admin_bus_service() -> AdminBusService:
    """Dependency to get AdminBusService instance"""
    return AdminBusService()
