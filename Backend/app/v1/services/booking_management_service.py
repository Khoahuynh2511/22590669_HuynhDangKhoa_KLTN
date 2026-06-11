"""
Booking Management Service
Service cho UC-USER-03: Quản lý Tour Đã Đăng Ký
"""
import logging
from typing import Optional, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from ..core.config import settings
from ..core.datetime_utils import to_json_value

logger = logging.getLogger(__name__)


class BookingManagementService:
    """Service for managing user bookings with tour package information"""

    def __init__(self):
        """Initialize BookingManagementService"""
        self.db_url = settings.DATABASE_URL

    def _get_conn(self):
        """Get a new database connection"""
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    def _normalize(self, rows):
        """Convert RealDictRow to regular dict"""
        return [dict(r) for r in rows]

    def get_user_bookings(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Lấy danh sách bookings của user với thông tin tour package

        Args:
            user_id: ID của user
            status: Filter theo trạng thái (pending/confirmed/cancelled/completed)
            limit: Maximum number of results
            offset: Number of records to skip

        Returns:
            Dict with EC, EM, data, and total
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                # Build query with JOIN to tour_packages
                query = """
                    SELECT
                        b.booking_id,
                        b.package_id,
                        b.number_of_people,
                        b.total_amount,
                        b.status,
                        b.created_at,
                        tp.package_name,
                        tp.destination,
                        tp.start_date,
                        tp.end_date
                    FROM bookings b
                    LEFT JOIN tour_packages tp ON b.package_id = tp.package_id
                    WHERE b.user_id = %s
                """
                params = [user_id]

                # Apply status filter
                if status:
                    query += " AND b.status = %s"
                    params.append(status)

                # Get total count
                count_query = "SELECT COUNT(*) as cnt FROM bookings b WHERE b.user_id = %s"
                count_params = [user_id]
                if status:
                    count_query += " AND b.status = %s"
                    count_params.append(status)

                cursor.execute(count_query, tuple(count_params))
                total = cursor.fetchone()['cnt']

                # Add ordering and pagination
                query += " ORDER BY b.created_at DESC"

                if limit:
                    query += " LIMIT %s"
                    params.append(limit)
                if offset:
                    query += " OFFSET %s"
                    params.append(offset)

                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()

                # Format response data
                formatted_data = []
                for booking in rows:
                    formatted_data.append({
                        "booking_id": str(booking['booking_id']),
                        "package_id": str(booking['package_id']) if booking['package_id'] else None,
                        "tour_name": booking.get('package_name', 'Unknown Tour'),
                        "destination": booking.get('destination', 'Unknown'),
                        "start_date": to_json_value(booking.get('start_date')),
                        "end_date": to_json_value(booking.get('end_date')),
                        "number_of_people": booking['number_of_people'],
                        "total_amount": float(booking['total_amount']),
                        "status": booking['status'],
                        "created_at": to_json_value(booking.get('created_at'))
                    })

                return {
                    "EC": 0,
                    "EM": "Success",
                    "data": formatted_data,
                    "total": total
                }

        except Exception as e:
            logger.error(f"Error getting user bookings: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error retrieving bookings: {str(e)}",
                "data": None,
                "total": 0
            }

    def get_user_booking_detail(
        self,
        booking_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Lấy chi tiết booking của user với đầy đủ thông tin tour package

        Args:
            booking_id: UUID của booking
            user_id: ID của user (để verify ownership)

        Returns:
            Dict with EC, EM, and data
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                # Query with JOIN to tour_packages
                query = """
                    SELECT
                        b.*,
                        tp.package_id,
                        tp.package_name,
                        tp.destination,
                        tp.description,
                        tp.duration_days,
                        tp.start_date,
                        tp.end_date,
                        tp.price,
                        tp.image_urls
                    FROM bookings b
                    LEFT JOIN tour_packages tp ON b.package_id = tp.package_id
                    WHERE b.booking_id = %s AND b.user_id = %s
                """

                cursor.execute(query, (booking_id, user_id))
                row = cursor.fetchone()

                if not row:
                    return {
                        "EC": 1,
                        "EM": "Booking not found or access denied",
                        "data": None
                    }

                # Format tour package info
                tour_package_info = None
                if row.get('package_id'):
                    tour_package_info = {
                        "package_id": str(row['package_id']),
                        "package_name": row.get('package_name'),
                        "destination": row.get('destination'),
                        "description": row.get('description'),
                        "duration_days": row.get('duration_days'),
                        "start_date": to_json_value(row.get('start_date')),
                        "end_date": to_json_value(row.get('end_date')),
                        "price": float(row.get('price', 0)) if row.get('price') else 0,
                        "image_urls": row.get('image_urls')
                    }

                # Format booking detail
                formatted_data = {
                    "booking_id": str(row['booking_id']),
                    "status": row['status'],
                    "number_of_people": row['number_of_people'],
                    "total_amount": float(row['total_amount']),
                    "contact_name": row['contact_name'],
                    "contact_phone": row['contact_phone'],
                    "special_requests": row.get('special_requests'),
                    "created_at": to_json_value(row.get('created_at')),
                    "updated_at": to_json_value(row.get('updated_at')),
                    "tour_package": tour_package_info
                }

                return {
                    "EC": 0,
                    "EM": "Success",
                    "data": formatted_data
                }

        except Exception as e:
            logger.error(f"Error getting booking detail {booking_id}: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error retrieving booking: {str(e)}",
                "data": None
            }

    def get_all_bookings_admin(
        self,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Admin: Lấy tất cả bookings trong hệ thống với thông tin user và tour

        Args:
            status: Filter theo trạng thái
            limit: Maximum number of results
            offset: Number of records to skip

        Returns:
            Dict with EC, EM, data, and total
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                # Build query with JOIN to tour_packages
                query = """
                    SELECT
                        b.booking_id,
                        b.user_id,
                        b.number_of_people,
                        b.total_amount,
                        b.status,
                        b.created_at,
                        tp.package_name,
                        tp.destination,
                        tp.start_date
                    FROM bookings b
                    LEFT JOIN tour_packages tp ON b.package_id = tp.package_id
                    WHERE 1=1
                """
                params = []

                # Apply status filter
                if status:
                    query += " AND b.status = %s"
                    params.append(status)

                # Get total count
                count_query = "SELECT COUNT(*) as cnt FROM bookings b WHERE 1=1"
                count_params = []
                if status:
                    count_query += " AND b.status = %s"
                    count_params.append(status)

                cursor.execute(count_query, tuple(count_params))
                total = cursor.fetchone()['cnt']

                # Add ordering and pagination
                query += " ORDER BY b.created_at DESC"

                if limit:
                    query += " LIMIT %s"
                    params.append(limit)
                if offset:
                    query += " OFFSET %s"
                    params.append(offset)

                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()

                # Format response data with user info
                formatted_data = []
                for booking in rows:
                    user_id = booking['user_id']
                    user_email = None
                    user_full_name = None

                    # Get user info separately
                    if user_id:
                        try:
                            cursor.execute(
                                "SELECT email, full_name FROM users WHERE user_id = %s",
                                (user_id,)
                            )
                            user_row = cursor.fetchone()
                            if user_row:
                                user_email = user_row.get('email')
                                user_full_name = user_row.get('full_name')
                        except Exception as e:
                            logger.warning(f"Could not fetch user info for {user_id}: {str(e)}")

                    formatted_data.append({
                        "booking_id": str(booking['booking_id']),
                        "user_id": str(user_id) if user_id else None,
                        "user_email": user_email,
                        "user_full_name": user_full_name,
                        "tour_name": booking.get('package_name', 'Unknown Tour'),
                        "destination": booking.get('destination', 'Unknown'),
                        "start_date": to_json_value(booking.get('start_date')),
                        "number_of_people": booking['number_of_people'],
                        "total_amount": float(booking['total_amount']),
                        "status": booking['status'],
                        "created_at": to_json_value(booking.get('created_at'))
                    })

                return {
                    "EC": 0,
                    "EM": "Success",
                    "data": formatted_data,
                    "total": total
                }

        except Exception as e:
            logger.error(f"Error getting all bookings admin: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error retrieving bookings: {str(e)}",
                "data": None,
                "total": 0
            }

    def get_user_bookings_admin(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Admin: Lấy tất cả bookings của 1 user cụ thể

        Args:
            user_id: ID của user cần xem
            status: Filter theo trạng thái
            limit: Maximum number of results
            offset: Number of records to skip

        Returns:
            Dict with EC, EM, data, and total
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                # Build query with JOIN to tour_packages
                query = """
                    SELECT
                        b.booking_id,
                        b.number_of_people,
                        b.total_amount,
                        b.status,
                        b.created_at,
                        tp.package_name,
                        tp.destination,
                        tp.start_date
                    FROM bookings b
                    LEFT JOIN tour_packages tp ON b.package_id = tp.package_id
                    WHERE b.user_id = %s
                """
                params = [user_id]

                # Apply status filter
                if status:
                    query += " AND b.status = %s"
                    params.append(status)

                # Get total count
                count_query = "SELECT COUNT(*) as cnt FROM bookings b WHERE b.user_id = %s"
                count_params = [user_id]
                if status:
                    count_query += " AND b.status = %s"
                    count_params.append(status)

                cursor.execute(count_query, tuple(count_params))
                total = cursor.fetchone()['cnt']

                # Add ordering and pagination
                query += " ORDER BY b.created_at DESC"

                if limit:
                    query += " LIMIT %s"
                    params.append(limit)
                if offset:
                    query += " OFFSET %s"
                    params.append(offset)

                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()

                # Format response data
                formatted_data = []
                for booking in rows:
                    formatted_data.append({
                        "booking_id": str(booking['booking_id']),
                        "user_id": user_id,  # Include user_id for admin
                        "tour_name": booking.get('package_name', 'Unknown Tour'),
                        "destination": booking.get('destination', 'Unknown'),
                        "start_date": to_json_value(booking.get('start_date')),
                        "number_of_people": booking['number_of_people'],
                        "total_amount": float(booking['total_amount']),
                        "status": booking['status'],
                        "created_at": to_json_value(booking.get('created_at'))
                    })

                return {
                    "EC": 0,
                    "EM": "Success",
                    "data": formatted_data,
                    "total": total
                }

        except Exception as e:
            logger.error(f"Error getting user bookings admin: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error retrieving bookings: {str(e)}",
                "data": None,
                "total": 0
            }

    def get_booking_detail_admin(
        self,
        booking_id: str
    ) -> Dict[str, Any]:
        """
        Admin: Lấy chi tiết bất kỳ booking nào

        Args:
            booking_id: UUID của booking

        Returns:
            Dict with EC, EM, and data
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                # Query with JOIN to tour_packages
                query = """
                    SELECT
                        b.*,
                        tp.package_id,
                        tp.package_name,
                        tp.destination,
                        tp.description,
                        tp.duration_days,
                        tp.start_date,
                        tp.end_date,
                        tp.price,
                        tp.image_urls
                    FROM bookings b
                    LEFT JOIN tour_packages tp ON b.package_id = tp.package_id
                    WHERE b.booking_id = %s
                """

                cursor.execute(query, (booking_id,))
                row = cursor.fetchone()

                if not row:
                    return {
                        "EC": 1,
                        "EM": "Booking not found",
                        "data": None
                    }

                # Format tour package info
                tour_package_info = None
                if row.get('package_id'):
                    tour_package_info = {
                        "package_id": str(row['package_id']),
                        "package_name": row.get('package_name'),
                        "destination": row.get('destination'),
                        "description": row.get('description'),
                        "duration_days": row.get('duration_days'),
                        "start_date": to_json_value(row.get('start_date')),
                        "end_date": to_json_value(row.get('end_date')),
                        "price": float(row.get('price', 0)) if row.get('price') else 0,
                        "image_urls": row.get('image_urls')
                    }

                # Format booking detail
                formatted_data = {
                    "booking_id": str(row['booking_id']),
                    "status": row['status'],
                    "number_of_people": row['number_of_people'],
                    "total_amount": float(row['total_amount']),
                    "contact_name": row['contact_name'],
                    "contact_phone": row['contact_phone'],
                    "special_requests": row.get('special_requests'),
                    "created_at": to_json_value(row.get('created_at')),
                    "updated_at": to_json_value(row.get('updated_at')),
                    "tour_package": tour_package_info
                }

                return {
                    "EC": 0,
                    "EM": "Success",
                    "data": formatted_data
                }

        except Exception as e:
            logger.error(f"Error getting booking detail admin {booking_id}: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error retrieving booking: {str(e)}",
                "data": None
            }

    def get_all_cancellations_admin(
        self,
        cancelled_by: Optional[str] = None,
        limit: Optional[int] = 100,
        offset: Optional[int] = 0
    ) -> Dict[str, Any]:
        """
        Admin: Lấy danh sách tất cả booking cancellations trong hệ thống

        Args:
            cancelled_by: Filter by who cancelled (user/admin/system)
            limit: Maximum number of results
            offset: Number of records to skip

        Returns:
            Dict with EC, EM, data, and total
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                # Build query - JOIN with bookings and tour_packages for full info
                query = """
                    SELECT
                        bc.cancellation_id,
                        bc.booking_id,
                        bc.reason,
                        bc.cancelled_by,
                        bc.refund_amount,
                        bc.refund_status,
                        bc.created_at,
                        b.user_id,
                        b.package_id,
                        b.number_of_people,
                        b.total_amount,
                        b.contact_name,
                        b.contact_phone,
                        b.contact_email,
                        b.special_requests,
                        b.status as booking_status,
                        b.created_at as booking_created_at
                    FROM booking_cancellations bc
                    LEFT JOIN bookings b ON bc.booking_id = b.booking_id
                    WHERE 1=1
                """
                params = []

                # Note: cancelled_by in DB is a UUID reference to users, not a role string
                # Skip this filter as it's incompatible with current schema
                # if cancelled_by:
                #     query += " AND bc.cancelled_by = %s"
                #     params.append(cancelled_by)

                # Get total count
                count_query = "SELECT COUNT(*) as cnt FROM booking_cancellations WHERE 1=1"
                count_params = []

                cursor.execute(count_query, tuple(count_params))
                total = cursor.fetchone()['cnt']

                # Add ordering and pagination
                query += " ORDER BY bc.created_at DESC"

                if limit:
                    query += " LIMIT %s"
                    params.append(limit)
                if offset:
                    query += " OFFSET %s"
                    params.append(offset)

                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()

                # Format response data with additional info
                formatted_data = []
                for cancel in rows:
                    # Get tour info
                    tour_name = "Unknown Tour"
                    if cancel.get('package_id'):
                        try:
                            cursor.execute(
                                "SELECT package_name, destination FROM tour_packages WHERE package_id = %s",
                                (cancel['package_id'],)
                            )
                            tour_row = cursor.fetchone()
                            if tour_row:
                                tour_name = tour_row.get('package_name', 'Unknown Tour')
                        except Exception as e:
                            logger.warning(f"Could not fetch tour info for {cancel.get('package_id')}: {str(e)}")

                    # Get user info
                    user_email = None
                    user_full_name = None
                    if cancel.get('user_id'):
                        try:
                            cursor.execute(
                                "SELECT email, full_name FROM users WHERE user_id = %s",
                                (cancel['user_id'],)
                            )
                            user_row = cursor.fetchone()
                            if user_row:
                                user_email = user_row.get('email')
                                user_full_name = user_row.get('full_name')
                        except Exception as e:
                            logger.warning(f"Could not fetch user info for {cancel.get('user_id')}: {str(e)}")

                    formatted_data.append({
                        "cancellation_id": str(cancel.get('cancellation_id')) if cancel.get('cancellation_id') else None,
                        "booking_id": str(cancel.get('booking_id')) if cancel.get('booking_id') else None,
                        "user_id": str(cancel.get('user_id')) if cancel.get('user_id') else None,
                        "user_email": user_email,
                        "user_full_name": user_full_name,
                        "package_id": str(cancel.get('package_id')) if cancel.get('package_id') else None,
                        "tour_name": tour_name,
                        # Booking snapshot (from JOIN with bookings)
                        "number_of_people": cancel.get('number_of_people'),
                        "total_amount": float(cancel.get('total_amount', 0)) if cancel.get('total_amount') else 0,
                        "contact_name": cancel.get('contact_name'),
                        "contact_phone": cancel.get('contact_phone'),
                        "contact_email": cancel.get('contact_email'),
                        "special_requests": cancel.get('special_requests'),
                        "previous_status": cancel.get('booking_status'),
                        "booking_created_at": to_json_value(cancel.get('booking_created_at')),
                        # Cancellation info
                        "reason": cancel.get('reason'),
                        "cancelled_at": to_json_value(cancel.get('created_at')),
                        "cancelled_by": str(cancel.get('cancelled_by')) if cancel.get('cancelled_by') else None,
                        "refund_amount": float(cancel.get('refund_amount', 0)) if cancel.get('refund_amount') else 0,
                        "refund_status": cancel.get('refund_status'),
                        "created_at": to_json_value(cancel.get('created_at'))
                    })

                return {
                    "EC": 0,
                    "EM": "Success",
                    "data": formatted_data,
                    "total": total
                }

        except Exception as e:
            logger.error(f"Error getting all cancellations admin: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error retrieving cancellations: {str(e)}",
                "data": None,
                "total": 0
            }


# Dependency function
def get_booking_management_service():
    """Dependency function to get BookingManagementService instance"""
    return BookingManagementService()
