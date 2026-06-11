"""
Payment Service
Service xử lý CRUD operations cho payments
"""
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from supabase import Client

from .vnpay_service import VNPayService
from ..core.config import settings

logger = logging.getLogger(__name__)


class PaymentService:
    """Service for managing payments"""

    def __init__(self, supabase_client: Client):
        """
        Initialize PaymentService

        Args:
            supabase_client: Supabase client instance (kept for compatibility)
        """
        self.supabase = supabase_client
        self.vnpay_service = VNPayService()

    def _pg_conn(self):
        """Get PostgreSQL connection"""
        url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
        return psycopg2.connect(url, cursor_factory=RealDictCursor)

    async def create_payment(
        self,
        booking_id: str,
        payment_method: str = "vnpay",
        ip_addr: str = "127.0.0.1",
        client_return_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Tạo payment mới và generate VNPay URL
        """
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    # 1. Kiểm tra booking tồn tại và lấy thông tin
                    cur.execute("""
                        SELECT b.booking_id, b.total_amount, b.status, b.user_id, t.package_name
                        FROM bookings b
                        LEFT JOIN tour_packages t ON b.package_id = t.package_id
                        WHERE b.booking_id = %s
                    """, (booking_id,))
                    booking = cur.fetchone()

                    if not booking:
                        return {"EC": 1, "EM": "Booking not found", "data": None}

                    # 2. Kiểm tra booking status
                    if booking['status'] not in ['pending', 'confirmed']:
                        return {
                            "EC": 2, "EM": f"Cannot create payment for booking with status: {
                                booking['status']}", "data": None}

                    # 3. Kiểm tra đã có payment pending chưa
                    cur.execute("""
                        SELECT payment_id, status FROM payments
                        WHERE booking_id = %s AND status IN ('pending', 'completed')
                    """, (booking_id,))
                    existing = cur.fetchone()

                    if existing:
                        if existing['status'] == 'completed':
                            return {"EC": 3, "EM": "Booking already paid", "data": None}
                        return await self._regenerate_payment_url(existing['payment_id'], booking, ip_addr)

                    # 4. Tạo payment record
                    amount = float(booking['total_amount'])
                    now = datetime.now(timezone.utc)

                    cur.execute("""
                        INSERT INTO payments (booking_id, amount, payment_method, status, created_at)
                        VALUES (%s, %s, %s, 'pending', %s)
                        RETURNING payment_id, booking_id, amount, payment_method, status, created_at
                    """, (booking_id, amount, payment_method, now))
                    payment = dict(cur.fetchone())
                    conn.commit()

                    # 5. Generate VNPay URL
                    tour_name = booking.get('package_name', 'Tour')
                    order_info = f"Thanh toan tour {tour_name}"

                    payment_url = self.vnpay_service.create_payment_url(
                        payment_id=str(payment['payment_id']),
                        amount=amount,
                        order_info=order_info,
                        ip_addr=ip_addr,
                        client_return_url=client_return_url
                    )

                    payment['payment_url'] = payment_url
                    logger.info(f"Created payment {payment['payment_id']} for booking {booking_id}")

                    return {"EC": 0, "EM": "Payment created successfully", "data": payment}

        except Exception as e:
            logger.error(f"Error creating payment: {str(e)}")
            return {"EC": 5, "EM": f"Error creating payment: {str(e)}", "data": None}

    async def _regenerate_payment_url(
        self,
        payment_id: str,
        booking: Dict[str, Any],
        ip_addr: str
    ) -> Dict[str, Any]:
        """Regenerate payment URL for existing pending payment"""
        try:
            amount = float(booking['total_amount'])
            tour_name = booking.get('package_name', 'Tour')
            order_info = f"Thanh toan tour {tour_name}"

            payment_url = self.vnpay_service.create_payment_url(
                payment_id=str(payment_id),
                amount=amount,
                order_info=order_info,
                ip_addr=ip_addr
            )

            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM payments WHERE payment_id = %s", (payment_id,))
                    payment = dict(cur.fetchone()) if cur.rowcount else {}

            payment['payment_url'] = payment_url
            return {"EC": 0, "EM": "Payment URL regenerated", "data": payment}

        except Exception as e:
            logger.error(f"Error regenerating payment URL: {str(e)}")
            return {"EC": 5, "EM": f"Error: {str(e)}", "data": None}

    async def get_payment_by_id(self, payment_id: str) -> Dict[str, Any]:
        """Lấy payment theo ID"""
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM payments WHERE payment_id = %s", (payment_id,))
                    payment = cur.fetchone()

            if not payment:
                return {"EC": 1, "EM": "Payment not found", "data": None}

            return {"EC": 0, "EM": "Success", "data": dict(payment)}

        except Exception as e:
            logger.error(f"Error getting payment {payment_id}: {str(e)}")
            return {"EC": 2, "EM": f"Error: {str(e)}", "data": None}

    async def get_payment_by_booking_id(self, booking_id: str) -> Dict[str, Any]:
        """Lấy payment theo booking_id"""
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT * FROM payments WHERE booking_id = %s ORDER BY created_at DESC LIMIT 1
                    """, (booking_id,))
                    payment = cur.fetchone()

            if not payment:
                return {"EC": 1, "EM": "Payment not found for this booking", "data": None}

            return {"EC": 0, "EM": "Success", "data": dict(payment)}

        except Exception as e:
            logger.error(f"Error getting payment for booking {booking_id}: {str(e)}")
            return {"EC": 2, "EM": f"Error: {str(e)}", "data": None}

    async def update_status(
        self,
        payment_id: str,
        status: str,
        transaction_id: Optional[str] = None,
        paid_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update payment status"""
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    if paid_at is None and status == "completed":
                        paid_at = datetime.now(timezone.utc).isoformat()

                    cur.execute("""
                        UPDATE payments SET status = %s, transaction_id = COALESCE(%s, transaction_id),
                        paid_at = COALESCE(%s, paid_at)
                        WHERE payment_id = %s
                        RETURNING *
                    """, (status, transaction_id, paid_at, payment_id))
                    payment = cur.fetchone()
                    conn.commit()

            if not payment:
                return {"EC": 1, "EM": "Payment not found", "data": None}

            logger.info(f"Updated payment {payment_id} status to {status}")
            return {"EC": 0, "EM": "Payment status updated", "data": dict(payment)}

        except Exception as e:
            logger.error(f"Error updating payment {payment_id}: {str(e)}")
            return {"EC": 2, "EM": f"Error: {str(e)}", "data": None}

    async def verify_and_complete_payment(
        self,
        callback_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Verify VNPay callback và complete payment"""
        try:
            # 1. Verify signature
            verify_result = self.vnpay_service.verify_payment_response(callback_data)

            if not verify_result['is_valid']:
                return {"EC": 97, "EM": "Invalid signature", "data": None, "is_success": False}

            payment_id = verify_result['payment_id']
            response_code = verify_result['response_code']
            transaction_status = verify_result['transaction_status']
            transaction_id = verify_result['transaction_id']

            # 2. Get payment record
            payment_result = await self.get_payment_by_id(payment_id)

            if payment_result['EC'] != 0:
                return {"EC": 1, "EM": "Payment not found", "data": None, "is_success": False}

            payment = payment_result['data']

            # 3. Check if already processed
            if payment['status'] == 'completed':
                return {"EC": 0, "EM": "Payment already completed", "data": payment, "is_success": True}

            # 4. Verify amount
            callback_amount = verify_result['amount']
            if float(payment['amount']) != callback_amount:
                logger.warning(f"Amount mismatch: expected {payment['amount']}, got {callback_amount}")
                return {"EC": 4, "EM": "Amount mismatch", "data": None, "is_success": False}

            # 5. Update payment status based on response
            is_success = self.vnpay_service.is_payment_success(response_code, transaction_status)
            new_status = "completed" if is_success else "failed"

            # Parse pay_date
            pay_date = verify_result.get('pay_date')
            paid_at = None
            if pay_date and is_success:
                try:
                    paid_at = datetime.strptime(pay_date, '%Y%m%d%H%M%S').isoformat()
                except BaseException:
                    paid_at = datetime.now(timezone.utc).isoformat()

            update_result = await self.update_status(
                payment_id=payment_id,
                status=new_status,
                transaction_id=transaction_id,
                paid_at=paid_at
            )

            # 6. Update booking status if payment successful
            if is_success:
                booking_type = payment.get('booking_type', 'tour')
                if booking_type == 'flight':
                    flight_bid = payment.get('flight_booking_id')
                    if flight_bid:
                        with self._pg_conn() as conn:
                            with conn.cursor() as cur:
                                cur.execute(
                                    "UPDATE flight_bookings SET status = 'confirmed', payment_status = 'paid' WHERE booking_id = %s", (flight_bid,))
                                conn.commit()
                        logger.info(f"Flight booking {flight_bid} confirmed after payment")
                elif booking_type == 'train':
                    train_bid = payment.get('train_booking_id')
                    if train_bid:
                        with self._pg_conn() as conn:
                            with conn.cursor() as cur:
                                cur.execute(
                                    "UPDATE train_bookings SET status = 'confirmed', payment_status = 'paid' WHERE booking_id = %s", (train_bid,))
                                conn.commit()
                        logger.info(f"Train booking {train_bid} confirmed after payment")
                else:
                    booking_id = payment['booking_id']
                    if booking_id:
                        with self._pg_conn() as conn:
                            with conn.cursor() as cur:
                                cur.execute(
                                    "UPDATE bookings SET status = 'confirmed' WHERE booking_id = %s", (booking_id,))
                                conn.commit()
                        logger.info(f"Booking {booking_id} confirmed after payment")

            message = self.vnpay_service.get_response_message(response_code)

            return {
                "EC": 0 if is_success else int(response_code),
                "EM": message,
                "data": update_result.get('data'),
                "is_success": is_success
            }

        except Exception as e:
            logger.error(f"Error verifying payment: {str(e)}")
            return {"EC": 99, "EM": f"Error: {str(e)}", "data": None, "is_success": False}

    async def create_transport_payment(
        self,
        booking_type: str,
        booking_id: str,
        payment_method: str = "vnpay",
        ip_addr: str = "127.0.0.1",
        client_return_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tạo payment cho flight/train booking"""
        try:
            if booking_type not in ("flight", "train"):
                return {"EC": 1, "EM": "booking_type must be 'flight' or 'train'", "data": None}

            table = "flight_bookings" if booking_type == "flight" else "train_bookings"
            id_col = "flight_booking_id" if booking_type == "flight" else "train_booking_id"

            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"SELECT * FROM {table} WHERE booking_id = %s", (booking_id,))
                    booking = cur.fetchone()

                    if not booking:
                        return {"EC": 1, "EM": f"Booking {booking_id} not found", "data": None}

                    if booking.get("payment_status") == "paid":
                        return {"EC": 3, "EM": "Booking already paid", "data": None}

                    cur.execute(
                        f"SELECT payment_id, status FROM payments WHERE {id_col} = %s AND status IN ('pending', 'completed')",
                        (booking_id,)
                    )
                    existing = cur.fetchone()
                    if existing:
                        if existing["status"] == "completed":
                            return {"EC": 3, "EM": "Already paid", "data": None}
                        amount = float(booking["total_price"])
                        order_info = f"Thanh toan ve {'may bay' if booking_type == 'flight' else 'tau'} {booking_id}"
                        payment_url = self.vnpay_service.create_payment_url(
                            payment_id=str(existing["payment_id"]),
                            amount=amount,
                            order_info=order_info,
                            ip_addr=ip_addr,
                            client_return_url=client_return_url
                        )
                        return {
                            "EC": 0,
                            "EM": "Payment URL regenerated",
                            "data": {
                                "payment_id": str(
                                    existing["payment_id"]),
                                "payment_url": payment_url,
                                "amount": amount}}

                    amount = float(booking["total_price"])
                    now = datetime.now(timezone.utc)

                    cur.execute(
                        f"INSERT INTO payments (booking_type, {id_col}, amount, payment_method, status, created_at) VALUES (%s, %s, %s, %s, 'pending', %s) RETURNING payment_id, amount, payment_method, status, created_at",
                        (booking_type,
                         booking_id,
                         amount,
                         payment_method,
                         now))
                    payment = dict(cur.fetchone())
                    conn.commit()

                    order_info = f"Thanh toan ve {'may bay' if booking_type == 'flight' else 'tau'} {booking_id}"
                    payment_url = self.vnpay_service.create_payment_url(
                        payment_id=str(payment["payment_id"]),
                        amount=amount,
                        order_info=order_info,
                        ip_addr=ip_addr,
                        client_return_url=client_return_url
                    )

                    payment["payment_url"] = payment_url
                    payment["booking_type"] = booking_type
                    payment["booking_id"] = booking_id
                    logger.info(
                        f"Created transport payment {
                            payment['payment_id']} for {booking_type} booking {booking_id}")

                    return {"EC": 0, "EM": "Payment created successfully", "data": payment}

        except Exception as e:
            logger.error(f"Error creating transport payment: {str(e)}")
            return {"EC": 5, "EM": f"Error: {str(e)}", "data": None}

    async def get_user_payments(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """Lấy payment history của user"""
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT p.*, t.package_name, t.destination
                        FROM payments p
                        JOIN bookings b ON p.booking_id = b.booking_id
                        LEFT JOIN tour_packages t ON b.package_id = t.package_id
                        WHERE b.user_id = %s
                    """
                    params = [user_id]

                    if status:
                        query += " AND p.status = %s"
                        params.append(status)

                    query += " ORDER BY p.created_at DESC"

                    if limit:
                        query += " LIMIT %s"
                        params.append(limit)
                    if offset:
                        query += " OFFSET %s"
                        params.append(offset)

                    cur.execute(query, params)
                    payments = cur.fetchall()

                    # Get total count
                    count_query = """
                        SELECT COUNT(*) FROM payments p
                        JOIN bookings b ON p.booking_id = b.booking_id
                        WHERE b.user_id = %s
                    """
                    count_params = [user_id]
                    if status:
                        count_query += " AND p.status = %s"
                        count_params.append(status)
                    cur.execute(count_query, count_params)
                    total = cur.fetchone()['count']

            formatted_data = []
            for p in payments:
                formatted_data.append({
                    "payment_id": str(p['payment_id']),
                    "booking_id": str(p['booking_id']),
                    "amount": float(p['amount']),
                    "payment_method": p['payment_method'],
                    "status": p['status'],
                    "transaction_id": p.get('transaction_id'),
                    "paid_at": p.get('paid_at').isoformat() if p.get('paid_at') else None,
                    "created_at": p['created_at'].isoformat() if p.get('created_at') else None,
                    "tour_name": p.get('package_name'),
                    "destination": p.get('destination')
                })

            return {"EC": 0, "EM": "Success", "data": formatted_data, "total": total}

        except Exception as e:
            logger.error(f"Error getting user payments: {str(e)}")
            return {"EC": 1, "EM": f"Error: {str(e)}", "data": None, "total": 0}

    # ================== ADMIN PAYMENT METHODS ==================

    async def create_payment_by_admin(
        self,
        booking_id: str,
        admin_id: str,
        payment_method: str = "bank_transfer",
        transaction_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tạo payment thủ công bởi admin (bypass VNPay)"""
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    # 1. Kiểm tra booking
                    cur.execute(
                        "SELECT booking_id, total_amount, status, user_id FROM bookings WHERE booking_id = %s", (booking_id,))
                    booking = cur.fetchone()

                    if not booking:
                        return {"EC": 1, "EM": "Booking not found", "data": None}

                    if booking['status'] not in ['pending', 'confirmed']:
                        return {
                            "EC": 2, "EM": f"Cannot create payment for booking with status '{
                                booking['status']}'", "data": None}

                    # 2. Kiểm tra đã có payment completed chưa
                    cur.execute(
                        "SELECT payment_id FROM payments WHERE booking_id = %s AND status = 'completed'", (booking_id,))
                    if cur.fetchone():
                        return {"EC": 3, "EM": "Payment already exists for this booking", "data": None}

                    # 3. Tạo payment với status completed
                    now = datetime.now(timezone.utc)
                    cur.execute("""
                        INSERT INTO payments (booking_id, amount, payment_method, status, transaction_id, paid_at, created_at)
                        VALUES (%s, %s, %s, 'completed', %s, %s, %s)
                        RETURNING *
                    """, (booking_id, booking['total_amount'], payment_method, transaction_id, now, now))
                    payment = dict(cur.fetchone())

                    # 4. Cập nhật booking status
                    cur.execute("UPDATE bookings SET status = 'confirmed' WHERE booking_id = %s", (booking_id,))
                    conn.commit()

                    logger.info(f"Admin {admin_id} created payment for booking {booking_id}")
                    return {"EC": 0, "EM": "Payment created successfully", "data": payment}

        except Exception as e:
            logger.error(f"Error creating payment by admin: {str(e)}")
            return {"EC": 5, "EM": f"Error: {str(e)}", "data": None}

    async def confirm_cash_payment_by_admin(
        self,
        booking_id: str,
        admin_id: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Admin xác nhận khách hàng đã thanh toán tiền mặt cho booking"""
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    # 1. Kiểm tra booking
                    cur.execute(
                        "SELECT booking_id, total_amount, status, user_id FROM bookings WHERE booking_id = %s", (booking_id,))
                    booking = cur.fetchone()

                    if not booking:
                        return {"EC": 1, "EM": "Booking not found", "data": None}

                    if booking['status'] != 'pending':
                        return {
                            "EC": 2,
                            "EM": f"Chỉ có thể xác nhận thanh toán cho booking có status 'pending'. Booking hiện tại có status '{
                                booking['status']}'",
                            "data": None}

                    # 2. Kiểm tra payment hiện có
                    cur.execute(
                        "SELECT payment_id, status, payment_method FROM payments WHERE booking_id = %s", (booking_id,))
                    existing = cur.fetchone()

                    now = datetime.now(timezone.utc)

                    if existing:
                        if existing['status'] == 'completed':
                            return {
                                "EC": 3,
                                "EM": "Booking này đã có payment completed. Không thể tạo payment mới.",
                                "data": None}

                        # Update existing payment
                        cur.execute("""
                            UPDATE payments SET payment_method = 'cash', status = 'completed', paid_at = %s, transaction_id = NULL
                            WHERE payment_id = %s RETURNING *
                        """, (now, existing['payment_id']))
                        payment = dict(cur.fetchone())
                    else:
                        # Create new payment
                        cur.execute("""
                            INSERT INTO payments (booking_id, amount, payment_method, status, paid_at, created_at)
                            VALUES (%s, %s, 'cash', 'completed', %s, %s)
                            RETURNING *
                        """, (booking_id, booking['total_amount'], now, now))
                        payment = dict(cur.fetchone())

                    # Update booking status
                    cur.execute("UPDATE bookings SET status = 'confirmed' WHERE booking_id = %s", (booking_id,))
                    conn.commit()

                    log_msg = f"Admin {admin_id} confirmed cash payment for booking {booking_id}. Amount: {
                        booking['total_amount']}"
                    if notes:
                        log_msg += f" Notes: {notes}"
                    logger.info(log_msg)

                    return {
                        "EC": 0,
                        "EM": "Đã xác nhận thanh toán tiền mặt thành công. Booking đã được xác nhận.",
                        "data": payment}

        except Exception as e:
            logger.error(f"Error confirming cash payment by admin: {str(e)}")
            return {"EC": 5, "EM": f"Error: {str(e)}", "data": None}

    async def refund_payment_by_admin(
        self,
        payment_id: str,
        admin_id: str,
        refund_reason: str
    ) -> Dict[str, Any]:
        """Hoàn tiền payment bởi admin"""
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    # 1. Lấy thông tin payment
                    cur.execute(
                        "SELECT payment_id, booking_id, amount, status, refunded_at FROM payments WHERE payment_id = %s", (payment_id,))
                    payment = cur.fetchone()

                    if not payment:
                        return {"EC": 1, "EM": "Payment not found", "data": None}

                    if payment['status'] != 'completed':
                        return {"EC": 2, "EM": f"Cannot refund payment with status '{payment['status']}'", "data": None}

                    if payment['refunded_at'] is not None:
                        return {"EC": 3, "EM": "Payment already refunded", "data": None}

                    # 2. Lấy thông tin booking
                    cur.execute("SELECT booking_id, status FROM bookings WHERE booking_id = %s",
                                (payment['booking_id'],))
                    booking = cur.fetchone()

                    if not booking:
                        return {"EC": 4, "EM": "Booking not found", "data": None}

                    if booking['status'] in ['cancelled', 'completed']:
                        return {
                            "EC": 5, "EM": f"Cannot refund payment for booking with status '{
                                booking['status']}'", "data": None}

                    # 3. Update payment với thông tin refund
                    now = datetime.now(timezone.utc)
                    cur.execute("""
                        UPDATE payments SET status = 'refunded', refunded_at = %s, refund_amount = %s, refund_reason = %s
                        WHERE payment_id = %s RETURNING *
                    """, (now, payment['amount'], refund_reason, payment_id))
                    refunded = dict(cur.fetchone())

                    # 4. Update booking status về pending
                    cur.execute("UPDATE bookings SET status = 'pending' WHERE booking_id = %s",
                                (payment['booking_id'],))
                    conn.commit()

                    logger.info(f"Admin {admin_id} refunded payment {payment_id} for booking {payment['booking_id']}")
                    return {"EC": 0, "EM": "Payment refunded successfully", "data": refunded}

        except Exception as e:
            logger.error(f"Error refunding payment by admin: {str(e)}")
            return {"EC": 7, "EM": f"Error: {str(e)}", "data": None}

    async def get_all_payments_admin(
        self,
        status: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """Lấy danh sách tất cả payments cho admin"""
        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT p.*, b.user_id, b.contact_phone, b.contact_email, t.package_name, t.start_date
                        FROM payments p
                        JOIN bookings b ON p.booking_id = b.booking_id
                        LEFT JOIN tour_packages t ON b.package_id = t.package_id
                        WHERE 1=1
                    """
                    params = []

                    if status:
                        query += " AND p.status = %s"
                        params.append(status)

                    if user_id:
                        query += " AND b.user_id = %s"
                        params.append(user_id)

                    query += " ORDER BY p.created_at DESC"

                    if limit:
                        query += " LIMIT %s"
                        params.append(limit)
                    if offset:
                        query += " OFFSET %s"
                        params.append(offset)

                    cur.execute(query, params)
                    payments = cur.fetchall()

                    # Get total count
                    count_query = "SELECT COUNT(*) FROM payments p JOIN bookings b ON p.booking_id = b.booking_id WHERE 1=1"
                    count_params = []
                    if status:
                        count_query += " AND p.status = %s"
                        count_params.append(status)
                    if user_id:
                        count_query += " AND b.user_id = %s"
                        count_params.append(user_id)
                    cur.execute(count_query, count_params)
                    total = cur.fetchone()['count']

            formatted_data = []
            for p in payments:
                formatted_data.append({
                    "payment_id": str(p['payment_id']),
                    "booking_id": str(p['booking_id']),
                    "user_id": str(p['user_id']) if p.get('user_id') else None,
                    "amount": float(p['amount']),
                    "payment_method": p['payment_method'],
                    "status": p['status'],
                    "transaction_id": p.get('transaction_id'),
                    "paid_at": p['paid_at'].isoformat() if p.get('paid_at') else None,
                    "created_at": p['created_at'].isoformat() if p.get('created_at') else None,
                    "tour_name": p.get('package_name'),
                    "start_date": str(p['start_date']) if p.get('start_date') else None,
                    "contact_phone": p.get('contact_phone'),
                    "contact_email": p.get('contact_email'),
                    "refunded_at": p['refunded_at'].isoformat() if p.get('refunded_at') else None
                })

            return {"EC": 0, "EM": "Success", "data": formatted_data, "total": total}

        except Exception as e:
            logger.error(f"Error getting all payments for admin: {str(e)}")
            return {"EC": 1, "EM": f"Error: {str(e)}", "data": None, "total": 0}
