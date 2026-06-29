"""
Visited Province Service
Quản lý tính năng "Bản đồ khám phá Việt Nam": check-in tỉnh thành, thống kê tiến độ,
và auto check-in từ booking đã xác nhận.

Pattern theo favorite_service.py (psycopg2 trực tiếp + async wrapper + EC/EM).
"""
import logging
import re
import unicodedata
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from ..core.config import settings

logger = logging.getLogger(__name__)


# Map các điểm đến du lịch phổ biến (free-text trong booking) -> tên tỉnh (theo GeoJSON).
# Bù đắp trường hợp tên điểm đến != tên tỉnh (VD: "Đà Lạt" thuộc "Lâm Đồng").
DESTINATION_TO_PROVINCE: Dict[str, str] = {
    "da lat": "Lâm Đồng",
    "da lat city": "Lâm Đồng",
    "nha trang": "Khánh Hòa",
    "vung tau": "Bà Rịa - Vũng Tàu",
    "phan thiet": "Bình Thuận",
    "mui ne": "Bình Thuận",
    "hoi an": "Quảng Nam",
    "sapa": "Lào Cai",
    "sa pa": "Lào Cai",
    "phu quoc": "Kiên Giang",
    "hue": "Thừa Thiên - Huế",
    "moc chau": "Sơn La",
    "ha giang": "Hà Giang",
    "ha long": "Quảng Ninh",
    "ha long bay": "Quảng Ninh",
    "con dao": "Bà Rịa - Vũng Tàu",
    "da nang": "Đà Nẵng",
    "quy nhon": "Bình Định",
    "phan rang": "Ninh Thuận",
    "cao bang": "Cao Bằng",
    "dien bien": "Điện Biên",
    "phong nha": "Quảng Bình",
    "son doong": "Quảng Bình",
    "cat ba": "Hải Phòng",  # Cát Bà thuộc Hải Phòng
    "ly son": "Quảng Ngãi",
    "cu lao cham": "Quảng Nam",
    "tay ninh": "Tây Ninh",
    "ninh binh": "Ninh Bình",
    "trang an": "Ninh Bình",
    "mai chau": "Hòa Bình",
    "buon ma thuot": "Đắk Lắk",
    # 5 thành phố trực thuộc trung ương + alias phổ biến
    "ho chi minh": "Hồ Chí Minh city",
    "hcm": "Hồ Chí Minh city",
    "thanh pho ho chi minh": "Hồ Chí Minh city",
    "hanoi": "Hà Nội",
    "thanh pho ha noi": "Hà Nội",
    "can tho": "Cần Thơ",
    "hai phong": "Hải Phòng",
}


