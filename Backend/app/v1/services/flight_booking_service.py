"""
Flight Booking Service
Handles flight booking CRUD + OTP verification flow
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
from .otp_service import get_otp_service, get_otp_db_timestamps

logger = logging.getLogger(__name__)


class FlightBookingService:
    """Service for managing flight bookings"""

    def __init__(self):
        self.db_url = settings.DATABASE_URL

    def _get_conn(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    async def create_booking_with_otp(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create flight booking with OTP verification"""
        try:
            flight_id = booking_data['flight_id']
            user_id = str(booking_data['user_id'])
            passenger_email = booking_data.get('passenger_email', '')
            seat_class = booking_data.get('seat_class', 'economy')
            num_passengers = booking_data.get('num_passengers', 1)

            if not passenger_email:
                return {"EC": 1, "EM": "Email là bắt buộc để xác thực OTP", "data": None}

            # Validate seat class
            valid_classes = ['economy', 'business', 'first_class']
            if seat_class not in valid_classes:
                return {"EC": 1, "EM": f"Hạng ghế không hợp lệ. Hợp lệ: {', '.join(valid_classes)}", "data": None}

            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Get flight from database
                    cur.execute(
                        "SELECT * FROM flights WHERE flight_id = %s",
                        (flight_id,)
                    )
                    flight = cur.fetchone()

                    if not flight:
                        return {"EC": 1, "EM": "Không tìm thấy chuyến bay", "data": None}

                    if not flight.get('is_active', True):
                        return {"EC": 2, "EM": "Chuyến bay không còn hoạt động", "data": None}

                    if flight.get('status') not in ('scheduled', None):
                        return {"EC": 2, "EM": f"Chuyến bay không khả dụng (trạng thái: {flight.get('status')})", "data": None}

                    # Get price for selected seat class
                    price_field = f"{seat_class}_price"
                    seat_price = flight.get(price_field)
                    if seat_price is None or seat_price == 0:
                        return {"EC": 3, "EM": f"Hạng ghế {seat_class} không khả dụng cho chuyến bay này", "data": None}

                    # Check seat availability
                    seats_field = f"{seat_class}_seats"
                    available_seats = flight.get(seats_field, 0) or 0
                    if available_seats < num_passengers:
                        return {"EC": 4, "EM": f"Chỉ còn {available_seats} ghế {seat_class} trống", "data": None}

                    total_price = float(seat_price) * num_passengers

                    # Create booking
                    booking_id = f"FLB{uuid.uuid4().hex[:16].upper()}"
                    now = datetime.now(timezone.utc).isoformat()

                    cur.execute(
                        """INSERT INTO flight_bookings
                           (booking_id, flight_id, user_id, passenger_name, passenger_phone,
                            passenger_email, seat_class, num_passengers, total_price,
                            status, payment_status, created_at, updated_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           RETURNING booking_id""",
                        (booking_id, flight_id, user_id, booking_data['passenger_name'],
                         booking_data['passenger_phone'], passenger_email, seat_class,
                         num_passengers, total_price, 'otp_sent', 'unpaid', now, now)
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
                    new_seats = available_seats - num_passengers
                    cur.execute(
                        f"UPDATE flights SET {seats_field} = %s WHERE flight_id = %s",
                        (new_seats, flight_id)
                    )

                    conn.commit()

            # Send OTP email (non-fatal — booking still created even if email fails)
            try:
                otp_service = get_otp_service()
                email_sent = otp_service.send_otp_email(
                    email=passenger_email,
                    otp=otp_code,
                    tour_name=f"Chuyến bay {flight['flight_number']}"
                )
                if not email_sent:
                    logger.warning(f"Failed to send OTP email to {passenger_email}, but booking created.")
            except Exception as email_err:
                logger.warning(f"Email sending failed for {passenger_email}: {email_err}. Booking {booking_id} still created.")

            logger.info(f"Created flight booking {booking_id} with OTP flow")

            return {
                "EC": 0,
                "EM": "Đặt vé thành công. Vui lòng nhập mã OTP để xác nhận.",
                "data": {
                    "booking_id": booking_id,
                    "awaiting_otp": True,
                    "status": "otp_sent",
                    "contact_email": passenger_email,
                    "total_price": total_price,
                    "flight_number": flight['flight_number'],
                    "otp_code": otp_code
                }
            }

        except Exception as e:
            logger.error(f"Error creating flight booking: {str(e)}")
            return {"EC": 7, "EM": f"Lỗi tạo đặt vé: {str(e)}", "data": None}

    async def verify_otp(self, booking_id: str, otp_code: str) -> Dict[str, Any]:
        """Verify OTP for flight booking"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Get booking
                    cur.execute(
                        "SELECT * FROM flight_bookings WHERE booking_id = %s",
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
                        """UPDATE flight_bookings
                           SET status = 'confirmed', payment_status = 'paid', updated_at = %s
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
                "EM": "Xác nhận đặt vé máy bay thành công!",
                "data": {"booking_id": booking_id, "status": "confirmed"}
            }

        except Exception as e:
            logger.error(f"Error verifying flight OTP: {str(e)}")
            return {"EC": 6, "EM": f"Lỗi xác thực: {str(e)}", "data": None}

    async def resend_otp(self, booking_id: str) -> Dict[str, Any]:
        """Resend OTP for flight booking"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Get booking
                    cur.execute(
                        "SELECT * FROM flight_bookings WHERE booking_id = %s",
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

                    # Get flight name for email
                    cur.execute(
                        "SELECT flight_number FROM flights WHERE flight_id = %s",
                        (booking['flight_id'],)
                    )
                    flight_row = cur.fetchone()
                    flight_name = f"Chuyến bay {flight_row['flight_number']}" if flight_row else "Chuyến bay"

                    conn.commit()

            # Send OTP email (non-fatal)
            try:
                otp_service = get_otp_service()
                otp_service.send_otp_email(email=passenger_email, otp=otp_code, tour_name=flight_name)
            except Exception as email_err:
                logger.warning(f"Resend OTP email failed for {passenger_email}: {email_err}")

            return {
                "EC": 0,
                "EM": "Mã OTP mới đã được tạo.",
                "data": {"booking_id": booking_id, "contact_email": passenger_email, "otp_code": otp_code}
            }

        except Exception as e:
            logger.error(f"Error resending flight OTP: {str(e)}")
            return {"EC": 4, "EM": f"Lỗi gửi lại OTP: {str(e)}", "data": None}

    def get_my_bookings(self, user_id: str) -> Dict[str, Any]:
        """Get list of flight bookings for a user"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Get bookings with flight and airline info via JOIN
                    cur.execute("""
                        SELECT
                            fb.booking_id, fb.num_passengers, fb.total_price,
                            fb.status, fb.created_at, fb.seat_class,
                            f.flight_number, f.departure_airport, f.arrival_airport,
                            f.departure_time, f.arrival_time,
                            a.name as airline_name
                        FROM flight_bookings fb
                        LEFT JOIN flights f ON fb.flight_id = f.flight_id
                        LEFT JOIN airlines a ON f.airline_id = a.airline_id
                        WHERE fb.user_id = %s
                        ORDER BY fb.created_at DESC
                    """, (user_id,))
                    rows = cur.fetchall()

                    # Get airport info for city names
                    cur.execute("SELECT airport_id, city FROM airports")
                    airport_map = {r['airport_id']: r['city'] for r in cur.fetchall()}

                    bookings = []
                    for row in rows:
                        bookings.append({
                            "booking_id": row['booking_id'],
                            "flight_number": row.get('flight_number', 'N/A'),
                            "airline_name": row.get('airline_name', 'N/A'),
                            "departure_city": airport_map.get(row.get('departure_airport'), ''),
                            "arrival_city": airport_map.get(row.get('arrival_airport'), ''),
                            "departure_time": str(row['departure_time']) if row.get('departure_time') else '',
                            "seat_class": row['seat_class'],
                            "num_passengers": row['num_passengers'],
                            "total_price": float(row['total_price']),
                            "status": row['status'],
                            "created_at": str(row['created_at']) if row.get('created_at') else ''
                        })

            return {"EC": 0, "EM": "Success", "data": bookings, "total": len(bookings)}

        except Exception as e:
            logger.error(f"Error getting flight bookings: {str(e)}")
            return {"EC": 1, "EM": str(e), "data": None, "total": 0}

    def get_booking_detail(self, booking_id: str, user_id: str) -> Dict[str, Any]:
        """Get detail of a specific flight booking"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT
                            fb.*,
                            f.flight_id as f_flight_id, f.flight_number, f.airline_id,
                            f.departure_airport, f.arrival_airport, f.departure_time,
                            f.arrival_time, f.duration_minutes, f.aircraft,
                            a.name as airline_name, a.logo_url as airline_logo_url
                        FROM flight_bookings fb
                        LEFT JOIN flights f ON fb.flight_id = f.flight_id
                        LEFT JOIN airlines a ON f.airline_id = a.airline_id
                        WHERE fb.booking_id = %s AND fb.user_id = %s
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
                        "seat_class": row['seat_class'],
                        "num_passengers": row['num_passengers'],
                        "total_price": float(row['total_price']),
                        "created_at": str(row['created_at']) if row.get('created_at') else '',
                        "updated_at": str(row['updated_at']) if row.get('updated_at') else '',
                        "flight": {
                            "flight_id": row.get('f_flight_id'),
                            "flight_number": row.get('flight_number'),
                            "airline": {
                                "name": row.get('airline_name', ''),
                                "logo_url": row.get('airline_logo_url', '')
                            },
                            "departure_airport": row.get('departure_airport'),
                            "arrival_airport": row.get('arrival_airport'),
                            "departure_time": str(row['departure_time']) if row.get('departure_time') else '',
                            "arrival_time": str(row['arrival_time']) if row.get('arrival_time') else '',
                            "duration_minutes": row.get('duration_minutes'),
                            "aircraft": row.get('aircraft')
                        } if row.get('f_flight_id') else None
                    }

            return {"EC": 0, "EM": "Success", "data": detail}

        except Exception as e:
            logger.error(f"Error getting flight booking detail: {str(e)}")
            return {"EC": 1, "EM": str(e), "data": None}

    async def cancel_booking(self, booking_id: str, user_id: str, reason: str = None) -> Dict[str, Any]:
        """Cancel a flight booking and restore seats"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM flight_bookings WHERE booking_id = %s AND user_id = %s",
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
                    if reason:
                        cur.execute(
                            "UPDATE flight_bookings SET status = 'cancelled', cancel_reason = %s, updated_at = %s WHERE booking_id = %s",
                            (reason, now, booking_id)
                        )
                    else:
                        cur.execute(
                            "UPDATE flight_bookings SET status = 'cancelled', updated_at = %s WHERE booking_id = %s",
                            (now, booking_id)
                        )

                    # Restore available seats
                    if booking['status'] in ('confirmed', 'otp_sent'):
                        seat_class = booking['seat_class']
                        seats_field = f"{seat_class}_seats"
                        cur.execute(
                            f"SELECT {seats_field} FROM flights WHERE flight_id = %s",
                            (booking['flight_id'],)
                        )
                        flight_row = cur.fetchone()
                        if flight_row:
                            current_seats = flight_row.get(seats_field, 0) or 0
                            cur.execute(
                                f"UPDATE flights SET {seats_field} = %s WHERE flight_id = %s",
                                (current_seats + booking['num_passengers'], booking['flight_id'])
                            )

                    conn.commit()

            return {"EC": 0, "EM": "Hủy đặt vé máy bay thành công", "data": None}

        except Exception as e:
            logger.error(f"Error cancelling flight booking: {str(e)}")
            return {"EC": 3, "EM": str(e), "data": None}


def get_flight_booking_service():
    """Dependency to get FlightBookingService"""
    return FlightBookingService()
