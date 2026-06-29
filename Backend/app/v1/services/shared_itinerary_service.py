"""
Shared Itinerary Service
Tạo và phục vụ lịch trình chia sẻ công khai (QR + link) cho tính năng viral.
Pattern theo visited_province_service.py (psycopg2 trực tiếp + async wrapper + EC/EM).
"""
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from ..core.config import settings

logger = logging.getLogger(__name__)

# Số ngày link chia sẻ sống (None = vĩnh viễn). 30 ngày theo kế hoạch.
SHARE_TTL_DAYS: Optional[int] = 30


class SharedItineraryService:
    """Service quản lý shared itineraries (lịch trình chia sẻ công khai)."""

    def __init__(self):
        pass

    def _pg_conn(self):
        return psycopg2.connect(settings.DATABASE_URL, cursor_factory=RealDictCursor)

    # ---------- serialization helpers ----------
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

    # ----------------------------- write --------------------------------
    async def create_share(
        self, user_id: str, payload: Dict[str, Any], title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Tạo một bản ghi lịch trình chia sẻ. Trả về share_id + public url.
        `payload` là JSON tuỳ ý do FE gửi (destination, days, total_price, ...).
        """
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO shared_itineraries (user_id, payload, title, expires_at)
                        VALUES (%s, %s::jsonb, %s,
                                CASE WHEN %s IS NULL THEN NULL ELSE NOW() + (%s || ' days')::interval END)
                        RETURNING share_id
                        """,
                        (
                            user_id,
                            psycopg2.extras.Json(payload),
                            title,
                            SHARE_TTL_DAYS,
                            str(SHARE_TTL_DAYS) if SHARE_TTL_DAYS else "0",
                        ),
                    )
                    row = cur.fetchone()
                    conn.commit()

            if not row:
                return {"EC": 1, "EM": "Không tạo được link chia sẻ", "share_id": None, "url": None}

            share_id = str(row["share_id"])
            url = f"{settings.SHARE_LINK_BASE_URL.rstrip('/')}/itinerary/{share_id}"
            return {"EC": 0, "EM": "Success", "share_id": share_id, "url": url}
        except Exception as e:
            logger.error("Error creating shared itinerary: %s", e)
            return {"EC": 1, "EM": f"Error creating share: {e}", "share_id": None, "url": None}

    # ----------------------------- read ---------------------------------
    async def get_shared(self, share_id: str) -> Dict[str, Any]:
        """
        Lấy lịch trình chia sẻ công khai (không cần auth). Tăng view_count.
        Trả EC:1 nếu không tìm thấy hoặc đã hết hạn.
        """
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT share_id, payload, title, view_count, expires_at, created_at
                        FROM shared_itineraries
                        WHERE share_id = %s
                          AND (expires_at IS NULL OR expires_at > NOW())
                        """,
                        (share_id,),
                    )
                    row = cur.fetchone()
                    if not row:
                        return {"EC": 1, "EM": "Không tìm thấy lịch trình hoặc link đã hết hạn"}

                    cur.execute(
                        "UPDATE shared_itineraries SET view_count = view_count + 1 "
                        "WHERE share_id = %s RETURNING view_count",
                        (share_id,),
                    )
                    bumped = cur.fetchone()
                    conn.commit()

            data = self._serialize_row(row)
            payload = data.get("payload")
            # Dùng giá trị view_count thực tế sau increment (tránh lệch 1 khi có truy cập đồng thời).
            view_count = (bumped.get("view_count") if bumped else None)
            if view_count is None:
                view_count = (data.get("view_count") or 0) + 1
            return {
                "EC": 0,
                "EM": "Success",
                "title": data.get("title") or "",
                "itinerary": payload if isinstance(payload, (dict, list)) else {},
                "view_count": view_count,
                "created_at": data.get("created_at"),
            }
        except Exception as e:
            logger.error("Error getting shared itinerary %s: %s", share_id, e)
            return {"EC": 1, "EM": f"Error retrieving share: {e}"}
