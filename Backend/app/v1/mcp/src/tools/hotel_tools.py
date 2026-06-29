"""
Hotel Tools - MCP Tools cho tim kiem va dat phong khach san
Su du lieu tu PostgreSQL database
"""

from fastmcp import FastMCP
from typing import Dict, Any, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from app.v1.core.config import settings
import uuid


class HotelMCPService:
    """Hotel Service cho MCP tools - query tu DB"""

    def _get_conn(self):
        return psycopg2.connect(settings.DATABASE_URL, cursor_factory=RealDictCursor)

    def _format_hotel_info(self, hotel: Dict[str, Any], index: int, total: int) -> str:
        """Format hotel info thanh string dep"""
        result = f"\U0001f3e8 Khach san {index}/{total}\n"
        result += "─" * 50 + "\n"
        result += f"\U0001f3e8 {hotel['hotel_name']}\n"
        result += f"\U0001f4cd {hotel['location']}\n"
        if hotel.get('address'):
            result += f"   \U0001f4cd {hotel['address']}\n"
        result += f"⭐ {hotel.get('star_rating', 4.0)}/5 - Diem danh gia: {hotel.get('review_score', 8.0)}/10 ({hotel.get('review_count', 0):,} danh gia)\n"

        amenities = hotel.get('amenities', [])
        if amenities:
            result += f"\U0001f381 Tien ich: {', '.join(amenities)}\n"

        result += f"\U0001f6cf  Con {hotel.get('available_rooms', 0)} phong trong\n"

        price = float(hotel['price'])
        original_price = hotel.get('original_price')
        discount = hotel.get('discount', 0)

        if original_price and discount > 0:
            result += f"\U0001f4b0 Gia: {price:,.0f} VND (giam {discount}% tu {float(original_price):,.0f} VND)\n"
        else:
            result += f"\U0001f4b0 Gia: {price:,.0f} VND/phong/dem\n"

        result += f"\U0001f194 ID: {hotel['hotel_id']}\n"
        return result

    async def search_hotels(
        self,
        location: str = "",
        min_price: float = 0,
        max_price: float = 0,
        limit: int = 5
    ) -> str:
        """Tim kiem khach san tu database"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Match theo thành phố (location), tên KS, hoặc tên tỉnh
                    # (province_name / province_name_en) để "Đà Lạt", "Lâm Đồng",
                    # "lam_dong" đều tìm được.
                    sql = ("SELECT h.* FROM hotels h "
                           "LEFT JOIN provinces p ON h.province_id = p.province_id "
                           "WHERE h.is_active = TRUE")
                    params = []

                    if location:
                        sql += """ AND (
                            h.location ILIKE %s OR h.hotel_name ILIKE %s
                            OR p.province_name ILIKE %s OR p.province_name_en ILIKE %s
                        )"""
                        pat = f"%{location}%"
                        params += [pat, pat, pat, pat]
                    if min_price > 0:
                        sql += " AND h.price >= %s"
                        params.append(min_price)
                    if max_price > 0:
                        sql += " AND h.price <= %s"
                        params.append(max_price)

                    sql += " ORDER BY h.review_score DESC LIMIT %s"
                    params.append(min(limit, 20))

                    cur.execute(sql, params)
                    hotels = [dict(row) for row in cur.fetchall()]

            if not hotels:
                return "Khong tim thay khach san" + (f" tai {location}" if location else "") + "."

            loc_text = f" tai {location}" if location else ""
            result = f"\U0001f3e8 KET QUA TIM KIEM KHACH SAN{loc_text}\n"
            result += "=" * 50 + "\n"
            result += f"Tim thay: {len(hotels)} khach san\n"
            result += "=" * 50 + "\n\n"

            for i, hotel in enumerate(hotels, 1):
                result += self._format_hotel_info(hotel, i, len(hotels))
                result += "\n"

            result += "=" * 50 + "\n"
            result += "\U0001f4a1 Goi y: Su dung book_hotel de dat phong\n"
            return result

        except Exception as e:
            return f"Loi tim kiem khach san: {str(e)}"

    async def get_hotel_details(self, hotel_id: str) -> str:
        """Lay chi tiet 1 khach san"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM hotels WHERE hotel_id = %s AND is_active = TRUE", (hotel_id,))
                    row = cur.fetchone()

            if not row:
                return f"Khong tim thay khach san voi ID {hotel_id}."

            hotel = dict(row)
            result = self._format_hotel_info(hotel, 1, 1)
            if hotel.get('description'):
                result += f"\n\U0001f4dd Mo ta: {hotel['description']}\n"
            result += "\n\U0001f4a1 Su dung book_hotel de dat phong tai day"
            return result

        except Exception as e:
            return f"Loi lay chi tiet khach san: {str(e)}"

    async def book_hotel(
        self,
        hotel_id: str,
        guest_name: str,
        guest_phone: str,
        guest_email: str,
        check_in: str,
        check_out: str,
        num_rooms: int = 1,
        num_guests: int = 1,
        user_id: Optional[str] = None
    ) -> str:
        """Dat phong khach san va luu vao database"""
        try:
            # Check hotel exists and has rooms
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM hotels WHERE hotel_id = %s AND is_active = TRUE", (hotel_id,))
                    hotel = cur.fetchone()

            if not hotel:
                return f"Khong tim thay khach san voi ID {hotel_id}."

            hotel = dict(hotel)
            if hotel['available_rooms'] < num_rooms:
                return f"Khach san chi con {hotel['available_rooms']} phong, khong du {num_rooms} phong."

            # Calculate total price
            check_in_date = datetime.strptime(check_in, "%Y-%m-%d").date()
            check_out_date = datetime.strptime(check_out, "%Y-%m-%d").date()
            nights = (check_out_date - check_in_date).days
            if nights <= 0:
                return "Ngay tra phong phai sau ngay nhan phong."

            total_price = float(hotel['price']) * nights * num_rooms
            booking_id = f"HTL-{uuid.uuid4().hex[:8].upper()}"

            # Insert booking
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO hotel_bookings
                        (booking_id, hotel_id, user_id, guest_name, guest_phone, guest_email,
                         check_in, check_out, num_rooms, num_guests, total_price, status, payment_status)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (booking_id) DO NOTHING""",
                        (booking_id, hotel_id, user_id, guest_name, guest_phone, guest_email,
                         check_in_date, check_out_date, num_rooms, num_guests,
                         total_price, "pending_payment", "unpaid"))
                    # Update available rooms
                    cur.execute(
                        "UPDATE hotels SET available_rooms = available_rooms - %s WHERE hotel_id = %s",
                        (num_rooms, hotel_id))
                    conn.commit()

            result = "✅ DAT PHONG THANH CONG!\n"
            result += "=" * 40 + "\n"
            result += f"\U0001f4cb Ma dat phong: {booking_id}\n"
            result += f"\U0001f3e8 Khach san: {hotel['hotel_name']}\n"
            result += f"\U0001f4cd Dia diem: {hotel['location']}\n\n"
            result += f"\U0001f464 Khach: {guest_name}\n"
            result += f"\U0001f4f1 Dien thoai: {guest_phone}\n"
            result += f"\U0001f4e7 Email: {guest_email}\n\n"
            result += f"\U0001f4c5 Nhan phong: {check_in}\n"
            result += f"\U0001f4c5 Tra phong: {check_out}\n"
            result += f"\U0001f6cf  So phong: {num_rooms}\n"
            result += f"\U0001f465 So khach: {num_guests}\n"
            result += f"\U0001f4b0 Tong tien: {total_price:,.0f} VND ({nights} dem x {num_rooms} phong)\n\n"
            result += "⏰ Trang thai: Cho thanh toan\n"
            result += "=" * 40
            return result

        except Exception as e:
            return f"Loi dat phong: {str(e)}"

    async def get_hotel_locations(self) -> str:
        """Lay danh sach dia diem co khach san"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT DISTINCT location FROM hotels WHERE is_active = TRUE ORDER BY location")
                    locations = [row['location'] for row in cur.fetchall()]

            if not locations:
                return "Hien chua co khach san nao."

            result = "\U0001f4cd DANH SACH DIA DIEM CO KHACH SAN\n"
            result += "=" * 40 + "\n\n"
            for loc in locations:
                result += f"   • {loc}\n"
            result += "\n\U0001f4a1 Su dung search_hotels(location='...') de tim kiem"
            return result

        except Exception as e:
            return f"Loi lay dia diem: {str(e)}"


