"""
Admin Train Service - CRUD cho quản lý chuyến tàu
"""
from typing import Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import uuid
import csv
import io
from ..core.config import settings


class AdminTrainService:
    def __init__(self):
        self.db_url = settings.DATABASE_URL

    def _get_conn(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    def _normalize(self, rows):
        return [dict(r) for r in rows]

    def get_all_trains(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        status: Optional[str] = None,
        train_type_id: Optional[str] = None,
        departure_station: Optional[str] = None,
        arrival_station: Optional[str] = None
    ) -> Dict[str, Any]:
        """Lấy danh sách chuyến tàu"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM trains WHERE is_active = true"
                params = []
                conditions = []

                if status:
                    conditions.append("status = %s")
                    params.append(status)
                if train_type_id:
                    conditions.append("train_type_id = %s")
                    params.append(train_type_id)
                if departure_station:
                    conditions.append("departure_station = %s")
                    params.append(departure_station)
                if arrival_station:
                    conditions.append("arrival_station = %s")
                    params.append(arrival_station)

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
                trains = self._normalize(cursor.fetchall())

                # Get total count
                count_query = "SELECT COUNT(*) as total FROM trains WHERE is_active = true"
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
                        "trains": trains,
                        "total": total
                    }
                }
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi server: {str(e)}", "data": None}

    def get_train_by_id(self, train_id: str) -> Dict[str, Any]:
        """Lấy chi tiết 1 chuyến tàu"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM trains WHERE train_id = %s", (train_id,))
                trains = self._normalize(cursor.fetchall())

                if not trains:
                    return {"EC": 1, "EM": "Không tìm thấy chuyến tàu", "data": None}

                train = trains[0]
                for key, value in train.items():
                    if isinstance(value, uuid.UUID):
                        train[key] = str(value)

                return {"EC": 0, "EM": "Success", "data": train}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi server: {str(e)}", "data": None}

    def create_train(self, train_data: Dict[str, Any]) -> Dict[str, Any]:
        """Tạo chuyến tàu mới"""
        try:
            if "train_id" not in train_data:
                train_data["train_id"] = f"TR-{uuid.uuid4().hex[:8].upper()}"

            with self._get_conn() as conn:
                cursor = conn.cursor()

                columns = train_data.keys()
                placeholders = ", ".join(["%s"] * len(columns))
                column_names = ", ".join(columns)
                values = list(train_data.values())

                query = f"INSERT INTO trains ({column_names}) VALUES ({placeholders}) RETURNING *"
                cursor.execute(query, values)
                conn.commit()

                train = dict(cursor.fetchone())
                for key, value in train.items():
                    if isinstance(value, uuid.UUID):
                        train[key] = str(value)

                return {"EC": 0, "EM": "Tạo chuyến tàu thành công", "data": train}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi tạo chuyến tàu: {str(e)}", "data": None}

    def update_train(self, train_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cập nhật chuyến tàu"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT train_id FROM trains WHERE train_id = %s", (train_id,))
                if not cursor.fetchone():
                    return {"EC": 1, "EM": "Không tìm thấy chuyến tàu", "data": None}

                set_clause = ", ".join([f"{key} = %s" for key in update_data.keys()])
                values = list(update_data.values())
                values.append(train_id)

                query = f"UPDATE trains SET {set_clause} WHERE train_id = %s RETURNING *"
                cursor.execute(query, values)
                conn.commit()

                train = dict(cursor.fetchone())
                for key, value in train.items():
                    if isinstance(value, uuid.UUID):
                        train[key] = str(value)

                return {"EC": 0, "EM": "Cập nhật thành công", "data": train}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi cập nhật: {str(e)}", "data": None}

    def delete_train(self, train_id: str) -> Dict[str, Any]:
        """Xóa chuyến tàu (soft delete)"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT train_id FROM trains WHERE train_id = %s", (train_id,))
                if not cursor.fetchone():
                    return {"EC": 1, "EM": "Không tìm thấy chuyến tàu", "data": None}

                cursor.execute("UPDATE trains SET is_active = false WHERE train_id = %s", (train_id,))
                conn.commit()

                return {"EC": 0, "EM": "Xóa chuyến tàu thành công", "data": None}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi xóa: {str(e)}", "data": None}

    def update_train_status(self, train_id: str, status: str) -> Dict[str, Any]:
        """Cập nhật trạng thái chuyến tàu"""
        valid_statuses = ["scheduled", "departed", "arrived", "cancelled"]
        if status not in valid_statuses:
            return {"EC": 1, "EM": f"Trạng thái không hợp lệ. Hợp lệ: {', '.join(valid_statuses)}", "data": None}

        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                cursor.execute("SELECT train_id FROM trains WHERE train_id = %s", (train_id,))
                if not cursor.fetchone():
                    return {"EC": 1, "EM": "Không tìm thấy chuyến tàu", "data": None}

                cursor.execute(
                    "UPDATE trains SET status = %s WHERE train_id = %s RETURNING *",
                    (status, train_id)
                )
                conn.commit()

                train = dict(cursor.fetchone())
                for key, value in train.items():
                    if isinstance(value, uuid.UUID):
                        train[key] = str(value)

                return {"EC": 0, "EM": "Cập nhật trạng thái thành công", "data": train}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi cập nhật: {str(e)}", "data": None}

    def get_train_stations(self) -> Dict[str, Any]:
        """Lấy danh sách ga tàu"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM train_stations WHERE is_active = true")
                stations = self._normalize(cursor.fetchall())

                for station in stations:
                    for key, value in station.items():
                        if isinstance(value, uuid.UUID):
                            station[key] = str(value)

                return {"EC": 0, "EM": "Success", "data": stations}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi server: {str(e)}", "data": None}

    def get_train_types(self) -> Dict[str, Any]:
        """Lấy danh sách loại tàu"""
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM train_types WHERE is_active = true")
                types = self._normalize(cursor.fetchall())

                for t in types:
                    for key, value in t.items():
                        if isinstance(value, uuid.UUID):
                            t[key] = str(value)

                return {"EC": 0, "EM": "Success", "data": types}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi server: {str(e)}", "data": None}

    def create_trains_from_csv(self, csv_text: str) -> Dict[str, Any]:
        """Tạo nhiều chuyến tàu từ CSV"""
        try:
            reader = csv.DictReader(io.StringIO(csv_text))
            success_count = 0
            fail_count = 0
            errors = []

            for row_num, row in enumerate(reader, start=2):
                try:
                    train_data = {
                        "train_id": f"TR-{uuid.uuid4().hex[:8].upper()}",
                        "train_number": row.get("train_number", "").strip(),
                        "train_type_id": row.get("train_type_id", "").strip(),
                        "departure_station": row.get("departure_station", "").strip(),
                        "arrival_station": row.get("arrival_station", "").strip(),
                        "departure_time": row.get("departure_time", "").strip(),
                        "arrival_time": row.get("arrival_time", "").strip(),
                        "duration_hours": float(row.get("duration_hours", 0) or 0),
                        "status": row.get("status", "scheduled").strip() or "scheduled",
                    }

                    if not train_data["train_number"]:
                        raise ValueError("Thiếu train_number")

                    result = self.create_train(train_data)
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


def get_admin_train_service() -> AdminTrainService:
    """Dependency to get AdminTrainService instance"""
    return AdminTrainService()
