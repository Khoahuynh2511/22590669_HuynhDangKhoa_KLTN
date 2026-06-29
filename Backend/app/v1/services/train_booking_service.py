"""
Train Booking Service
Handles train booking CRUD + OTP verification flow
Uses Render PostgreSQL via psycopg2
"""
import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from ..core.config import settings
from ..core.datetime_utils import to_json_value
from .otp_service import get_otp_service, get_otp_db_timestamps

logger = logging.getLogger(__name__)


class TrainBookingService:
    """Service for managing train bookings"""

    def __init__(self):
        self.db_url = settings.DATABASE_URL

    def _get_conn(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    async def create_booking_with_otp(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create train booking with OTP verification"""
        try:
            train_id = booking_data['train_id']
            user_id = str(booking_data['user_id'])
            passenger_email = booking_data.get('passenger_email', '')
            seat_type_id = booking_data.get('seat_type_id', '')
            num_passengers = booking_data.get('num_passengers', 1)

            if not passenger_email:
                return {"EC": 1, "EM": "Email là bắt buộc để xác thực OTP", "data": None}

            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Get train from database
                    cur.execute(
                        "SELECT * FROM trains WHERE train_id = %s",
                        (train_id,)
                    )
                    train = cur.fetchone()

                    if not train:
                        return {"EC": 1, "EM": "Không tìm thấy chuyến tàu", "data": None}

                    if not train.get('is_active', True):
                        return {"EC": 2, "EM": "Chuyến tàu không còn hoạt động", "data": None}

                    if train.get('status') not in ('scheduled', None):
                        return {"EC": 2, "EM": f"Chuyến tàu không khả dụng (trạng thái: {train.get('status')})", "data": None}

                    # Get seat price and availability
                    cur.execute(
                        "SELECT * FROM train_seat_prices WHERE train_id = %s AND seat_type_id = %s",
                        (train_id, seat_type_id)
                    )
                    seat_price_info = cur.fetchone()

                    if not seat_price_info:
                        return {"EC": 3, "EM": f"Loại ghế {seat_type_id} không khả dụng cho chuyến tàu này", "data": None}

                    unit_price = float(seat_price_info['price'])
                    available_seats = seat_price_info.get('available_seats', 0) or 0

                    if available_seats < num_passengers:
                        return {"EC": 4, "EM": f"Chỉ còn {available_seats} ghế trống cho loại ghế này", "data": None}

                    total_price = unit_price * num_passengers

                    # Get seat type name
                    cur.execute(
                        "SELECT name FROM seat_types WHERE seat_type_id = %s",
                        (seat_type_id,)
                    )
                    seat_type_row = cur.fetchone()
                    seat_type_name = seat_type_row['name'] if seat_type_row else seat_type_id

                    # Create booking
                    booking_id = f"TNB{uuid.uuid4().hex[:16].upper()}"
                    now = datetime.now(timezone.utc).isoformat()
                    selected_seats = booking_data.get('selected_seats', '')

                    cur.execute(
                        """INSERT INTO train_bookings
                           (booking_id, train_id, user_id, passenger_name, passenger_phone,
                            passenger_email, seat_type_id, num_passengers, total_price,
                            status, payment_status, selected_seats, created_at, updated_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           RETURNING booking_id""",
                        (booking_id, train_id, user_id, booking_data['passenger_name'],
                         booking_data['passenger_phone'], passenger_email, seat_type_id,
                         num_passengers, total_price, 'otp_sent', 'unpaid', selected_seats, now, now)
                    )
                    if not cur.fetchone():
                        return {"EC": 5, "EM": "Không thể tạo đặt vé", "data": None}

                    # Generate and store OTP
                    otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                    otp_created_at, otp_expires_at = get_otp_db_timestamps()

                    try:
                        cur.execute(
                            """INSERT INTO otp_verifications
                               (booking_id, otp_code, email, is_verified, expires_at, created_at)
                               VALUES (%s, %s, %s, FALSE, %s, %s)
                               RETURNING otp_id""",
                            (booking_id, otp_code, passenger_email, otp_expires_at, otp_created_at)
                        )
                        if not cur.fetchone():
                            conn.rollback()
                            return {"EC": 6, "EM": "Không thể tạo mã OTP", "data": None}
                    except Exception as e:
                        conn.rollback()
                        return {"EC": 6, "EM": f"Lỗi OTP: {str(e)}", "data": None}

                    # Update available seats
                    new_available = available_seats - num_passengers
                    cur.execute(
                        "UPDATE train_seat_prices SET available_seats = %s WHERE train_id = %s AND seat_type_id = %s",
                        (new_available, train_id, seat_type_id)
                    )

                    conn.commit()

            # Send OTP email (non-fatal — booking still created even if email fails)
            try:
                otp_service = get_otp_service()
                email_sent = otp_service.send_otp_email(
                    email=passenger_email,
                    otp=otp_code,
                    tour_name=f"Tàu {train['train_number']} - {seat_type_name}"
                )
                if not email_sent:
                    logger.warning(f"Failed to send OTP email to {passenger_email}, but booking created.")
            except Exception as email_err:
                logger.warning(f"Email sending failed for {passenger_email}: {email_err}. Booking {booking_id} still created.")

            logger.info(f"Created train booking {booking_id} with OTP flow")

            return {
                "EC": 0,
                "EM": "Đặt vé thành công. Vui lòng nhập mã OTP để xác nhận.",
                "data": {
                    "booking_id": booking_id,
                    "awaiting_otp": True,
                    "status": "otp_sent",
                    "contact_email": passenger_email,
                    "total_price": total_price,
                    "train_number": train['train_number'],
                    "seat_type_name": seat_type_name,
                    **({"otp_code": otp_code} if settings.OTP_SHOW_IN_RESPONSE else {})
                }
            }

        except Exception as e:
            logger.error(f"Error creating train booking: {str(e)}")
            return {"EC": 7, "EM": f"Lỗi tạo đặt vé: {str(e)}", "data": None}

    async def verify_otp(self, booking_id: str, otp_code: str) -> Dict[str, Any]:
        """Verify OTP for train booking"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Get booking
                    cur.execute(
                        "SELECT * FROM train_bookings WHERE booking_id = %s",
                        (booking_id,)
                    )
                    booking = cur.fetchone()

                    if not booking:
                        return {"EC": 1, "EM": "Không tìm thấy đặt vé", "data": None}

                    if booking['status'] != 'otp_sent':
                        return {"EC": 2, "EM": f"Đặt vé đã ở trạng thái: {booking['status']}", "data": None}

                    # Get latest OTP
                    cur.execute(
                        """SELECT * FROM otp_verifications
                           WHERE booking_id = %s
                           ORDER BY created_at DESC LIMIT 1""",
                        (booking_id,)
                    )
                    otp_record = cur.fetchone()

                    if not otp_record:
                        return {"EC": 3, "EM": "Không tìm thấy mã OTP", "data": None}

                    if otp_record['otp_code'] != otp_code:
                        return {"EC": 4, "EM": "Mã OTP không đúng", "data": None}

                    # Check expiry
                    expires_at = otp_record.get('expires_at')
                    if expires_at:
                        if isinstance(expires_at, str):
                            expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                        elif expires_at.tzinfo is None:
                            expires_at = expires_at.replace(tzinfo=timezone.utc)
                        if datetime.now(timezone.utc) > expires_at:
                            return {"EC": 5, "EM": "Mã OTP đã hết hạn (5 phút)", "data": None}

                    # Update booking status
                    now = datetime.now(timezone.utc).isoformat()
                    cur.execute(
                        """UPDATE train_bookings
                           SET status = 'pending', payment_status = 'unpaid', updated_at = %s
                           WHERE booking_id = %s""",
                        (now, booking_id)
                    )

                    # Mark OTP as verified
                    cur.execute(
                        "UPDATE otp_verifications SET is_verified = TRUE WHERE otp_id = %s",
                        (otp_record['otp_id'],)
                    )

                    conn.commit()

            return {
                "EC": 0,
                "EM": "Xác nhận đặt vé tàu thành công!",
                "data": {"booking_id": booking_id, "status": "confirmed"}
            }

        except Exception as e:
            logger.error(f"Error verifying train OTP: {str(e)}")
            return {"EC": 6, "EM": f"Lỗi xác thực: {str(e)}", "data": None}

    async def resend_otp(self, booking_id: str) -> Dict[str, Any]:
        """Resend OTP for train booking"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Get booking
                    cur.execute(
                        "SELECT * FROM train_bookings WHERE booking_id = %s",
                        (booking_id,)
                    )
                    booking = cur.fetchone()

                    if not booking:
                        return {"EC": 1, "EM": "Không tìm thấy đặt vé", "data": None}

                    if booking['status'] != 'otp_sent':
                        return {"EC": 2, "EM": "Đặt vé không cần xác thực OTP", "data": None}

                    passenger_email = booking.get('passenger_email')
                    if not passenger_email:
                        return {"EC": 3, "EM": "Không có email liên hệ", "data": None}

                    # Generate new OTP
                    otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                    otp_created_at, otp_expires_at = get_otp_db_timestamps()
                    cur.execute(
                        """INSERT INTO otp_verifications
                           (booking_id, otp_code, email, is_verified, expires_at, created_at)
                           VALUES (%s, %s, %s, FALSE, %s, %s)""",
                        (booking_id, otp_code, passenger_email, otp_expires_at, otp_created_at)
                    )

                    # Get train name for email
                    cur.execute(
                        "SELECT train_number FROM trains WHERE train_id = %s",
                        (booking['train_id'],)
                    )
                    train_row = cur.fetchone()
                    train_name = f"Tàu {train_row['train_number']}" if train_row else "Tàu hỏa"

                    conn.commit()

            # Send OTP email (non-fatal)
            try:
                otp_service = get_otp_service()
                otp_service.send_otp_email(email=passenger_email, otp=otp_code, tour_name=train_name)
            except Exception as email_err:
                logger.warning(f"Resend OTP email failed for {passenger_email}: {email_err}")

            return {
                "EC": 0,
                "EM": "Mã OTP mới đã được tạo.",
                "data": {"booking_id": booking_id, "contact_email": passenger_email, **({"otp_code": otp_code} if settings.OTP_SHOW_IN_RESPONSE else {})}
            }

        except Exception as e:
            logger.error(f"Error resending train OTP: {str(e)}")
            return {"EC": 4, "EM": f"Lỗi gửi lại OTP: {str(e)}", "data": None}

    def get_my_bookings(self, user_id: str) -> Dict[str, Any]:
        """Get list of train bookings for a user"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Get bookings with train and seat type info via JOIN
                    cur.execute("""
                        SELECT
                            tb.booking_id, tb.num_passengers, tb.total_price,
                            tb.status, tb.payment_status, tb.created_at, tb.seat_type_id,
                            t.train_number, t.departure_station, t.arrival_station, t.departure_time,
                            st.name as seat_type_name
                        FROM train_bookings tb
                        LEFT JOIN trains t ON tb.train_id = t.train_id
                        LEFT JOIN seat_types st ON tb.seat_type_id = st.seat_type_id
                        WHERE tb.user_id = %s
                        ORDER BY tb.created_at DESC
                    """, (user_id,))
                    rows = cur.fetchall()

                    # Get station info for city names
                    cur.execute("SELECT station_id, city FROM train_stations")
                    station_map = {r['station_id']: r['city'] for r in cur.fetchall()}

                    bookings = []
                    for row in rows:
                        bookings.append({
                            "booking_id": row['booking_id'],
                            "train_number": row.get('train_number', 'N/A'),
                            "departure_city": station_map.get(row.get('departure_station'), ''),
                            "arrival_city": station_map.get(row.get('arrival_station'), ''),
                            "departure_time": to_json_value(row.get('departure_time')) or '',
                            "seat_type": row.get('seat_type_name', row.get('seat_type_id', '')),
                            "num_passengers": row['num_passengers'],
                            "total_price": float(row['total_price']),
                            "status": row['status'],
                            "payment_status": row.get('payment_status', 'unpaid'),
                            "created_at": to_json_value(row.get('created_at')) or ''
                        })

            return {"EC": 0, "EM": "Success", "data": bookings, "total": len(bookings)}

        except Exception as e:
            logger.error(f"Error getting train bookings: {str(e)}")
            return {"EC": 1, "EM": str(e), "data": None, "total": 0}

    def get_booking_detail(self, booking_id: str, user_id: str) -> Dict[str, Any]:
        """Get detail of a specific train booking"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT
                            tb.*,
                            t.train_id as t_train_id, t.train_number, t.departure_station,
                            t.arrival_station, t.departure_time, t.arrival_time,
                            t.duration_hours, t.train_type_id,
                            tt.name as train_type_name,
                            st.name as seat_type_name
                        FROM train_bookings tb
                        LEFT JOIN trains t ON tb.train_id = t.train_id
                        LEFT JOIN train_types tt ON t.train_type_id = tt.type_id
                        LEFT JOIN seat_types st ON tb.seat_type_id = st.seat_type_id
                        WHERE tb.booking_id = %s AND tb.user_id = %s
                    """, (booking_id, user_id))
                    row = cur.fetchone()

                    if not row:
                        return {"EC": 1, "EM": "Không tìm thấy đặt vé", "data": None}

                    detail = {
                        "booking_id": row['booking_id'],
                        "status": row['status'],
                        "passenger_name": row['passenger_name'],
                        "passenger_phone": row['passenger_phone'],
                        "passenger_email": row.get('passenger_email'),
                        "seat_type": row.get('seat_type_name', row.get('seat_type_id', '')),
                        "num_passengers": row['num_passengers'],
                        "total_price": float(row['total_price']),
                        "selected_seats": row.get('selected_seats', ''),
                        "payment_status": row.get('payment_status', 'unpaid'),
                        "created_at": str(row['created_at']) if row.get('created_at') else '',
                        "updated_at": str(row['updated_at']) if row.get('updated_at') else '',
                        "train": {
                            "train_id": row.get('t_train_id'),
                            "train_number": row.get('train_number'),
                            "train_type": {"name": row.get('train_type_name', '')},
                            "departure_station": row.get('departure_station'),
                            "arrival_station": row.get('arrival_station'),
                            "departure_time": str(row['departure_time']) if row.get('departure_time') else '',
                            "arrival_time": str(row['arrival_time']) if row.get('arrival_time') else '',
                            "duration_hours": float(row['duration_hours']) if row.get('duration_hours') else 0
                        } if row.get('t_train_id') else None
                    }

            return {"EC": 0, "EM": "Success", "data": detail}

        except Exception as e:
            logger.error(f"Error getting train booking detail: {str(e)}")
            return {"EC": 1, "EM": str(e), "data": None}

    async def cancel_booking(self, booking_id: str, user_id: str, reason: str = None) -> Dict[str, Any]:
        """Cancel a train booking and restore seats"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM train_bookings WHERE booking_id = %s AND user_id = %s",
                        (booking_id, user_id)
                    )
                    booking = cur.fetchone()

                    if not booking:
                        return {"EC": 1, "EM": "Không tìm thấy đặt vé", "data": None}

                    if booking['status'] == 'cancelled':
                        return {"EC": 2, "EM": "Đặt vé đã bị hủy trước đó", "data": None}

                    if booking['status'] == 'completed':
                        return {"EC": 2, "EM": "Không thể hủy đặt vé đã hoàn thành", "data": None}

                    now = datetime.now(timezone.utc).isoformat()
                    cur.execute(
                        "UPDATE train_bookings SET status = 'cancelled', updated_at = %s WHERE booking_id = %s",
                        (now, booking_id)
                    )

                    # Restore available seats
                    if booking['status'] in ('confirmed', 'otp_sent'):
                        cur.execute(
                            """SELECT available_seats FROM train_seat_prices
                               WHERE train_id = %s AND seat_type_id = %s""",
                            (booking['train_id'], booking['seat_type_id'])
                        )
                        seat_row = cur.fetchone()
                        if seat_row:
                            current = seat_row.get('available_seats', 0) or 0
                            cur.execute(
                                """UPDATE train_seat_prices SET available_seats = %s
                                   WHERE train_id = %s AND seat_type_id = %s""",
                                (current + booking['num_passengers'],
                                 booking['train_id'], booking['seat_type_id'])
                            )

                    conn.commit()

            return {"EC": 0, "EM": "Hủy đặt vé tàu thành công", "data": None}

        except Exception as e:
            logger.error(f"Error cancelling train booking: {str(e)}")
            return {"EC": 3, "EM": str(e), "data": None}

    def get_occupied_seats(self, train_id: str) -> Dict[str, Any]:
        """Get list of occupied seats for a specific train"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT selected_seats FROM train_bookings WHERE train_id = %s AND status != 'cancelled' AND selected_seats IS NOT NULL",
                        (train_id,)
                    )
                    rows = cur.fetchall()
                    occupied = []
                    for row in rows:
                        seats_str = row.get('selected_seats', '')
                        if seats_str:
                            occupied.extend([s.strip() for s in seats_str.split(',') if s.strip()])
            return {"EC": 0, "EM": "Success", "data": list(set(occupied))}
        except Exception as e:
            logger.error(f"Error getting occupied seats for train {train_id}: {str(e)}")
            return {"EC": 1, "EM": str(e), "data": []}



def get_train_booking_service():
    """Dependency to get TrainBookingService"""
    return TrainBookingService()