def register_hotel_tools(mcp: FastMCP):
    """Register hotel tools voi FastMCP server"""

    hotel_service = HotelMCPService()

    @mcp.tool()
    async def search_hotels(
        location: str = "",
        min_price: float = 0,
        max_price: float = 0,
        limit: int = 5,
    ) -> str:
        """
        Tim kiem khach san tai Viet Nam va khu vuc.

        Args:
            location: Dia diem tim kiem (vd: 'Bandung', 'Bali', 'Garut')
            min_price: Gia toi thieu (VND), mac dinh 0
            max_price: Gia toi da (VND), 0 = khong gioi han
            limit: So ket qua toi da (1-20)

        Returns:
            Danh sach khach san voi gia, tien ich, so phong trong
        """
        return await hotel_service.search_hotels(
            location=location,
            min_price=min_price,
            max_price=max_price,
            limit=limit
        )

    @mcp.tool()
    async def get_hotel_details(hotel_id: str) -> str:
        """
        Lay chi tiet 1 khach san theo ID.

        Args:
            hotel_id: ID cua khach san

        Returns:
            Thong tin chi tiet khach san
        """
        return await hotel_service.get_hotel_details(hotel_id=hotel_id)

    @mcp.tool()
    async def book_hotel(
        hotel_id: str,
        guest_name: str,
        guest_phone: str,
        guest_email: str,
        check_in: str,
        check_out: str,
        num_rooms: int = 1,
        num_guests: int = 1,
        user_id: Optional[str] = None
    ) -> str:
        """
        Dat phong khach san.

        Args:
            hotel_id: ID khach san tu ket qua search
            guest_name: Ho ten khach
            guest_phone: So dien thoai
            guest_email: Email
            check_in: Ngay nhan phong (YYYY-MM-DD)
            check_out: Ngay tra phong (YYYY-MM-DD)
            num_rooms: So phong (mac dinh 1)
            num_guests: So khach (mac dinh 1)
            user_id: ID user (tu dong inject)

        Returns:
            Thong tin dat phong va ma booking
        """
        return await hotel_service.book_hotel(
            hotel_id=hotel_id,
            guest_name=guest_name,
            guest_phone=guest_phone,
            guest_email=guest_email,
            check_in=check_in,
            check_out=check_out,
            num_rooms=num_rooms,
            num_guests=num_guests,
            user_id=user_id
        )

    @mcp.tool()
    async def get_hotel_locations() -> str:
        """
        Lay danh sach dia diem co khach san.

        Returns:
            Danh sach dia diem ho tro
        """
        return await hotel_service.get_hotel_locations()
