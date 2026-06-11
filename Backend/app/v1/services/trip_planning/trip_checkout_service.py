"""
Trip checkout service — creates custom plan, booking, and VNPay payment.
Mirrors the real tour booking + payment flow for authenticated users.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from app.v1.core.config import settings
from app.v1.core.supabase import get_supabase_client
from app.v1.services.payment_service import PaymentService
from app.v1.services.trip_planning.activity_service import normalize_destination

logger = logging.getLogger(__name__)


def calculate_grand_total(state: Dict[str, Any]) -> float:
    """Sum itinerary activities and selected transport."""
    total_price = float(state.get("itinerary_total_price") or 0)
    group_size = int(state.get("group_size") or 1)
    transport_extra = 0.0

    if state.get("selected_flight"):
        transport_extra += float(state["selected_flight"].get("price", 0) or 0) * group_size
    if state.get("selected_train"):
        transport_extra += float(state["selected_train"].get("price", 0) or 0) * group_size

    return total_price + transport_extra


class TripCheckoutService:
    """Persist custom trip plan and create booking + VNPay payment."""

    def _db_url(self) -> str:
        url = settings.DATABASE_URL or ""
        return url.replace("postgresql+asyncpg://", "postgresql://")

    def _conn(self):
        return psycopg2.connect(self._db_url(), cursor_factory=RealDictCursor)

    @staticmethod
    def _serialize_itinerary(itinerary: Dict[str, Any]) -> Dict[str, Any]:
        itinerary_data: Dict[str, Any] = {}
        for day_key, slots in (itinerary or {}).items():
            itinerary_data[day_key] = {}
            if not isinstance(slots, dict):
                continue
            for slot, activity in slots.items():
                if activity and isinstance(activity, dict):
                    itinerary_data[day_key][slot] = activity.get("activity_id") or activity.get("name")
                else:
                    itinerary_data[day_key][slot] = None
        return itinerary_data

    async def create_checkout(
        self,
        state: Dict[str, Any],
        ip_addr: str = "127.0.0.1",
        return_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create custom_trip_plans + tour_packages + bookings + payments.
        Returns dict with plan_id, booking_id, payment_url, total_price, error.
        """
        user_id = str(state.get("user_id") or "")
        if not user_id:
            return {"success": False, "error": "Thiếu thông tin người dùng."}

        destination = normalize_destination(state.get("destination") or "")
        duration_days = int(state.get("duration_days") or 1)
        group_size = int(state.get("group_size") or 1)
        grand_total = calculate_grand_total(state)
        if grand_total <= 0:
            return {"success": False, "error": "Tổng thanh toán không hợp lệ."}

        itinerary = state.get("confirmed_itinerary") or state.get("suggested_itinerary") or {}
        itinerary_data = self._serialize_itinerary(itinerary)
        price_per_person = grand_total / max(group_size, 1)

        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT full_name, email, phone_number
                        FROM users WHERE user_id = %s
                        """,
                        (user_id,),
                    )
                    user = cur.fetchone()
                    if not user:
                        return {"success": False, "error": "Không tìm thấy tài khoản người dùng."}

                    contact_name = user.get("full_name") or "Khách hàng"
                    contact_email = user.get("email") or ""
                    contact_phone = user.get("phone_number") or "0000000000"
                    phone_digits = "".join(ch for ch in contact_phone if ch.isdigit())
                    if len(phone_digits) < 9:
                        contact_phone = "0900000000"
                    else:
                        contact_phone = phone_digits[:10]

                    cur.execute(
                        """
                        INSERT INTO custom_trip_plans
                            (user_id, destination, travel_date, duration_days, group_size,
                             group_type, budget_level, itinerary, total_price, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING plan_id
                        """,
                        (
                            user_id,
                            destination,
                            state.get("travel_date"),
                            duration_days,
                            group_size,
                            state.get("group_type"),
                            state.get("budget_level"),
                            json.dumps(itinerary_data, ensure_ascii=False),
                            grand_total,
                            "pending_payment",
                        ),
                    )
                    plan_id = str(cur.fetchone()["plan_id"])

                    package_name = f"Ke hoach tuy chinh - {destination} {duration_days}N"
                    package_description = (
                        f"Trip Planner: {destination}, {duration_days} ngay, {group_size} nguoi. "
                        f"Plan ID: {plan_id}"
                    )
                    now = datetime.now(timezone.utc)

                    cur.execute(
                        """
                        INSERT INTO tour_packages
                            (package_name, destination, description, duration_days, price,
                             available_slots, is_active, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s, %s)
                        RETURNING package_id
                        """,
                        (
                            package_name,
                            destination,
                            package_description,
                            duration_days,
                            price_per_person,
                            max(group_size, 1),
                            now,
                            now,
                        ),
                    )
                    package_id = str(cur.fetchone()["package_id"])

                    special_requests = json.dumps(
                        {
                            "source": "trip_planner",
                            "plan_id": plan_id,
                            "itinerary": itinerary_data,
                            "transport": {
                                "flight": state.get("selected_flight"),
                                "train": state.get("selected_train"),
                            },
                        },
                        ensure_ascii=False,
                    )

                    cur.execute(
                        """
                        INSERT INTO bookings
                            (package_id, number_of_people, total_amount, contact_name,
                             contact_phone, contact_email, special_requests, user_id,
                             status, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING booking_id
                        """,
                        (
                            package_id,
                            group_size,
                            grand_total,
                            contact_name,
                            contact_phone,
                            contact_email,
                            special_requests,
                            user_id,
                            "pending",
                            now,
                            now,
                        ),
                    )
                    booking_id = str(cur.fetchone()["booking_id"])
                conn.commit()

            if not return_url:
                room_id = state.get("conversation_id") or ""
                if room_id:
                    return_url = (
                        f"{settings.FRONTEND_BASE_URL.rstrip('/')}/chat-room/{room_id}"
                        f"?payment_success=true"
                    )
                else:
                    return_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/chat-room?payment_success=true"

            payment_service = PaymentService(get_supabase_client())
            payment_result = await payment_service.create_payment(
                booking_id=booking_id,
                payment_method="vnpay",
                ip_addr=ip_addr,
                client_return_url=return_url,
            )

            if payment_result.get("EC") != 0 or not payment_result.get("data"):
                return {
                    "success": False,
                    "error": payment_result.get("EM") or "Không thể tạo thanh toán VNPay.",
                    "plan_id": plan_id,
                    "booking_id": booking_id,
                }

            payment = payment_result["data"]
            return {
                "success": True,
                "plan_id": plan_id,
                "booking_id": booking_id,
                "payment_id": str(payment.get("payment_id")),
                "payment_url": payment.get("payment_url"),
                "total_price": grand_total,
            }

        except Exception as exc:
            logger.error(f"Trip checkout failed: {exc}", exc_info=True)
            return {"success": False, "error": str(exc)}


trip_checkout_service = TripCheckoutService()
