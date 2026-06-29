"""
Hotel Booking Service
Handles hotel booking CRUD + OTP verification flow
Uses Render PostgreSQL via psycopg2
"""
import logging
import random
import uuid
from datetime import datetime, timezone, date
from typing import Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from ..core.config import settings
from ..core.datetime_utils import to_json_value
from .otp_service import get_otp_service, get_otp_db_timestamps

logger = logging.getLogger(__name__)


class HotelBookingService:
    """Service for managing hotel bookings"""

    def __init__(self):
        self.db_url = settings.DATABASE_URL

    def _get_conn(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    async def create_booking_with_otp(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create hotel booking with OTP verification"""
        try:
            hotel_id = str(booking_data['hotel_id'])
            user_id = str(booking_data['user_id'])
            check_in = booking_data['check_in']
            check_out = booking_data['check_out']
            num_rooms = booking_data.get('num_rooms', 1)
            num_guests = booking_data.get('num_guests', 1)
            guest_email = booking_data.get('guest_email', '')

            if not guest_email:
                return {"EC": 1, "EM": "Email là bắt buộc để xác thực OTP", "data": None}

            # Validate dates
            if isinstance(check_in, str):
                check_in = date.fromisoformat(check_in)
            if isinstance(check_out, str):
                check_out = date.fromisoformat(check_out)

            if check_in <= date.today():
                return {"EC": 2, "EM": "Ngày nhận phòng phải từ ngày mai trở đi", "data": None}
            if check_out <= check_in:
                return {"EC": 2, "EM": "Ngày trả phòng phải sau ngày nhận phòng", "data": None}

            nights = (check_out - check_in).days

            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Verify hotel exists and has rooms
                    cur.execute(
                        "SELECT available_rooms, is_active, price, hotel_name, image_urls FROM hotels WHERE hotel_id = %s",
                        (hotel_id,)
                    )
                    hotel = cur.fetchone()

                    if not hotel:
                        return {"EC": 1, "EM": "Không tìm thấy khách sạn", "data": None}

                    if not hotel.get('is_active', True):
                        return {"EC": 2, "EM": "Khách sạn hiện không hoạt động", "data": None}

                    if hotel.get('available_rooms', 0) < num_rooms:
                        return {"EC": 3, "EM": f"Chỉ còn {hotel.get('available_rooms', 0)} phòng trống", "data": None}

                    # Calculate total price
                    total_price = float(hotel['price']) * nights * num_rooms

                    # Create booking
                    booking_id = f"HTB{uuid.uuid4().hex[:16].upper()}"
                    now = datetime.now(timezone.utc).isoformat()

                    cur.execute(
                        """INSERT INTO hotel_bookings
                           (booking_id, hotel_id, user_id, check_in, check_out, num_rooms, num_guests,
                            total_price, guest_name, guest_phone, guest_email, special_requests,
                            status, payment_status, created_at, updated_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           RETURNING booking_id""",
                        (booking_id, hotel_id, user_id, check_in.isoformat(), check_out.isoformat(),
                         num_rooms, num_guests, total_price, booking_data['guest_name'],
                         booking_data['guest_phone'], guest_email, booking_data.get('special_requests'),
                         'otp_sent', 'unpaid', now, now)
                    )

                    if not cur.fetchone():
                        return {"EC": 4, "EM": "Không thể tạo đặt phòng", "data": None}

                    # Generate and store OTP
                    otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                    otp_created_at, otp_expires_at = get_otp_db_timestamps()

                    try:
                        cur.execute(
                            """INSERT INTO otp_verifications
                               (booking_id, otp_code, email, is_verified, expires_at, created_at)
                               VALUES (%s, %s, %s, FALSE, %s, %s)
                               RETURNING otp_id""",
                            (booking_id, otp_code, guest_email, otp_expires_at, otp_created_at)
                        )
                        if not cur.fetchone():
                            conn.rollback()
                            return {"EC": 5, "EM": "Không thể tạo mã OTP", "data": None}
                    except Exception as e:
                        conn.rollback()
                        return {"EC": 5, "EM": f"Lỗi OTP: {str(e)}", "data": None}

                    # Update available rooms
                    new_rooms = hotel.get('available_rooms', 0) - num_rooms
                    cur.execute(
                        "UPDATE hotels SET available_rooms = %s WHERE hotel_id = %s",
                        (new_rooms, hotel_id)
                    )

                    conn.commit()

            # Send OTP email (non-fatal — booking still created even if email fails)
            try:
                otp_service = get_otp_service()
                email_sent = otp_service.send_otp_email(
                    email=guest_email,
                    otp=otp_code,
                    tour_name=f"Khách sạn {hotel['hotel_name']}"  # reuse OTP template
                )
                if not email_sent:
                    logger.warning(f"Failed to send OTP email to {guest_email}, but booking created.")
            except Exception as email_err:
                logger.warning(f"Email sending failed for {guest_email}: {email_err}. Booking {booking_id} still created.")

            logger.info(f"Created hotel booking {booking_id} with OTP flow")

            return {
                "EC": 0,
                "EM": "Đặt phòng thành công. Vui lòng nhập mã OTP để xác nhận.",
                "data": {
                    "booking_id": booking_id,
                    "awaiting_otp": True,
                    "status": "otp_sent",
                    "contact_email": guest_email,
                    "total_price": total_price,
                    "nights": nights,
                    "hotel_name": hotel['hotel_name'],
                    **({"otp_code": otp_code} if settings.OTP_SHOW_IN_RESPONSE else {})
                }
            }

        except Exception as e:
            logger.error(f"Error creating hotel booking: {str(e)}")
            return {"EC": 6, "EM": f"Lỗi tạo đặt phòng: {str(e)}", "data": None}

    async def verify_otp(self, booking_id: str, otp_code: str) -> Dict[str, Any]:
        """Verify OTP for hotel booking"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Get booking
                    cur.execute(
                        "SELECT * FROM hotel_bookings WHERE booking_id = %s",
                        (booking_id,)
                    )
                    booking = cur.fetchone()

                    if not booking:
                        return {"EC": 1, "EM": "Không tìm thấy đặt phòng", "data": None}

                    if booking['status'] != 'otp_sent':
                        return {"EC": 2, "EM": f"Đặt phòng đã ở trạng thái: {booking['status']}", "data": None}

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
                        """UPDATE hotel_bookings
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
                "EM": "Xác nhận đặt phòng thành công!",
                "data": {"booking_id": booking_id, "status": "confirmed"}
            }

        except Exception as e:
            logger.error(f"Error verifying hotel OTP: {str(e)}")
            return {"EC": 6, "EM": f"Lỗi xác thực: {str(e)}", "data": None}

    async def resend_otp(self, booking_id: str) -> Dict[str, Any]:
        """Resend OTP for hotel booking"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Get booking
                    cur.execute(
                        "SELECT * FROM hotel_bookings WHERE booking_id = %s",
                        (booking_id,)
                    )
                    booking = cur.fetchone()

                    if not booking:
                        return {"EC": 1, "EM": "Không tìm thấy đặt phòng", "data": None}

                    if booking['status'] != 'otp_sent':
                        return {"EC": 2, "EM": "Đặt phòng không cần xác thực OTP", "data": None}

                    guest_email = booking.get('guest_email')
                    if not guest_email:
                        return {"EC": 3, "EM": "Không có email liên hệ", "data": None}

                    # Get hotel name for email
                    cur.execute(
                        "SELECT hotel_name FROM hotels WHERE hotel_id = %s",
                        (booking['hotel_id'],)
                    )
                    hotel_row = cur.fetchone()
                    hotel_name = f"Khách sạn {hotel_row['hotel_name']}" if hotel_row else "Khách sạn"

                    # Generate new OTP
                    otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                    otp_created_at, otp_expires_at = get_otp_db_timestamps()
                    cur.execute(
                        """INSERT INTO otp_verifications
                           (booking_id, otp_code, email, is_verified, expires_at, created_at)
                           VALUES (%s, %s, %s, FALSE, %s, %s)""",
                        (booking_id, otp_code, guest_email, otp_expires_at, otp_created_at)
                    )

                    conn.commit()

            # Send OTP email (non-fatal)
            try:
                otp_service = get_otp_service()
                otp_service.send_otp_email(email=guest_email, otp=otp_code, tour_name=hotel_name)
            except Exception as email_err:
                logger.warning(f"Resend OTP email failed for {guest_email}: {email_err}")

            return {
                "EC": 0,
                "EM": "Mã OTP mới đã được tạo.",
                "data": {"booking_id": booking_id, "contact_email": guest_email, **({"otp_code": otp_code} if settings.OTP_SHOW_IN_RESPONSE else {})}
            }

        except Exception as e:
            logger.error(f"Error resending hotel OTP: {str(e)}")
            return {"EC": 4, "EM": f"Lỗi gửi lại OTP: {str(e)}", "data": None}

    def get_my_bookings(self, user_id: str) -> Dict[str, Any]:
        """Get list of hotel bookings for a user"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Get bookings with hotel info via JOIN
                    cur.execute("""
                        SELECT
                            hb.booking_id, hb.check_in, hb.check_out, hb.num_rooms,
                            hb.num_guests, hb.total_price, hb.status, hb.created_at,
                            h.hotel_name, h.location, h.image_urls, h.price, h.star_rating
                        FROM hotel_bookings hb
                        LEFT JOIN hotels h ON hb.hotel_id = h.hotel_id
                        WHERE hb.user_id = %s
                        ORDER BY hb.created_at DESC
                    """, (user_id,))
                    rows = cur.fetchall()

                    bookings = []
                    for row in rows:
                        bookings.append({
                            "booking_id": row['booking_id'],
                            "hotel_name": row.get('hotel_name', 'N/A'),
                            "location": row.get('location', ''),
                            "check_in": to_json_value(row.get('check_in')),
                            "check_out": to_json_value(row.get('check_out')),
                            "num_rooms": row['num_rooms'],
                            "num_guests": row['num_guests'],
                            "total_price": float(row['total_price']),
                            "status": row['status'],
                            "image_urls": row.get('image_urls'),
                            "created_at": to_json_value(row.get('created_at'))
                        })

            return {"EC": 0, "EM": "Success", "data": bookings, "total": len(bookings)}

        except Exception as e:
            logger.error(f"Error getting hotel bookings: {str(e)}")
            return {"EC": 1, "EM": str(e), "data": None, "total": 0}

    def get_booking_detail(self, booking_id: str, user_id: str) -> Dict[str, Any]:
        """Get detail of a specific hotel booking"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT
                            hb.*,
                            h.hotel_id as h_hotel_id, h.hotel_name, h.location, h.star_rating,
                            h.image_urls, h.price, h.address
                        FROM hotel_bookings hb
                        LEFT JOIN hotels h ON hb.hotel_id = h.hotel_id
                        WHERE hb.booking_id = %s AND hb.user_id = %s
                    """, (booking_id, user_id))
                    row = cur.fetchone()

                    if not row:
                        return {"EC": 1, "EM": "Không tìm thấy đặt phòng", "data": None}

                    detail = {
                        "booking_id": row['booking_id'],
                        "status": row['status'],
                        "check_in": row['check_in'],
                        "check_out": row['check_out'],
                        "num_rooms": row['num_rooms'],
                        "num_guests": row['num_guests'],
                        "total_price": float(row['total_price']),
                        "guest_name": row['guest_name'],
                        "guest_phone": row['guest_phone'],
                        "guest_email": row.get('guest_email'),
                        "special_requests": row.get('special_requests'),
                        "created_at": row['created_at'],
                        "updated_at": row['updated_at'],
                        "hotel": {
                            "hotel_id": row.get('h_hotel_id'),
                            "hotel_name": row.get('hotel_name', ''),
                            "location": row.get('location', ''),
                            "star_rating": float(row.get('star_rating', 0)) if row.get('star_rating') else 0,
                            "image_urls": row.get('image_urls'),
                            "price": float(row.get('price', 0)) if row.get('price') else 0,
                            "address": row.get('address', '')
                        } if row.get('h_hotel_id') else None
                    }

            return {"EC": 0, "EM": "Success", "data": detail}

        except Exception as e:
            logger.error(f"Error getting hotel booking detail: {str(e)}")
            return {"EC": 1, "EM": str(e), "data": None}

    async def cancel_booking(self, booking_id: str, user_id: str, reason: str = None) -> Dict[str, Any]:
        """Cancel a hotel booking and restore room availability"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM hotel_bookings WHERE booking_id = %s AND user_id = %s",
                        (booking_id, user_id)
                    )
                    booking = cur.fetchone()

                    if not booking:
                        return {"EC": 1, "EM": "Không tìm thấy đặt phòng", "data": None}

                    if booking['status'] == 'cancelled':
                        return {"EC": 2, "EM": "Đặt phòng đã bị hủy trước đó", "data": None}

                    if booking['status'] == 'completed':
                        return {"EC": 2, "EM": "Không thể hủy đặt phòng đã hoàn thành", "data": None}

                    now = datetime.now(timezone.utc).isoformat()
                    cur.execute(
                        "UPDATE hotel_bookings SET status = 'cancelled', updated_at = %s WHERE booking_id = %s",
                        (now, booking_id)
                    )

                    # Restore available rooms
                    if booking['status'] in ('confirmed', 'otp_sent'):
                        cur.execute(
                            "SELECT available_rooms FROM hotels WHERE hotel_id = %s",
                            (booking['hotel_id'],)
                        )
                        hotel_row = cur.fetchone()
                        if hotel_row:
                            current = hotel_row.get('available_rooms', 0) or 0
                            cur.execute(
                                "UPDATE hotels SET available_rooms = %s WHERE hotel_id = %s",
                                (current + booking['num_rooms'], booking['hotel_id'])
                            )

                    conn.commit()

            return {"EC": 0, "EM": "Hủy đặt phòng thành công", "data": None}

        except Exception as e:
            logger.error(f"Error cancelling hotel booking: {str(e)}")
            return {"EC": 3, "EM": str(e), "data": None}


def get_hotel_booking_service():
    """Dependency to get HotelBookingService"""
    return HotelBookingService()
