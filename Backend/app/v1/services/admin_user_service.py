"""
Admin User Management Service
Business logic for admin customer management operations
Uses psycopg2 direct connection (same as HotelService)
"""
import logging
import bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from ..core.config import settings

logger = logging.getLogger(__name__)


class AdminUserService:
    """Service for admin user management operations"""

    def __init__(self):
        self.db_url = settings.DATABASE_URL
        self.salt_rounds = 10

    def _get_conn(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    def _normalize(self, rows):
        """Convert RealDictRow to plain dict"""
        return [dict(r) for r in rows]

    def _hash_password(self, password: str) -> str:
        salt = bcrypt.gensalt(rounds=self.salt_rounds)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT user_id, email, full_name, phone as phone_number,
                               avatar_url as profile_picture, role, is_active, created_at, updated_at
                        FROM users WHERE user_id = %s
                    """, (user_id,))
                    row = cur.fetchone()

            if not row:
                return {"EC": 1, "EM": "User not found", "data": None}

            user = dict(row)
            user["user_id"] = str(user["user_id"])
            return {"EC": 0, "EM": "Success", "data": user}
        except Exception as e:
            logger.error(f"Error getting user profile {user_id}: {str(e)}", exc_info=True)
            return {"EC": 2, "EM": f"Error retrieving user profile: {str(e)}", "data": None}

    def get_user_bookings(
        self,
        user_id: str,
        page: int = 1,
        limit: int = 20,
        status: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        sort: str = "created_at_desc"
    ) -> Dict[str, Any]:
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Count total
                    count_sql = """
                        SELECT COUNT(*) as cnt FROM bookings b
                        JOIN tour_packages tp ON b.package_id = tp.package_id
                        WHERE b.user_id = %s
                    """
                    params: list = [user_id]

                    if status:
                        count_sql += " AND b.status = %s"
                        params.append(status)
                    if from_date:
                        count_sql += " AND b.created_at >= %s"
                        params.append(from_date)
                    if to_date:
                        count_sql += " AND b.created_at <= %s"
                        params.append(to_date)

                    cur.execute(count_sql, params)
                    total = cur.fetchone()["cnt"]

                    # Fetch bookings
                    order_map = {
                        "start_date_desc": "tp.start_date DESC",
                        "start_date_asc": "tp.start_date ASC",
                        "created_at_desc": "b.created_at DESC"
                    }
                    order = order_map.get(sort, "b.created_at DESC")

                    data_sql = f"""
                        SELECT b.booking_id, b.user_id, b.package_id, b.number_of_people,
                               b.total_amount, b.status, b.created_at,
                               tp.package_name, tp.start_date, tp.end_date
                        FROM bookings b
                        JOIN tour_packages tp ON b.package_id = tp.package_id
                        WHERE b.user_id = %s
                    """
                    data_params: list = [user_id]

                    if status:
                        data_sql += " AND b.status = %s"
                        data_params.append(status)
                    if from_date:
                        data_sql += " AND b.created_at >= %s"
                        data_params.append(from_date)
                    if to_date:
                        data_sql += " AND b.created_at <= %s"
                        data_params.append(to_date)

                    data_sql += f" ORDER BY {order}"
                    offset = (page - 1) * limit
                    data_sql += " LIMIT %s OFFSET %s"
                    data_params.extend([limit, offset])

                    cur.execute(data_sql, data_params)
                    rows = self._normalize(cur.fetchall())

            items = []
            for b in rows:
                items.append({
                    "booking_id": str(b["booking_id"]),
                    "user_id": str(b["user_id"]),
                    "package_id": str(b["package_id"]),
                    "package_name": b.get("package_name", ""),
                    "start_date": b.get("start_date"),
                    "end_date": b.get("end_date"),
                    "number_of_people": b.get("number_of_people", 0),
                    "total_price": float(b.get("total_amount", 0)),
                    "currency": "VND",
                    "status": b.get("status", ""),
                    "created_at": b.get("created_at")
                })

            total_pages = (total + limit - 1) // limit if total > 0 else 0

            return {
                "EC": 0, "EM": "Success",
                "data": {
                    "items": items, "page": page, "limit": limit,
                    "total": total, "total_pages": total_pages
                }
            }
        except Exception as e:
            logger.error(f"Error getting user bookings {user_id}: {str(e)}", exc_info=True)
            return {"EC": 2, "EM": f"Error retrieving user bookings: {str(e)}", "data": None}

    def set_user_active(
        self,
        user_id: str,
        is_active: bool,
        reason: Optional[str] = None,
        admin_id: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE users SET is_active = %s, updated_at = NOW()
                        WHERE user_id = %s
                        RETURNING user_id
                    """, (is_active, user_id))
                    row = cur.fetchone()
                    conn.commit()

            if not row:
                return {"EC": 1, "EM": "User not found", "data": None}

            if reason:
                logger.info(f"Admin {admin_id} {'disabled' if not is_active else 'enabled'} user {user_id}. Reason: {reason}")

            return {"EC": 0, "EM": "Success", "data": {"user_id": user_id, "is_active": is_active}}
        except Exception as e:
            logger.error(f"Error updating user status {user_id}: {str(e)}", exc_info=True)
            return {"EC": 2, "EM": f"Error updating user status: {str(e)}", "data": None}

    def get_user_summary(
        self,
        user_id: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            profile_result = self.get_user_profile(user_id)
            if profile_result["EC"] != 0:
                return profile_result

            user_profile = profile_result["data"]

            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Booking KPIs
                    booking_sql = """
                        SELECT status, COUNT(*) as cnt, COALESCE(SUM(total_amount), 0) as total
                        FROM bookings WHERE user_id = %s
                    """
                    params: list = [user_id]
                    if from_date:
                        booking_sql += " AND created_at >= %s"
                        params.append(from_date)
                    if to_date:
                        booking_sql += " AND created_at <= %s"
                        params.append(to_date)
                    booking_sql += " GROUP BY status"

                    cur.execute(booking_sql, params)
                    booking_stats = self._normalize(cur.fetchall())

                    total_bookings = sum(s["cnt"] for s in booking_stats)
                    completed_tours = next((s["cnt"] for s in booking_stats if s["status"] == "completed"), 0)
                    cancelled_bookings = next((s["cnt"] for s in booking_stats if s["status"] == "cancelled"), 0)
                    pending_bookings = next((s["cnt"] for s in booking_stats if s["status"] == "pending"), 0)
                    confirmed_bookings = next((s["cnt"] for s in booking_stats if s["status"] == "confirmed"), 0)

                    # Payment total
                    payment_sql = """
                        SELECT COALESCE(SUM(amount), 0) as total_paid FROM payments
                        WHERE user_id = %s AND payment_status = 'completed'
                    """
                    pay_params: list = [user_id]
                    if from_date:
                        payment_sql += " AND paid_at >= %s"
                        pay_params.append(from_date)
                    if to_date:
                        payment_sql += " AND paid_at <= %s"
                        pay_params.append(to_date)

                    cur.execute(payment_sql, pay_params)
                    total_paid = float(cur.fetchone()["total_paid"])

                    # Recent bookings
                    cur.execute("""
                        SELECT b.booking_id, b.package_id, b.status, b.total_amount, b.created_at,
                               tp.package_name
                        FROM bookings b
                        JOIN tour_packages tp ON b.package_id = tp.package_id
                        WHERE b.user_id = %s
                        ORDER BY b.created_at DESC LIMIT 10
                    """, (user_id,))
                    recent_bookings = []
                    for b in self._normalize(cur.fetchall()):
                        recent_bookings.append({
                            "booking_id": str(b["booking_id"]),
                            "package_id": str(b["package_id"]),
                            "package_name": b.get("package_name", ""),
                            "status": b.get("status", ""),
                            "total_price": float(b.get("total_amount", 0)),
                            "created_at": b.get("created_at")
                        })

                    # Recent payments
                    cur.execute("""
                        SELECT payment_id, amount, payment_status, paid_at
                        FROM payments WHERE user_id = %s
                        ORDER BY paid_at DESC LIMIT 10
                    """, (user_id,))
                    recent_payments = []
                    for p in self._normalize(cur.fetchall()):
                        recent_payments.append({
                            "payment_id": str(p.get("payment_id", "")),
                            "amount": float(p.get("amount", 0)),
                            "status": p.get("payment_status", ""),
                            "paid_at": p.get("paid_at")
                        })

            return {
                "EC": 0, "EM": "Success",
                "data": {
                    "user": user_profile,
                    "kpi": {
                        "total_paid_amount": total_paid,
                        "currency": "VND",
                        "total_bookings": total_bookings,
                        "completed_tours": completed_tours,
                        "cancelled_bookings": cancelled_bookings,
                        "pending_bookings": pending_bookings,
                        "confirmed_bookings": confirmed_bookings
                    },
                    "recent": {
                        "recent_bookings": recent_bookings,
                        "recent_payments": recent_payments
                    }
                }
            }
        except Exception as e:
            logger.error(f"Error getting user summary {user_id}: {str(e)}", exc_info=True)
            return {"EC": 2, "EM": f"Error retrieving user summary: {str(e)}", "data": None}

    def get_user_chat_history(self, user_id: str) -> Dict[str, Any]:
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT room_id, title, created_at, updated_at
                        FROM chat_rooms WHERE user_id = %s
                        ORDER BY updated_at DESC
                    """, (user_id,))
                    rooms = self._normalize(cur.fetchall())

                    rooms_data = []
                    for room in rooms:
                        room_id = room["room_id"]
                        cur.execute("""
                            SELECT message_id, role, content, intent, created_at
                            FROM chat_history
                            WHERE conversation_id = %s
                            ORDER BY created_at ASC LIMIT 50
                        """, (room_id,))
                        messages = []
                        for msg in self._normalize(cur.fetchall()):
                            messages.append({
                                "message_id": str(msg["message_id"]),
                                "role": msg.get("role", ""),
                                "content": msg.get("content", ""),
                                "intent": msg.get("intent"),
                                "created_at": msg.get("created_at")
                            })

                        cur.execute("""
                            SELECT COUNT(*) as cnt FROM chat_history WHERE conversation_id = %s
                        """, (room_id,))
                        msg_count = cur.fetchone()["cnt"]

                        rooms_data.append({
                            "room_id": room_id,
                            "title": room.get("title"),
                            "created_at": room.get("created_at"),
                            "updated_at": room.get("updated_at"),
                            "message_count": msg_count,
                            "messages": messages
                        })

            return {
                "EC": 0, "EM": "Success",
                "data": {"user_id": user_id, "total_rooms": len(rooms_data), "rooms": rooms_data}
            }
        except Exception as e:
            logger.error(f"Error getting user chat history {user_id}: {str(e)}", exc_info=True)
            return {"EC": 2, "EM": f"Error retrieving user chat history: {str(e)}", "data": None}

    def get_all_users(self) -> Dict[str, Any]:
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT user_id, email, full_name, phone as phone_number,
                               avatar_url as profile_picture, role, is_active, created_at, updated_at
                        FROM users ORDER BY created_at DESC
                    """)
                    rows = self._normalize(cur.fetchall())

            users = []
            for user in rows:
                users.append({
                    "user_id": str(user["user_id"]),
                    "email": user.get("email", ""),
                    "full_name": user.get("full_name"),
                    "phone_number": user.get("phone_number"),
                    "profile_picture": user.get("profile_picture"),
                    "role": user.get("role", "user"),
                    "is_active": user.get("is_active", True),
                    "created_at": user.get("created_at"),
                    "updated_at": user.get("updated_at")
                })

            return {"EC": 0, "EM": "Success", "data": {"users": users, "total": len(users)}}
        except Exception as e:
            logger.error(f"Error getting all users: {str(e)}", exc_info=True)
            return {"EC": 2, "EM": f"Error retrieving users: {str(e)}", "data": None}

    def delete_user(self, user_id: str) -> Dict[str, Any]:
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Check user exists
                    cur.execute("SELECT user_id, email, full_name FROM users WHERE user_id = %s", (user_id,))
                    user = cur.fetchone()
                    if not user:
                        return {"EC": 1, "EM": "User not found", "data": None}

                    # Check related records
                    for table in ["bookings", "payments", "reviews", "chat_rooms", "otp_verifications"]:
                        cur.execute(f"SELECT 1 FROM {table} WHERE user_id = %s LIMIT 1", (user_id,))
                        if cur.fetchone():
                            return {
                                "EC": 3,
                                "EM": f"Cannot delete user: User has related records in {table}.",
                                "data": None
                            }

                    # Safe to delete
                    cur.execute("DELETE FROM users WHERE user_id = %s RETURNING user_id", (user_id,))
                    deleted = cur.fetchone()
                    conn.commit()

                    if not deleted:
                        return {"EC": 2, "EM": "Failed to delete user", "data": None}

                    logger.info(f"Admin deleted user {user_id} ({user.get('email', 'N/A')})")
                    return {
                        "EC": 0, "EM": "User deleted successfully",
                        "data": {
                            "user_id": user_id,
                            "email": user.get("email"),
                            "full_name": user.get("full_name")
                        }
                    }
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {str(e)}", exc_info=True)
            return {"EC": 2, "EM": f"Error deleting user: {str(e)}", "data": None}

    def create_user(
        self,
        email: str,
        full_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        password: Optional[str] = None,
        role: str = "user",
        is_active: bool = True
    ) -> Dict[str, Any]:
        try:
            import secrets
            import string

            if not password:
                alphabet = string.ascii_letters + string.digits
                password = ''.join(secrets.choice(alphabet) for i in range(12))

            hashed_password = self._hash_password(password)

            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Check duplicate email
                    cur.execute("SELECT user_id FROM users WHERE email = %s", (email,))
                    if cur.fetchone():
                        return {"EC": 1, "EM": "Email already exists", "data": None}

                    cur.execute("""
                        INSERT INTO users (full_name, email, password_hash, phone, is_active, role, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                        RETURNING user_id, email, full_name, phone as phone_number, role, is_active
                    """, (full_name or email.split('@')[0], email, hashed_password, phone_number, is_active, role))
                    user = dict(cur.fetchone())
                    conn.commit()

            user["user_id"] = str(user["user_id"])
            user["password"] = password  # Return password for admin to share

            logger.info(f"Admin created user {user['user_id']} ({email})")
            return {"EC": 0, "EM": "User created successfully", "data": user}
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}", exc_info=True)
            return {"EC": 2, "EM": f"Error creating user: {str(e)}", "data": None}

    def update_user(
        self,
        user_id: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        password: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Check user exists
                    cur.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
                    if not cur.fetchone():
                        return {"EC": 1, "EM": "User not found", "data": None}

                    # Check email uniqueness if changing
                    if email:
                        cur.execute("SELECT user_id FROM users WHERE email = %s AND user_id != %s", (email, user_id))
                        if cur.fetchone():
                            return {"EC": 2, "EM": "Email already exists", "data": None}

                    if role and role not in ["user", "admin"]:
                        return {"EC": 2, "EM": "Invalid role. Must be 'user' or 'admin'", "data": None}

                    # Build dynamic UPDATE
                    updates = ["updated_at = NOW()"]
                    params: list = []

                    if email is not None:
                        updates.append("email = %s")
                        params.append(email)
                    if full_name is not None:
                        updates.append("full_name = %s")
                        params.append(full_name)
                    if phone_number is not None:
                        updates.append("phone = %s")
                        params.append(phone_number)
                    if role is not None:
                        updates.append("role = %s")
                        params.append(role)
                    if is_active is not None:
                        updates.append("is_active = %s")
                        params.append(is_active)
                    if password is not None:
                        updates.append("password_hash = %s")
                        params.append(self._hash_password(password))

                    params.append(user_id)
                    sql = f"UPDATE users SET {', '.join(updates)} WHERE user_id = %s RETURNING user_id, email, full_name, phone as phone_number, role, is_active, updated_at"

                    cur.execute(sql, params)
                    updated = dict(cur.fetchone())
                    conn.commit()

            updated["user_id"] = str(updated["user_id"])
            logger.info(f"Admin updated user {user_id}")
            return {"EC": 0, "EM": "User updated successfully", "data": updated}
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {str(e)}", exc_info=True)
            return {"EC": 2, "EM": f"Error updating user: {str(e)}", "data": None}


def get_admin_user_service() -> AdminUserService:
    """Dependency to get AdminUserService instance"""
    return AdminUserService()
