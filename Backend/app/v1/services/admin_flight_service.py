"""
Admin Flight Service - CRUD cho quản lý chuyến bay
"""
from typing import Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
import csv
import io
from ..core.config import settings


class AdminFlightService:
    def __init__(self):
        self.db_url = settings.DATABASE_URL

    def _get_conn(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    def _normalize(self, rows):
        return [dict(r) for r in rows]

    def get_all_flights(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        status: Optional[str] = None,
        airline_id: Optional[str] = None,
        departure_airport: Optional[str] = None,
        arrival_airport: Optional[str] = None
    ) -> Dict[str, Any]:
        """Lấy danh sách chuyến bay"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM flights WHERE is_active = true"
                params = []
                conditions = []

                if status:
                    conditions.append("status = %s")
                    params.append(status)
                if airline_id:
                    conditions.append("airline_id = %s")
                    params.append(airline_id)
                if departure_airport:
                    conditions.append("departure_airport = %s")
                    params.append(departure_airport)
                if arrival_airport:
                    conditions.append("arrival_airport = %s")
                    params.append(arrival_airport)

                if conditions:
                    query += " AND " + " AND ".join(conditions)

                query += " ORDER BY created_at DESC"

                if limit:
                    query += " LIMIT %s"
                    params.append(limit)
                if offset:
                    query += " OFFSET %s"
                    params.append(offset)

                cursor.execute(query, params)
                flights = self._normalize(cursor.fetchall())

                # Get total count
                count_query = "SELECT COUNT(*) as total FROM flights WHERE is_active = true"
                count_params = []
                if conditions:
                    count_query += " AND " + " AND ".join(conditions)
                    count_params = params[:len(conditions)]

                cursor.execute(count_query, count_params)
                total = cursor.fetchone()['total']

                return {
                    "EC": 0,
                    "EM": "Success",
                    "data": {
                        "flights": flights,
                        "total": total
                    }
                }
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi server: {str(e)}", "data": None}

    def get_flight_by_id(self, flight_id: str) -> Dict[str, Any]:
        """Lấy chi tiết 1 chuyến bay"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM flights WHERE flight_id = %s", (flight_id,))
                flights = self._normalize(cursor.fetchall())

                if not flights:
                    return {"EC": 1, "EM": "Không tìm thấy chuyến bay", "data": None}

                flight = flights[0]
                for key, value in flight.items():
                    if isinstance(value, uuid.UUID):
                        flight[key] = str(value)

                return {"EC": 0, "EM": "Success", "data": flight}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi server: {str(e)}", "data": None}

    def create_flight(self, flight_data: Dict[str, Any]) -> Dict[str, Any]:
        """Tạo chuyến bay mới"""
        try:
            if "flight_id" not in flight_data:
                flight_data["flight_id"] = f"FL-{uuid.uuid4().hex[:8].upper()}"

            with self._get_conn() as conn:
                cursor = conn.cursor()

                columns = flight_data.keys()
                placeholders = ", ".join(["%s"] * len(columns))
                column_names = ", ".join(columns)
                values = list(flight_data.values())

                query = f"INSERT INTO flights ({column_names}) VALUES ({placeholders}) RETURNING *"
                cursor.execute(query, values)
                conn.commit()

                flight = dict(cursor.fetchone())
                for key, value in flight.items():
                    if isinstance(value, uuid.UUID):
                        flight[key] = str(value)

                return {"EC": 0, "EM": "Tạo chuyến bay thành công", "data": flight}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi tạo chuyến bay: {str(e)}", "data": None}

    def update_flight(self, flight_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cập nhật chuyến bay"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT flight_id FROM flights WHERE flight_id = %s", (flight_id,))
                if not cursor.fetchone():
                    return {"EC": 1, "EM": "Không tìm thấy chuyến bay", "data": None}

                set_clause = ", ".join([f"{key} = %s" for key in update_data.keys()])
                values = list(update_data.values())
                values.append(flight_id)

                query = f"UPDATE flights SET {set_clause} WHERE flight_id = %s RETURNING *"
                cursor.execute(query, values)
                conn.commit()

                flight = dict(cursor.fetchone())
                for key, value in flight.items():
                    if isinstance(value, uuid.UUID):
                        flight[key] = str(value)

                return {"EC": 0, "EM": "Cập nhật thành công", "data": flight}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi cập nhật: {str(e)}", "data": None}

    def delete_flight(self, flight_id: str) -> Dict[str, Any]:
        """Xóa chuyến bay (soft delete)"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT flight_id FROM flights WHERE flight_id = %s", (flight_id,))
                if not cursor.fetchone():
                    return {"EC": 1, "EM": "Không tìm thấy chuyến bay", "data": None}

                cursor.execute("UPDATE flights SET is_active = false WHERE flight_id = %s", (flight_id,))
                conn.commit()

                return {"EC": 0, "EM": "Xóa chuyến bay thành công", "data": None}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi xóa: {str(e)}", "data": None}

    def update_flight_status(self, flight_id: str, status: str) -> Dict[str, Any]:
        """Cập nhật trạng thái chuyến bay"""
        valid_statuses = ["scheduled", "boarding", "departed", "arrived", "cancelled"]
        if status not in valid_statuses:
            return {"EC": 1, "EM": f"Trạng thái không hợp lệ. Hợp lệ: {', '.join(valid_statuses)}", "data": None}

        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT flight_id FROM flights WHERE flight_id = %s", (flight_id,))
                if not cursor.fetchone():
                    return {"EC": 1, "EM": "Không tìm thấy chuyến bay", "data": None}

                cursor.execute(
                    "UPDATE flights SET status = %s WHERE flight_id = %s RETURNING *",
                    (status, flight_id)
                )
                conn.commit()

                flight = dict(cursor.fetchone())
                for key, value in flight.items():
                    if isinstance(value, uuid.UUID):
                        flight[key] = str(value)

                return {"EC": 0, "EM": "Cập nhật trạng thái thành công", "data": flight}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi cập nhật: {str(e)}", "data": None}

    def get_airlines(self) -> Dict[str, Any]:
        """Lấy danh sách hãng bay"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM airlines WHERE is_active = true")
                airlines = self._normalize(cursor.fetchall())

                for airline in airlines:
                    for key, value in airline.items():
                        if isinstance(value, uuid.UUID):
                            airline[key] = str(value)

                return {"EC": 0, "EM": "Success", "data": airlines}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi server: {str(e)}", "data": None}

    def get_airports(self) -> Dict[str, Any]:
        """Lấy danh sách sân bay"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM airports WHERE is_active = true")
                airports = self._normalize(cursor.fetchall())

                for airport in airports:
                    for key, value in airport.items():
                        if isinstance(value, uuid.UUID):
                            airport[key] = str(value)

                return {"EC": 0, "EM": "Success", "data": airports}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi server: {str(e)}", "data": None}

    def create_flights_from_csv(self, csv_text: str) -> Dict[str, Any]:
        """Tạo nhiều chuyến bay từ CSV"""
        try:
            reader = csv.DictReader(io.StringIO(csv_text))
            success_count = 0
            fail_count = 0
            errors = []

            for row_num, row in enumerate(reader, start=2):
                try:
                    flight_data = {
                        "flight_id": f"FL-{uuid.uuid4().hex[:8].upper()}",
                        "flight_number": row.get("flight_number", "").strip(),
                        "airline_id": row.get("airline_id", "").strip(),
                        "departure_airport": row.get("departure_airport", "").strip(),
                        "arrival_airport": row.get("arrival_airport", "").strip(),
                        "departure_time": row.get("departure_time", "").strip(),
                        "arrival_time": row.get("arrival_time", "").strip(),
                        "duration_minutes": int(row.get("duration_minutes", 0) or 0),
                        "aircraft": row.get("aircraft", "").strip(),
                        "economy_price": int(row.get("economy_price", 0) or 0),
                        "business_price": int(row.get("business_price", 0) or 0),
                        "first_class_price": int(row.get("first_class_price", 0) or 0) or None,
                        "economy_seats": int(row.get("economy_seats", 150) or 150),
                        "business_seats": int(row.get("business_seats", 20) or 20),
                        "first_class_seats": int(row.get("first_class_seats", 0) or 0),
                        "status": row.get("status", "scheduled").strip() or "scheduled",
                    }

                    if not flight_data["flight_number"]:
                        raise ValueError("Thiếu flight_number")

                    result = self.create_flight(flight_data)
                    if result["EC"] == 0:
                        success_count += 1
                    else:
                        fail_count += 1
                        errors.append({"row": row_num, "error": result["EM"]})
                except Exception as e:
                    fail_count += 1
                    errors.append({"row": row_num, "error": str(e)})

            return {
                "EC": 0,
                "EM": f"Import hoàn tất: {success_count} thành công, {fail_count} thất bại",
                "data": {
                    "success_count": success_count,
                    "fail_count": fail_count,
                    "errors": errors
                }
            }
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi đọc CSV: {str(e)}", "data": None}


def get_admin_flight_service() -> AdminFlightService:
    """Dependency to get AdminFlightService instance"""
    return AdminFlightService()