def _normalize(text: str) -> str:
    """Bỏ dấu tiếng Việt + lower case + trim để matching linh hoạt."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    # NFKD không tách được đ/Đ của tiếng Việt -> xử lý tay
    stripped = stripped.replace("đ", "d").replace("Đ", "D")
    return re.sub(r"\s+", " ", stripped).strip().lower()


class VisitedProvinceService:
    """Service quản lý visited provinces của user."""

    def __init__(self, supabase_client: Any | None = None):
        self.supabase = supabase_client

    def _pg_conn(self):
        return psycopg2.connect(settings.DATABASE_URL, cursor_factory=RealDictCursor)

    # ---------- serialization helpers (giống FavoriteTourService) ----------
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
    async def get_all_provinces(self) -> Dict[str, Any]:
        """Trả về 63 tỉnh để render bản đồ."""
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT province_id, province_code, province_name,
                               province_name_en, region, latitude, longitude
                        FROM provinces
                        ORDER BY region, province_name
                        """
                    )
                    provinces = self._serialize_rows(cur.fetchall())

            return {
                "EC": 0,
                "EM": "Successfully retrieved provinces",
                "total": len(provinces),
                "provinces": provinces,
            }
        except Exception as e:
            logger.error("Error getting all provinces: %s", e)
            return {"EC": 1, "EM": f"Error retrieving provinces: {e}", "total": 0, "provinces": []}

    async def get_user_visited(self, user_id: str) -> Dict[str, Any]:
        """Danh sách tỉnh đã check-in của user + thống kê tiến độ khám phá."""
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
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
                    provinces = self._serialize_rows(cur.fetchall())

                    cur.execute(
                        """
                        SELECT
                            COUNT(*) AS total,
                            COUNT(*) FILTER (WHERE p.region = 'north') AS north_count,
                            COUNT(*) FILTER (WHERE p.region = 'central') AS central_count,
                            COUNT(*) FILTER (WHERE p.region = 'south') AS south_count
                        FROM visited_provinces vp
                        JOIN provinces p ON p.province_id = vp.province_id
                        WHERE vp.user_id = %s
                        """,
                        (user_id,),
                    )
                    stats = cur.fetchone() or {}

                    cur.execute("SELECT COUNT(*) AS n FROM provinces")
                    total_provinces = (cur.fetchone() or {}).get("n", 63)

            total_visited = stats.get("total", 0) or 0
            progress = round((total_visited / total_provinces) * 100, 1) if total_provinces else 0.0

            return {
                "EC": 0,
                "EM": "Successfully retrieved visited provinces",
                "total": total_visited,
                "total_provinces": total_provinces,
                "north_count": stats.get("north_count", 0) or 0,
                "central_count": stats.get("central_count", 0) or 0,
                "south_count": stats.get("south_count", 0) or 0,
                "progress_percentage": progress,
                "provinces": provinces,
            }
        except Exception as e:
            logger.error("Error getting user visited: %s", e)
            return {
                "EC": 1,
                "EM": f"Error retrieving visited provinces: {e}",
                "total": 0,
                "total_provinces": 63,
                "north_count": 0,
                "central_count": 0,
                "south_count": 0,
                "progress_percentage": 0.0,
                "provinces": [],
            }

    # --------------------------- leaderboard ---------------------------
    async def get_leaderboard(
        self, limit: int = 20, offset: int = 0, viewer_user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Bảng xếp hạng người khám phá: top user theo số tỉnh đã check-in.
        - items: top N user (kèm số tỉnh + phân chia 3 miền).
        - total: tổng số explorer (đã check-in ít nhất 1 tỉnh).
        - my_rank: hạng của viewer (None nếu viewer chưa check-in tỉnh nào).
        """
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    # 1) Tổng số explorer
                    cur.execute(
                        """
                        SELECT COUNT(DISTINCT vp.user_id) AS n
                        FROM visited_provinces vp
                        JOIN users u ON u.user_id = vp.user_id
                        WHERE u.is_active = TRUE
                        """
                    )
                    total = (cur.fetchone() or {}).get("n", 0) or 0

                    # 2) Top N user
                    cur.execute(
                        """
                        SELECT u.user_id,
                               u.full_name,
                               u.avatar_url,
                               COUNT(vp.province_id) AS provinces_visited,
                               COUNT(*) FILTER (WHERE p.region = 'north')   AS north_count,
                               COUNT(*) FILTER (WHERE p.region = 'central') AS central_count,
                               COUNT(*) FILTER (WHERE p.region = 'south')   AS south_count,
                               MAX(vp.visited_at) AS last_visit_at
                        FROM visited_provinces vp
                        JOIN provinces p ON p.province_id = vp.province_id
                        JOIN users u ON u.user_id = vp.user_id
                        WHERE u.is_active = TRUE
                        GROUP BY u.user_id, u.full_name, u.avatar_url
                        ORDER BY provinces_visited DESC, last_visit_at ASC
                        LIMIT %s OFFSET %s
                        """,
                        (limit, offset),
                    )
                    items = self._serialize_rows(cur.fetchall())

                    # 3) Hạng của viewer = số user xếp trước + 1
                    my_rank = None
                    my_provinces_visited = 0
                    if viewer_user_id:
                        cur.execute(
                            """
                            SELECT COUNT(*) AS c, MAX(vp.visited_at) AS last_visit
                            FROM visited_provinces vp
                            WHERE vp.user_id = %s
                            """,
                            (viewer_user_id,),
                        )
                        mine = cur.fetchone() or {}
                        my_provinces_visited = mine.get("c", 0) or 0
                        my_last = mine.get("last_visit")
                        if my_provinces_visited > 0:
                            cur.execute(
                                """
                                SELECT COUNT(*) AS ahead
                                FROM (
                                    SELECT vp.user_id,
                                           COUNT(vp.province_id) AS cnt,
                                           MAX(vp.visited_at) AS last_visit
                                    FROM visited_provinces vp
                                    JOIN users u ON u.user_id = vp.user_id
                                    WHERE u.is_active = TRUE
                                    GROUP BY vp.user_id
                                ) s
                                WHERE s.cnt > %s
                                   OR (s.cnt = %s AND s.last_visit < %s)
                                """,
                                (my_provinces_visited, my_provinces_visited, my_last),
                            )
                            ahead = (cur.fetchone() or {}).get("ahead", 0) or 0
                            my_rank = ahead + 1

            return {
                "EC": 0,
                "EM": "Successfully retrieved leaderboard",
                "data": {
                    "items": items,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "my_rank": my_rank,
                    "my_provinces_visited": my_provinces_visited,
                },
            }
        except Exception as e:
            logger.error("Error getting leaderboard: %s", e)
            return {
                "EC": 1,
                "EM": f"Error retrieving leaderboard: {e}",
                "data": {
                    "items": [],
                    "total": 0,
                    "limit": limit,
                    "offset": offset,
                    "my_rank": None,
                    "my_provinces_visited": 0,
                },
            }

    # ----------------------------- write --------------------------------
    async def add_visited(self, user_id: str, province_id: str) -> Dict[str, Any]:
        """Check-in một tỉnh (manual). Đã tồn tại thì trả về is_visited=True (idempotent)."""
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO visited_provinces (user_id, province_id, visit_source, visited_at)
                        VALUES (%s, %s, 'manual', NOW())
                        ON CONFLICT (user_id, province_id) DO UPDATE
                            SET visited_at = NOW()
                        RETURNING visit_id
                        """,
                        (user_id, province_id),
                    )
                    cur.fetchone()
                    conn.commit()

            return {"EC": 0, "EM": "Province checked-in", "is_visited": True}
        except Exception as e:
            logger.error("Error adding visited province: %s", e)
            return {"EC": 1, "EM": f"Error checking-in province: {e}", "is_visited": False}

    async def remove_visited(self, user_id: str, province_id: str) -> Dict[str, Any]:
        """Bỏ check-in một tỉnh."""
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        DELETE FROM visited_provinces
                        WHERE user_id = %s AND province_id = %s
                        RETURNING visit_id
                        """,
                        (user_id, province_id),
                    )
                    cur.fetchone()
                    conn.commit()

            return {"EC": 0, "EM": "Province unchecked-in", "is_visited": False}
        except Exception as e:
            logger.error("Error removing visited province: %s", e)
            return {"EC": 1, "EM": f"Error unchecking-in province: {e}", "is_visited": True}

    # ----------------------- auto check-in (enhancement) ----------------
    async def auto_checkin_from_bookings(self, user_id: str) -> Dict[str, Any]:
        """
        Đồng bộ tỉnh đã đến từ booking đã xác nhận.
        - Lấy các chuỗi destination từ tour/hotel (mỗi nguồn độc lập, lỗi 1 nguồn không làm sập cả method).
        - Map destination -> tỉnh (curated map + fallback substring trên province name).
        - Check-in các tỉnh match được (source='auto_booking'), idempotent.
        Trả về số tỉnh mới + danh sách match để minh bạch.
        """
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    # Load provinces để matching trong Python
                    cur.execute(
                        "SELECT province_id, province_name, province_name_en FROM provinces"
                    )
                    all_provinces = cur.fetchall()

                    destinations = set()

                    # Tours: bookings JOIN tour_packages
                    try:
                        cur.execute(
                            """
                            SELECT DISTINCT tp.destination AS dest
                            FROM bookings b
                            JOIN tour_packages tp ON tp.package_id = b.package_id
                            WHERE b.user_id = %s
                              AND COALESCE(b.status, '') IN ('confirmed', 'completed')
                            """,
                            (user_id,),
                        )
                        destinations.update(
                            (r["dest"] for r in cur.fetchall() if r.get("dest"))
                        )
                    except Exception as e:
                        logger.warning("auto-checkin: tour source skipped: %s", e)

                    # Hotels: hotel_bookings JOIN hotels
                    try:
                        cur.execute(
                            """
                            SELECT DISTINCT h.location AS dest
                            FROM hotel_bookings hb
                            JOIN hotels h ON h.hotel_id = hb.hotel_id
                            WHERE hb.user_id = %s
                              AND COALESCE(hb.status, '') IN ('confirmed', 'completed')
                            """,
                            (user_id,),
                        )
                        destinations.update(
                            (r["dest"] for r in cur.fetchall() if r.get("dest"))
                        )
                    except Exception as e:
                        logger.warning("auto-checkin: hotel source skipped: %s", e)

                    # Build normalized province index once
                    prov_index = []  # (normalized_name, province_name, province_id)
                    for p in all_provinces:
                        prov_index.append((
                            _normalize(p["province_name"]),
                            p["province_name"],
                            str(p["province_id"]),
                        ))

                    matched_province_ids = set()
                    matched_names = []
                    for dest in destinations:
                        province_name = self._match_destination_to_province(dest, prov_index)
                        if not province_name:
                            continue
                        # province_name là display name; tìm id tương ứng
                        pid = next(
                            (str(p["province_id"]) for p in all_provinces
                             if p["province_name"] == province_name),
                            None,
                        )
                        if pid and pid not in matched_province_ids:
                            matched_province_ids.add(pid)
                            matched_names.append(province_name)

                    # Insert các tỉnh match (source = auto_booking)
                    new_count = 0
                    for pid in matched_province_ids:
                        cur.execute(
                            """
                            INSERT INTO visited_provinces (user_id, province_id, visit_source, visited_at)
                            VALUES (%s, %s, 'auto_booking', NOW())
                            ON CONFLICT (user_id, province_id) DO NOTHING
                            RETURNING visit_id
                            """,
                            (user_id, pid),
                        )
                        if cur.fetchone():
                            new_count += 1
                    conn.commit()

            return {
                "EC": 0,
                "EM": f"Auto check-in completed for {new_count} new province(s)",
                "auto_checkins": new_count,
                "matched": matched_names,
            }
        except Exception as e:
            logger.error("Error in auto check-in: %s", e)
            return {"EC": 1, "EM": f"Error in auto check-in: {e}", "auto_checkins": 0, "matched": []}

    @staticmethod
    def _match_destination_to_province(
        destination: str, prov_index: List[tuple]
    ) -> Optional[str]:
        """
        Match một chuỗi destination free-text -> tên tỉnh.
        1) Curated map (destination phổ biến).
        2) Fallback: destination normalized chứa province name normalized.
        Trả về province_name (display) hoặc None.
        """
        norm_dest = _normalize(destination)
        if not norm_dest:
            return None

        # 1) curated map (duyệt theo độ dài key giảm dần để match cụ thể trước)
        for key in sorted(DESTINATION_TO_PROVINCE.keys(), key=len, reverse=True):
            if key in norm_dest:
                return DESTINATION_TO_PROVINCE[key]

        # 2) fallback substring: destination chứa tên tỉnh
        for norm_name, display_name, _pid in prov_index:
            if norm_name and len(norm_name) >= 3 and norm_name in norm_dest:
                return display_name

        return None
