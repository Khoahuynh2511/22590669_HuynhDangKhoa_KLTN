"""
Booking Service
Handles booking CRUD operations
"""
import logging
import random
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from ..core.config import settings
from .promotion_service import PromotionService
from .otp_service import get_otp_service, get_otp_db_timestamps

logger = logging.getLogger(__name__)


class BookingService:
    """Service for managing tour bookings"""

    def __init__(self):
        """Initialize BookingService"""
        self.db_url = settings.DATABASE_URL
        self.promotion_service = PromotionService()

    def _get_conn(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    def _normalize(self, rows):
        """Normalize rows to list of dicts"""
        return [dict(r) for r in rows]

    async def get_all_bookings(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get all bookings with optional filters

        Args:
            user_id: Filter by user ID
            status: Filter by booking status
            limit: Maximum number of results
            offset: Number of records to skip

        Returns:
            Dict with EC, EM, data, and total
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Build query
                    query = "SELECT * FROM bookings WHERE 1=1"
                    params = []

                    # Apply filters
                    if user_id:
                        query += " AND user_id = %s"
                        params.append(user_id)
                    if status:
                        query += " AND status = %s"
                        params.append(status)

                    # Count total
                    count_query = "SELECT COUNT(*) as total FROM bookings WHERE 1=1"
                    count_params = []
                    if user_id:
                        count_query += " AND user_id = %s"
                        count_params.append(user_id)
                    if status:
                        count_query += " AND status = %s"
                        count_params.append(status)

                    # Add ordering and pagination
                    query += " ORDER BY created_at DESC"
                    if limit:
                        query += " LIMIT %s"
                        params.append(limit)
                    if offset:
                        query += " OFFSET %s"
                        params.append(offset)

                    # Execute count query
                    cur.execute(count_query, count_params)
                    total = cur.fetchone()['total']

                    # Execute main query
                    cur.execute(query, params)
                    data = self._normalize(cur.fetchall())

                    return {
                        "EC": 0,
                        "EM": "Success",
                        "data": data,
                        "total": total
                    }

        except Exception as e:
            logger.error(f"Error getting bookings: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error retrieving bookings: {str(e)}",
                "data": None,
                "total": 0
            }

    async def get_booking_by_id(self, booking_id: str) -> Dict[str, Any]:
        """
        Get booking by ID

        Args:
            booking_id: UUID of the booking

        Returns:
            Dict with EC, EM, and data
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM bookings WHERE booking_id = %s",
                        (booking_id,)
                    )
                    result = cur.fetchone()

                    if not result:
                        return {
                            "EC": 1,
                            "EM": "Booking not found",
                            "data": None
                        }

                    return {
                        "EC": 0,
                        "EM": "Success",
                        "data": dict(result)
                    }

        except Exception as e:
            logger.error(f"Error getting booking {booking_id}: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error retrieving booking: {str(e)}",
                "data": None
            }

    async def create_booking(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new booking

        Args:
            booking_data: Dictionary containing booking information
                - package_id: UUID
                - user_id: UUID
                - number_of_people: int
                - contact_name: str
                - contact_phone: str
                - special_requests: Optional[str]
                - promotion_id: Optional[UUID] - Mã khuyến mãi

        Returns:
            Dict with EC, EM, and data
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Verify package exists, has available slots, and get price
                    cur.execute(
                        "SELECT available_slots, is_active, price FROM tour_packages WHERE package_id = %s",
                        (str(booking_data['package_id']),)
                    )
                    package_result = cur.fetchone()

                    if not package_result:
                        return {
                            "EC": 1,
                            "EM": "Tour package not found",
                            "data": None
                        }

                    package = dict(package_result)

                    if not package['is_active']:
                        return {
                            "EC": 2,
                            "EM": "Tour package is not active",
                            "data": None
                        }

                    if package['available_slots'] < booking_data['number_of_people']:
                        return {
                            "EC": 3,
                            "EM": f"Not enough slots available. Only {package['available_slots']} slots left",
                            "data": None
                        }

                    # Calculate original total amount
                    original_amount = package['price'] * booking_data['number_of_people']
                    final_amount = original_amount
                    discount_amount = 0
                    promotion_id = booking_data.get('promotion_id')
                    promotion_code = booking_data.get('promotion_code')

                    # Resolve promotion: prioritize code over id
                    if promotion_code:
                        # Get promotion by code
                        promo_lookup = await self.promotion_service.get_promotion_by_code(promotion_code)
                        if promo_lookup['EC'] == 0:
                            promotion_id = promo_lookup['promotion']['promotion_id']
                            logger.info(f"Resolved promotion code {promotion_code} to ID {promotion_id}")
                        else:
                            logger.warning(f"Invalid promotion code: {promotion_code}")
                            promotion_id = None

                    # Apply promotion if we have a valid ID
                    if promotion_id:
                        promo_result = await self.promotion_service.apply_promotion_to_booking(
                            str(promotion_id),
                            original_amount
                        )

                        if promo_result['EC'] == 0:
                            # Promotion applied successfully
                            final_amount = promo_result['final_price']
                            discount_amount = promo_result['discount_amount']
                            logger.info(f"Applied promotion {promotion_id}: {original_amount} -> {final_amount}")
                        else:
                            # Promotion failed, log warning but continue with original price
                            logger.warning(f"Could not apply promotion {promotion_id}: {promo_result['EM']}")
                            promotion_id = None  # Don't save invalid promotion

                    # Prepare booking data
                    now = datetime.now(timezone.utc)
                    booking_insert = {
                        "package_id": str(booking_data['package_id']),
                        "number_of_people": booking_data['number_of_people'],
                        "total_amount": final_amount,  # Giá sau khi áp dụng khuyến mãi
                        "contact_name": booking_data['contact_name'],
                        "contact_phone": booking_data['contact_phone'],
                        "special_requests": booking_data.get('special_requests'),
                        "user_id": str(booking_data['user_id']),
                        "status": booking_data.get("status", "pending"),  # Allow custom status
                        "created_at": now,
                        "updated_at": now
                    }

                    # Add promotion_id if applied successfully
                    if promotion_id:
                        booking_insert["promotion_id"] = str(promotion_id)

                    # Insert booking
                    cur.execute(
                        """INSERT INTO bookings
                           (package_id, number_of_people, total_amount, contact_name,
                            contact_phone, special_requests, user_id, status,
                            created_at, updated_at, promotion_id)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           RETURNING *""",
                        (
                            booking_insert['package_id'],
                            booking_insert['number_of_people'],
                            booking_insert['total_amount'],
                            booking_insert['contact_name'],
                            booking_insert['contact_phone'],
                            booking_insert['special_requests'],
                            booking_insert['user_id'],
                            booking_insert['status'],
                            booking_insert['created_at'],
                            booking_insert['updated_at'],
                            booking_insert.get('promotion_id')
                        )
                    )
                    result = cur.fetchone()
                    conn.commit()

                    if not result:
                        return {
                            "EC": 4,
                            "EM": "Failed to create booking",
                            "data": None
                        }

                    # Update available slots
                    new_slots = package['available_slots'] - booking_data['number_of_people']
                    cur.execute(
                        "UPDATE tour_packages SET available_slots = %s WHERE package_id = %s",
                        (new_slots, str(booking_data['package_id']))
                    )
                    conn.commit()

                    logger.info(
                        f"Created booking {result['booking_id']} (Original: {original_amount}, Final: {final_amount}, Discount: {discount_amount})")

                    return {
                        "EC": 0,
                        "EM": "Booking created successfully",
                        "data": dict(result)
                    }

        except Exception as e:
            logger.error(f"Error creating booking: {str(e)}")
            return {
                "EC": 5,
                "EM": f"Error creating booking: {str(e)}",
                "data": None
            }

    async def update_booking(
        self,
        booking_id: str,
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update booking information

        Args:
            booking_id: UUID of the booking
            update_data: Dictionary containing fields to update

        Returns:
            Dict with EC, EM, and data
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Check if booking exists
                    existing = await self.get_booking_by_id(booking_id)
                    if existing["EC"] != 0:
                        return existing

                    old_booking = existing["data"]

                    # Get package info for price calculation
                    cur.execute(
                        "SELECT available_slots, price FROM tour_packages WHERE package_id = %s",
                        (old_booking['package_id'],)
                    )
                    package_result = cur.fetchone()

                    if not package_result:
                        return {
                            "EC": 1,
                            "EM": "Tour package not found",
                            "data": None
                        }

                    package = dict(package_result)

                    # Handle number_of_people change (update available slots)
                    if "number_of_people" in update_data:
                        old_people = old_booking['number_of_people']
                        new_people = update_data['number_of_people']
                        people_diff = new_people - old_people

                        if people_diff != 0:
                            current_slots = package['available_slots']

                            if people_diff > 0 and current_slots < people_diff:
                                return {
                                    "EC": 1,
                                    "EM": f"Not enough slots. Only {current_slots} available",
                                    "data": None
                                }

                            # Update package slots
                            new_slots = current_slots - people_diff
                            cur.execute(
                                "UPDATE tour_packages SET available_slots = %s WHERE package_id = %s",
                                (new_slots, old_booking['package_id'])
                            )
                            conn.commit()

                    # Recalculate total_amount if number_of_people or promotion_id/code changed
                    if "number_of_people" in update_data or "promotion_id" in update_data or "promotion_code" in update_data:
                        # Get the final number of people (new or old)
                        final_people = update_data.get('number_of_people', old_booking['number_of_people'])

                        # Calculate original amount
                        original_amount = package['price'] * final_people
                        final_amount = original_amount

                        # Resolve promotion: prioritize code over id
                        promotion_id = None
                        promotion_code = update_data.get('promotion_code')

                        if promotion_code:
                            # Get promotion by code
                            promo_lookup = await self.promotion_service.get_promotion_by_code(promotion_code)
                            if promo_lookup['EC'] == 0:
                                promotion_id = promo_lookup['promotion']['promotion_id']
                                logger.info(f"Resolved promotion code {promotion_code} to ID {promotion_id}")
                                update_data['promotion_id'] = str(promotion_id)
                            else:
                                logger.warning(f"Invalid promotion code: {promotion_code}")
                                promotion_id = None
                            # Remove promotion_code from update_data (not a DB column)
                            del update_data['promotion_code']
                        elif "promotion_id" in update_data:
                            # Use promotion_id directly
                            promotion_id = update_data.get('promotion_id')
                            # If explicitly setting promotion_id to None, remove discount
                            if promotion_id is None:
                                update_data['promotion_id'] = None
                            else:
                                # Convert UUID to string for database
                                update_data['promotion_id'] = str(promotion_id)
                        else:
                            # Keep old promotion if neither code nor id provided
                            promotion_id = old_booking.get('promotion_id')

                        # Apply promotion if exists
                        if promotion_id:
                            promo_result = await self.promotion_service.apply_promotion_to_booking(
                                str(promotion_id),
                                original_amount
                            )

                            if promo_result['EC'] == 0:
                                final_amount = promo_result['final_price']
                                logger.info(
                                    f"Applied promotion {promotion_id} to booking {booking_id}: {original_amount} -> {final_amount}")
                            else:
                                logger.warning(f"Could not apply promotion {promotion_id}: {promo_result['EM']}")
                                # Don't update promotion_id if it failed
                                update_data['promotion_id'] = old_booking.get('promotion_id')

                        # Update total_amount
                        update_data['total_amount'] = final_amount

                    # Add updated_at timestamp
                    update_data['updated_at'] = datetime.now(timezone.utc)

                    # Build update query
                    set_clauses = []
                    values = []
                    for key, value in update_data.items():
                        set_clauses.append(f"{key} = %s")
                        values.append(value)
                    values.append(booking_id)

                    # Update booking
                    cur.execute(
                        f"UPDATE bookings SET {', '.join(set_clauses)} WHERE booking_id = %s RETURNING *",
                        values
                    )
                    conn.commit()

                    result = cur.fetchone()

                    if not result:
                        return {
                            "EC": 2,
                            "EM": "Failed to update booking",
                            "data": None
                        }

                    logger.info(f"Updated booking {booking_id}")

                    return {
                        "EC": 0,
                        "EM": "Booking updated successfully",
                        "data": dict(result)
                    }

        except Exception as e:
            logger.error(f"Error updating booking {booking_id}: {str(e)}")
            return {
                "EC": 3,
                "EM": f"Error updating booking: {str(e)}",
                "data": None
            }

    async def cancel_booking(
        self,
        booking_id: str,
        reason: Optional[str] = None,
        cancelled_by: str = "user"
    ) -> Dict[str, Any]:
        """
        Cancel a booking (soft delete - update status to 'cancelled')
        Also inserts record to booking_cancellations table and restores slots.

        Can cancel bookings with status: 'otp_sent', 'pending', or 'confirmed'
        - 'otp_sent': User created booking but hasn't verified OTP yet
        - 'pending': Booking confirmed, waiting for payment
        - 'confirmed': Booking fully confirmed

        Args:
            booking_id: UUID of the booking
            reason: Optional cancellation reason
            cancelled_by: Who cancelled - 'user', 'admin', or 'system'

        Returns:
            Dict with EC, EM, and data
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Get booking data first
                    existing = await self.get_booking_by_id(booking_id)
                    if existing["EC"] != 0:
                        return existing

                    booking = existing["data"]

                    # Check if already cancelled
                    if booking['status'] == 'cancelled':
                        return {
                            "EC": 3,
                            "EM": "Booking is already cancelled",
                            "data": None
                        }

                    # Check if can be cancelled (otp_sent, pending, or confirmed)
                    if booking['status'] not in ['otp_sent', 'pending', 'confirmed']:
                        return {
                            "EC": 4,
                            "EM": f"Cannot cancel booking with status '{booking['status']}'",
                            "data": None
                        }

                    # 1. Insert to booking_cancellations table (full booking snapshot)
                    cancellation_data = {
                        "booking_id": booking_id,
                        "user_id": booking['user_id'],
                        "package_id": booking['package_id'],
                        # Booking snapshot
                        "number_of_people": booking['number_of_people'],
                        "total_amount": booking.get('total_amount'),
                        "contact_name": booking.get('contact_name'),
                        "contact_phone": booking.get('contact_phone'),
                        "contact_email": booking.get('contact_email'),
                        "special_requests": booking.get('special_requests'),
                        "previous_status": booking['status'],  # Status before cancel
                        "promotion_id": booking.get('promotion_id'),
                        "booking_created_at": booking.get('created_at'),
                        # Cancellation info
                        "reason": reason,
                        "cancelled_by": cancelled_by
                    }

                    cur.execute(
                        """INSERT INTO booking_cancellations
                           (booking_id, user_id, package_id, number_of_people, total_amount,
                            contact_name, contact_phone, contact_email, special_requests,
                            previous_status, promotion_id, booking_created_at, reason, cancelled_by)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (
                            cancellation_data['booking_id'],
                            cancellation_data['user_id'],
                            cancellation_data['package_id'],
                            cancellation_data['number_of_people'],
                            cancellation_data['total_amount'],
                            cancellation_data['contact_name'],
                            cancellation_data['contact_phone'],
                            cancellation_data['contact_email'],
                            cancellation_data['special_requests'],
                            cancellation_data['previous_status'],
                            cancellation_data['promotion_id'],
                            cancellation_data['booking_created_at'],
                            cancellation_data['reason'],
                            cancellation_data['cancelled_by']
                        )
                    )
                    conn.commit()

                    # 2. Update booking status to cancelled (soft delete)
                    cur.execute(
                        "UPDATE bookings SET status = 'cancelled', updated_at = NOW() WHERE booking_id = %s RETURNING *",
                        (booking_id,)
                    )
                    conn.commit()

                    update_result = cur.fetchone()

                    if not update_result:
                        return {
                            "EC": 1,
                            "EM": "Failed to cancel booking"
                        }

                    # 3. Restore package slots
                    cur.execute(
                        "SELECT available_slots FROM tour_packages WHERE package_id = %s",
                        (booking['package_id'],)
                    )
                    package_result = cur.fetchone()

                    if package_result:
                        current_slots = package_result['available_slots']
                        new_slots = current_slots + booking['number_of_people']

                        cur.execute(
                            "UPDATE tour_packages SET available_slots = %s WHERE package_id = %s",
                            (new_slots, booking['package_id'])
                        )
                        conn.commit()

                        logger.info(f"Restored {booking['number_of_people']} slots to package {booking['package_id']}")

                    logger.info(f"Cancelled booking {booking_id} by {cancelled_by}")

                    return {
                        "EC": 0,
                        "EM": "Booking cancelled successfully",
                        "data": dict(update_result)
                    }

        except Exception as e:
            logger.error(f"Error cancelling booking {booking_id}: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error cancelling booking: {str(e)}",
                "data": None
            }

    async def delete_booking(self, booking_id: str) -> Dict[str, Any]:
        """
        Delete a booking - DEPRECATED, use cancel_booking instead
        This now calls cancel_booking for backward compatibility

        Args:
            booking_id: UUID of the booking

        Returns:
            Dict with EC and EM
        """
        logger.warning(f"delete_booking is deprecated, use cancel_booking instead. Booking: {booking_id}")
        result = await self.cancel_booking(booking_id, reason="Deleted via deprecated method", cancelled_by="system")
        return result

    async def create_booking_with_otp(self, booking_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create booking with OTP verification flow (copy logic from MCP chatbot)

        Args:
            booking_data: Dictionary containing booking information including contact_email

        Returns:
            Dict with EC, EM, and data (includes booking_id, awaiting_otp flag)
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    contact_email = booking_data.get('contact_email')
                    contact_phone = booking_data.get('contact_phone')

                    if not contact_email:
                        return {
                            "EC": 1,
                            "EM": "Email is required for OTP verification",
                            "data": None
                        }

                    # 1. Verify package exists, has available slots, and get price
                    cur.execute(
                        "SELECT available_slots, is_active, price, package_name FROM tour_packages WHERE package_id = %s",
                        (str(booking_data['package_id']),)
                    )
                    package_result = cur.fetchone()

                    if not package_result:
                        return {
                            "EC": 1,
                            "EM": "Tour package not found",
                            "data": None
                        }

                    package = dict(package_result)

                    if not package['is_active']:
                        return {
                            "EC": 2,
                            "EM": "Tour package is not active",
                            "data": None
                        }

                    if package['available_slots'] < booking_data['number_of_people']:
                        return {
                            "EC": 3,
                            "EM": f"Not enough slots available. Only {package['available_slots']} slots left",
                            "data": None
                        }

                    # 2. Calculate amount
                    total_amount = package['price'] * booking_data['number_of_people']

                    # 3. Create booking with status "otp_sent"
                    now = datetime.now(timezone.utc)
                    booking_insert = {
                        "package_id": str(booking_data['package_id']),
                        "number_of_people": booking_data['number_of_people'],
                        "total_amount": total_amount,
                        "contact_name": booking_data['contact_name'],
                        "contact_phone": contact_phone,
                        "contact_email": contact_email,  # Lưu email vào booking
                        "special_requests": booking_data.get('special_requests'),
                        "user_id": str(booking_data['user_id']),
                        "status": "otp_sent",  # OTP flow status
                        "created_at": now,
                        "updated_at": now
                    }

                    cur.execute(
                        """INSERT INTO bookings
                           (package_id, number_of_people, total_amount, contact_name,
                            contact_phone, contact_email, special_requests, user_id,
                            status, created_at, updated_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           RETURNING *""",
                        (
                            booking_insert['package_id'],
                            booking_insert['number_of_people'],
                            booking_insert['total_amount'],
                            booking_insert['contact_name'],
                            booking_insert['contact_phone'],
                            booking_insert['contact_email'],
                            booking_insert['special_requests'],
                            booking_insert['user_id'],
                            booking_insert['status'],
                            booking_insert['created_at'],
                            booking_insert['updated_at']
                        )
                    )

                    result = cur.fetchone()
                    conn.commit()

                    if not result:
                        return {
                            "EC": 4,
                            "EM": "Failed to create booking",
                            "data": None
                        }

                    booking = dict(result)
                    booking_id = booking['booking_id']

                    # 4. Generate OTP (6 digits)
                    otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])

                    # 5. Store OTP in database
                    otp_created_at, otp_expires_at = get_otp_db_timestamps()
                    otp_data = {
                        "booking_id": booking_id,
                        "otp_code": otp_code,
                        "email": contact_email
                    }

                    try:
                        cur.execute(
                            """INSERT INTO otp_verifications
                               (booking_id, otp_code, email, is_verified, expires_at, created_at)
                               VALUES (%s, %s, %s, FALSE, %s, %s)""",
                            (
                                otp_data['booking_id'],
                                otp_data['otp_code'],
                                otp_data['email'],
                                otp_expires_at,
                                otp_created_at
                            )
                        )
                        conn.commit()
                    except Exception as e:
                        logger.error(f"Error inserting OTP: {str(e)}")
                        conn.rollback()
                        return {"EC": 5, "EM": f"Failed to create OTP: {str(e)}", "data": None}

                    # 6. Send OTP via email (non-fatal — booking still created even if email fails)
                    try:
                        otp_service = get_otp_service()
                        email_sent = otp_service.send_otp_email(
                            email=contact_email,
                            otp=otp_code,
                            tour_name=package['package_name']
                        )
                        if not email_sent:
                            logger.warning(f"⚠️ Failed to send OTP email to {contact_email}, but booking created. OTP: {otp_code}")
                    except Exception as email_err:
                        logger.warning(f"⚠️ Email sending failed for {contact_email}: {email_err}. Booking {booking_id} still created. OTP: {otp_code}")

                    # 7. Update package slots
                    new_slots = package['available_slots'] - booking_data['number_of_people']
                    cur.execute(
                        "UPDATE tour_packages SET available_slots = %s WHERE package_id = %s",
                        (new_slots, str(booking_data['package_id']))
                    )
                    conn.commit()

                    logger.info(f"Created booking {booking_id} with OTP flow")

                    # 8. Return response
                    return {
                        "EC": 0,
                        "EM": "Đặt tour thành công. Vui lòng nhập mã OTP để xác nhận.",
                        "data": {
                            "booking_id": booking_id,
                            "awaiting_otp": True,
                            "status": "otp_sent",
                            "contact_email": contact_email,
                            "total_amount": total_amount,
                            "otp_code": otp_code
                        }
                    }

        except Exception as e:
            logger.error(f"Error creating booking with OTP: {str(e)}")
            return {
                "EC": 6,
                "EM": f"Error creating booking: {str(e)}",
                "data": None
            }

    async def create_booking_by_admin(self, booking_data: Dict[str, Any], admin_id: str) -> Dict[str, Any]:
        """
        Admin tạo booking cho khách hàng (bỏ qua OTP, status = pending)

        Flow:
        1. Validate package & check slots
        2. Create booking với status="pending" (không cần OTP)
        3. Update package slots
        4. Return booking_id

        Args:
            booking_data: Dictionary containing booking information
            admin_id: ID của admin tạo booking

        Returns:
            Dict with EC, EM, and data (includes booking_id, status="pending")
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # 1. Verify package exists, has available slots, and get price
                    cur.execute(
                        "SELECT available_slots, is_active, price, package_name FROM tour_packages WHERE package_id = %s",
                        (str(booking_data['package_id']),)
                    )
                    package_result = cur.fetchone()

                    if not package_result:
                        return {
                            "EC": 1,
                            "EM": "Tour package not found",
                            "data": None
                        }

                    package = dict(package_result)

                    if not package['is_active']:
                        return {
                            "EC": 2,
                            "EM": "Tour package is not active",
                            "data": None
                        }

                    if package['available_slots'] < booking_data['number_of_people']:
                        return {
                            "EC": 3,
                            "EM": f"Not enough slots available. Only {package['available_slots']} slots left",
                            "data": None
                        }

                    # 2. Calculate amount
                    total_amount = package['price'] * booking_data['number_of_people']

                    # 3. Create booking with status "pending" (không cần OTP)
                    now = datetime.now(timezone.utc)
                    booking_insert = {
                        "package_id": str(booking_data['package_id']),
                        "number_of_people": booking_data['number_of_people'],
                        "total_amount": total_amount,
                        "contact_name": booking_data['contact_name'],
                        "contact_phone": booking_data.get('contact_phone'),
                        "contact_email": booking_data.get('contact_email'),  # Optional
                        "special_requests": booking_data.get('special_requests'),
                        "user_id": str(booking_data['user_id']),
                        "status": "pending",  # Status pending ngay, không cần OTP
                        "created_at": now,
                        "updated_at": now
                    }

                    cur.execute(
                        """INSERT INTO bookings
                           (package_id, number_of_people, total_amount, contact_name,
                            contact_phone, contact_email, special_requests, user_id,
                            status, created_at, updated_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           RETURNING *""",
                        (
                            booking_insert['package_id'],
                            booking_insert['number_of_people'],
                            booking_insert['total_amount'],
                            booking_insert['contact_name'],
                            booking_insert['contact_phone'],
                            booking_insert['contact_email'],
                            booking_insert['special_requests'],
                            booking_insert['user_id'],
                            booking_insert['status'],
                            booking_insert['created_at'],
                            booking_insert['updated_at']
                        )
                    )

                    result = cur.fetchone()
                    conn.commit()

                    if not result:
                        return {
                            "EC": 4,
                            "EM": "Failed to create booking",
                            "data": None
                        }

                    booking = dict(result)
                    booking_id = booking['booking_id']

                    # 4. Update package slots
                    new_slots = package['available_slots'] - booking_data['number_of_people']
                    cur.execute(
                        "UPDATE tour_packages SET available_slots = %s WHERE package_id = %s",
                        (new_slots, str(booking_data['package_id']))
                    )
                    conn.commit()

                    # 5. Tự động tạo payment với status "pending" và payment_method="cash"
                    payment_data = {
                        "booking_id": booking_id,
                        "amount": total_amount,
                        "payment_method": "cash",
                        "status": "pending",  # Chờ thanh toán
                        "transaction_id": None,
                        "created_at": now
                    }

                    try:
                        cur.execute(
                            """INSERT INTO payments
                               (booking_id, amount, payment_method, status, transaction_id, created_at)
                               VALUES (%s, %s, %s, %s, %s, %s)""",
                            (
                                payment_data['booking_id'],
                                payment_data['amount'],
                                payment_data['payment_method'],
                                payment_data['status'],
                                payment_data['transaction_id'],
                                payment_data['created_at']
                            )
                        )
                        conn.commit()
                        logger.info(f"Auto-created pending payment for booking {booking_id} (cash method)")
                    except Exception as e:
                        # Nếu tạo payment thất bại, vẫn tiếp tục (booking đã tạo thành công)
                        logger.error(f"Error auto-creating payment for booking {booking_id}: {str(e)}")

                    logger.info(f"Admin {admin_id} created booking {booking_id} with status pending (no OTP)")

                    # 6. Return response
                    return {
                        "EC": 0,
                        "EM": "Đã tạo booking thành công. Booking đang ở trạng thái pending, chờ thanh toán.",
                        "data": {
                            "booking_id": booking_id,
                            "status": "pending",
                            "total_amount": total_amount,
                            "contact_name": booking_data['contact_name'],
                            "contact_phone": booking_data.get('contact_phone'),
                            "contact_email": booking_data.get('contact_email')
                        }
                    }

        except Exception as e:
            logger.error(f"Error creating booking by admin: {str(e)}")
            return {
                "EC": 6,
                "EM": f"Error creating booking: {str(e)}",
                "data": None
            }

    async def verify_otp(self, booking_id: str, otp_code: str) -> Dict[str, Any]:
        """
        Verify OTP and confirm booking (copy logic from MCP chatbot)

        Args:
            booking_id: UUID of the booking
            otp_code: 6-digit OTP code

        Returns:
            Dict with EC, EM, and data
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # 1. Get OTP record
                    cur.execute(
                        "SELECT * FROM otp_verifications WHERE booking_id = %s",
                        (booking_id,)
                    )
                    booking_check = cur.fetchone()

                    if not booking_check:
                        return {"EC": 1, "EM": "Không tìm thấy mã OTP cho booking này", "data": None}

                    # 2. Get OTP record with correct code and not verified
                    cur.execute(
                        """SELECT * FROM otp_verifications
                           WHERE booking_id = %s AND otp_code = %s AND is_verified = False""",
                        (booking_id, otp_code)
                    )
                    otp_res = cur.fetchone()

                    if not otp_res:
                        # OTP code is wrong - increment attempts
                        cur.execute(
                            "SELECT attempts, otp_code, expires_at, created_at FROM otp_verifications WHERE booking_id = %s",
                            (booking_id,)
                        )
                        existing_otp = cur.fetchone()

                        if existing_otp:
                            otp_info = dict(existing_otp)
                            current_attempts = otp_info.get("attempts", 0)

                            # Increment attempts
                            cur.execute(
                                "UPDATE otp_verifications SET attempts = %s WHERE booking_id = %s",
                                (current_attempts + 1, booking_id)
                            )
                            conn.commit()

                            # Check if expired
                            expires_at_str = otp_info.get('expires_at')
                            if expires_at_str:
                                if isinstance(expires_at_str, str):
                                    if expires_at_str.endswith('Z'):
                                        expires_at_str = expires_at_str.replace('Z', '+00:00')
                                    expires_at = datetime.fromisoformat(expires_at_str)
                                else:
                                    expires_at = expires_at_str

                                if expires_at.tzinfo is None:
                                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                                else:
                                    expires_at = expires_at.astimezone(timezone.utc)

                                now_utc = datetime.now(timezone.utc)
                                if now_utc > expires_at:
                                    return {"EC": 2, "EM": "Mã OTP đã hết hạn", "data": None}

                            return {"EC": 3, "EM": "Mã OTP không đúng", "data": None}

                        return {"EC": 3, "EM": "Mã OTP không đúng", "data": None}

                    otp_record = dict(otp_res)

                    # 3. Check expiry
                    expires_at_str = otp_record['expires_at']

                    if isinstance(expires_at_str, str):
                        if expires_at_str.endswith('Z'):
                            expires_at_str = expires_at_str.replace('Z', '+00:00')
                        expires_at = datetime.fromisoformat(expires_at_str)
                    else:
                        expires_at = expires_at_str

                    if expires_at.tzinfo is None:
                        expires_at = expires_at.replace(tzinfo=timezone.utc)
                    else:
                        expires_at = expires_at.astimezone(timezone.utc)

                    now_utc = datetime.now(timezone.utc)

                    if now_utc > expires_at:
                        return {"EC": 2, "EM": "Mã OTP đã hết hạn", "data": None}

                    # 4. Check attempts (max 3)
                    if otp_record.get('attempts', 0) >= 3:
                        return {"EC": 4, "EM": "Đã vượt quá số lần nhập OTP cho phép", "data": None}

                    # 5. Mark OTP as verified
                    cur.execute(
                        """UPDATE otp_verifications
                           SET is_verified = True, verified_at = NOW()
                           WHERE booking_id = %s""",
                        (booking_id,)
                    )
                    conn.commit()

                    # 6. Update booking status to "pending" (waiting for payment)
                    cur.execute(
                        "UPDATE bookings SET status = 'pending' WHERE booking_id = %s",
                        (booking_id,)
                    )
                    conn.commit()

                    # 7. Get booking details with JOIN
                    cur.execute(
                        """SELECT b.*, t.package_name, t.destination, t.start_date, t.price
                           FROM bookings b
                           JOIN tour_packages t ON b.package_id = t.package_id
                           WHERE b.booking_id = %s""",
                        (booking_id,)
                    )
                    booking = cur.fetchone()

                    if not booking:
                        booking = {}
                        pkg = {}
                    else:
                        booking = dict(booking)
                        pkg = {
                            'package_name': booking.get('package_name'),
                            'destination': booking.get('destination'),
                            'start_date': booking.get('start_date'),
                            'price': booking.get('price')
                        }

                    logger.info(f"OTP verified for booking {booking_id}")

                    return {
                        "EC": 0,
                        "EM": "✅ Xác thực thành công! Đặt tour của bạn đã được xác nhận. Vui lòng thanh toán để hoàn tất đặt tour.",
                        "data": {
                            "booking_id": booking_id,
                            "status": "pending",
                            "tour_name": pkg.get('package_name', 'Unknown Tour'),
                            "destination": pkg.get('destination', 'Unknown'),
                            "start_date": pkg.get('start_date'),
                            "number_of_people": booking.get('number_of_people'),
                            "total_amount": booking.get('total_amount')
                        }
                    }

        except Exception as e:
            logger.error(f"Error verifying OTP for booking {booking_id}: {str(e)}")
            return {
                "EC": 5,
                "EM": f"Error verifying OTP: {str(e)}",
                "data": None
            }

    async def resend_otp(self, booking_id: str) -> Dict[str, Any]:
        """
        Resend OTP for a booking (when OTP expired or not received)

        Args:
            booking_id: UUID of the booking

        Returns:
            Dict with EC, EM, and data
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # 1. Get booking info with JOIN
                    cur.execute(
                        """SELECT b.*, t.package_name
                           FROM bookings b
                           JOIN tour_packages t ON b.package_id = t.package_id
                           WHERE b.booking_id = %s""",
                        (booking_id,)
                    )
                    booking_res = cur.fetchone()

                    if not booking_res:
                        return {"EC": 1, "EM": "Booking not found", "data": None}

                    booking = dict(booking_res)

                    # Check status - only allow resend for otp_sent status
                    if booking['status'] != 'otp_sent':
                        return {
                            "EC": 2,
                            "EM": f"Cannot resend OTP. Booking status is '{booking['status']}'. OTP can only be resent for status 'otp_sent'.",
                            "data": None
                        }

                    contact_email = booking.get('contact_email')

                    # 2. Validate email exists
                    if not contact_email:
                        return {"EC": 3, "EM": "Email not found in booking record. Cannot resend OTP.", "data": None}

                    # 3. Delete old OTP records for this booking
                    cur.execute(
                        "DELETE FROM otp_verifications WHERE booking_id = %s",
                        (booking_id,)
                    )
                    conn.commit()

                    # 4. Generate new OTP
                    otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])

                    # 5. Store new OTP (with email)
                    otp_created_at, otp_expires_at = get_otp_db_timestamps()
                    otp_data = {
                        "booking_id": booking_id,
                        "otp_code": otp_code,
                        "email": contact_email,
                    }

                    cur.execute(
                        """INSERT INTO otp_verifications
                           (booking_id, otp_code, email, is_verified, expires_at, created_at)
                           VALUES (%s, %s, %s, FALSE, %s, %s)""",
                        (
                            otp_data['booking_id'],
                            otp_data['otp_code'],
                            otp_data['email'],
                            otp_expires_at,
                            otp_created_at
                        )
                    )
                    conn.commit()

                    # 6. Get package name for email
                    tour_name = booking.get('package_name', 'Tour')

                    # 7. Send OTP via email (non-fatal)
                    try:
                        otp_service = get_otp_service()
                        email_sent = otp_service.send_otp_email(
                            email=contact_email,
                            otp=otp_code,
                            tour_name=tour_name
                        )
                        if not email_sent:
                            logger.warning(f"⚠️ Failed to send OTP email to {contact_email}, but OTP created. OTP code: {otp_code}")
                    except Exception as email_err:
                        logger.warning(f"⚠️ Resend OTP email failed for {contact_email}: {email_err}. OTP code: {otp_code}")

                    logger.info(f"OTP resent for booking {booking_id}")

                    return {
                        "EC": 0,
                        "EM": "Mã OTP mới đã được tạo.",
                        "data": {
                            "booking_id": booking_id,
                            "contact_email": contact_email,
                            "message": "OTP resent successfully",
                            "otp_code": otp_code
                        }
                    }

        except Exception as e:
            logger.error(f"Error resending OTP for booking {booking_id}: {str(e)}")
            return {
                "EC": 5,
                "EM": f"Error resending OTP: {str(e)}",
                "data": None
            }


def get_booking_service():
    """Get booking service instance"""
    return BookingService()
