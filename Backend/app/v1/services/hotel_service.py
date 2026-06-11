"""
Hotel Service - Public CRUD cho khach san
Su dung psycopg2 truc tiep
"""
from typing import Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from app.v1.core.config import settings


class HotelService:
    def __init__(self):
        self.db_url = settings.DATABASE_URL

    def _get_conn(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    def _normalize(self, rows):
        """Convert RealDictRow to plain dict"""
        return [dict(r) for r in rows]

    def get_all_hotels(
        self,
        location: Optional[str] = None,
        search: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """Lay danh sach khach san active"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    sql = "SELECT * FROM hotels WHERE is_active = TRUE"
                    params = []

                    if location:
                        sql += " AND location ILIKE %s"
                        params.append(f"%{location}%")
                    if search:
                        sql += " AND (hotel_name ILIKE %s OR location ILIKE %s)"
                        params.extend([f"%{search}%", f"%{search}%"])
                    if min_price is not None:
                        sql += " AND price >= %s"
                        params.append(min_price)
                    if max_price is not None:
                        sql += " AND price <= %s"
                        params.append(max_price)

                    # Count
                    count_sql = sql.replace("SELECT *", "SELECT COUNT(*) as cnt")
                    cur.execute(count_sql, params)
                    total = cur.fetchone()["cnt"]

                    sql += " ORDER BY review_score DESC"
                    if limit:
                        sql += " LIMIT %s"
                        params.append(limit)
                    if offset:
                        sql += " OFFSET %s"
                        params.append(offset)

                    cur.execute(sql, params)
                    hotels = self._normalize(cur.fetchall())

            return {
                "EC": 0,
                "EM": "Success",
                "total": total,
                "hotels": hotels
            }
        except Exception as e:
            return {"EC": 2, "EM": f"Loi server: {str(e)}", "total": 0, "hotels": []}

    def get_hotel_by_id(self, hotel_id: str) -> Dict[str, Any]:
        """Lay chi tiet 1 khach san"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM hotels WHERE hotel_id = %s AND is_active = TRUE", (hotel_id,))
                    row = cur.fetchone()

            if not row:
                return {"EC": 1, "EM": "Khong tim thay khach san", "hotel": None}
            return {"EC": 0, "EM": "Success", "hotel": dict(row)}
        except Exception as e:
            return {"EC": 2, "EM": f"Loi server: {str(e)}", "hotel": None}

    def get_hotel_locations(self) -> Dict[str, Any]:
        """Lay danh sach dia diem co khach san"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT DISTINCT location FROM hotels WHERE is_active = TRUE ORDER BY location")
                    locations = [row["location"] for row in cur.fetchall()]
            return {"EC": 0, "EM": "Success", "data": locations}
        except Exception as e:
            return {"EC": 2, "EM": f"Loi server: {str(e)}", "data": []}


def get_hotel_service() -> HotelService:
    """Dependency to get HotelService instance"""
    return HotelService()
