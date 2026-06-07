"""
Flight Tools - MCP Tools cho tìm kiếm và đặt vé máy bay
Sử dụng Mock Data Generator
"""

from fastmcp import FastMCP
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
from app.v1.core.config import settings

try:
    from ..mock_data.generator import get_generator
    from ..mock_data.flight_data import VIETNAM_AIRPORTS, VIETNAM_AIRLINES
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from mock_data.generator import get_generator
    from mock_data.flight_data import VIETNAM_AIRPORTS, VIETNAM_AIRLINES


class FlightService:
    """Flight Service sử dụng Mock Data Generator"""

    def __init__(self):
        self.generator = get_generator()
        self.vietnam_tz = timezone(timedelta(hours=7))

    def _format_flight_info(self, flight: Dict[str, Any], index: int, total: int) -> str:
        """Format flight info thành string đẹp"""
        result = f"✈️  Chuyến bay {index}/{total}\n"
        result += "─" * 50 + "\n"
        result += f"🛫 {flight['flight_number']} - {flight['airline']['name']}\n"
        result += f"📅 {flight['departure']['date']}\n\n"

        result += f"🛫 Khởi hành: {flight['departure']['time']}\n"
        result += f"   {flight['departure']['airport']} ({flight['departure']['iata']})\n"
        result += f"   Terminal {flight['departure']['terminal']}\n\n"

        result += f"🛬 Đến: {flight['arrival']['time']}\n"
        result += f"   {flight['arrival']['airport']} ({flight['arrival']['iata']})\n"
        result += f"   Terminal {flight['arrival']['terminal']}\n\n"

        result += f"⏱️  Thời gian bay: {flight['duration_formatted']}\n"
        result += f"💺 Ghế còn: {flight['available_seats']} chỗ\n"
        result += f"🧳 Hành lý: Xách tay {flight['baggage']['carry_on']}, Ký gửi {flight['baggage']['checked']}\n\n"

        result += f"💰 Giá vé:\n"
        result += f"   • Economy: {flight['price']['economy']:,} VND\n"
        result += f"   • Business: {flight['price']['business']:,} VND\n"

        return result

    def _get_airport_list(self) -> str:
        """Trả về danh sách sân bay"""
        result = "📋 Danh sách sân bay hỗ trợ:\n"
        for code, info in VIETNAM_AIRPORTS.items():
            result += f"   • {code}: {info['name']} ({info['city']})\n"
        return result

    async def search_flights(
        self,
        departure_iata: str,
        arrival_iata: str,
        date: Optional[str] = None,
        limit: int = 5
    ) -> str:
        """
        Tìm kiếm chuyến bay

        Args:
            departure_iata: Mã sân bay đi (SGN, HAN, DAD, ...)
            arrival_iata: Mã sân bay đến
            date: Ngày bay (YYYY-MM-DD), mặc định là hôm nay
            limit: Số kết quả tối đa
        """
        departure_iata = departure_iata.upper()
        arrival_iata = arrival_iata.upper()
        limit = max(1, min(limit, 10))

        # Ngày mặc định là hôm nay
        if not date:
            date = datetime.now(self.vietnam_tz).strftime("%Y-%m-%d")

        # Validate airports
        if departure_iata not in VIETNAM_AIRPORTS:
            return f"❌ Không tìm thấy sân bay với mã {departure_iata}.\n\n" + self._get_airport_list()

        if arrival_iata not in VIETNAM_AIRPORTS:
            return f"❌ Không tìm thấy sân bay với mã {arrival_iata}.\n\n" + self._get_airport_list()

        if departure_iata == arrival_iata:
            return "❌ Sân bay đi và đến không được trùng nhau."

        # Generate flights
        flights = self.generator.generate_flights(
            departure_iata=departure_iata,
            arrival_iata=arrival_iata,
            date=date,
            days_ahead=1,
            limit=limit
        )

        if not flights:
            return f"❌ Không tìm thấy chuyến bay từ {departure_iata} đến {arrival_iata} ngày {date}."

        # Filter future flights only
        current_time = datetime.now(self.vietnam_tz)
        if date == current_time.strftime("%Y-%m-%d"):
            flights = [f for f in flights if datetime.fromisoformat(f["departure"]["scheduled"]) > current_time]

        if not flights:
            return f"❌ Không còn chuyến bay nào từ {departure_iata} đến {arrival_iata} trong ngày {date}."

        # Format output
        dep_city = VIETNAM_AIRPORTS[departure_iata]["city"]
        arr_city = VIETNAM_AIRPORTS[arrival_iata]["city"]

        result = f"✈️  KẾT QUẢ TÌM KIẾM CHUYẾN BAY\n"
        result += "=" * 50 + "\n"
        result += f"📍 {dep_city} ({departure_iata}) → {arr_city} ({arrival_iata})\n"
        result += f"📅 Ngày: {date}\n"
        result += f"🔍 Tìm thấy: {len(flights)} chuyến bay\n"
        result += "=" * 50 + "\n\n"

        for i, flight in enumerate(flights, 1):
            result += self._format_flight_info(flight, i, len(flights))
            result += "\n"

        result += "=" * 50 + "\n"
        result += "💡 Gợi ý: Sử dụng book_flight để đặt vé\n"

        return result

    async def search_flights_json(
        self,
        departure_iata: str,
        arrival_iata: str,
        date: Optional[str] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """Trả về kết quả dạng JSON cho frontend"""
        departure_iata = departure_iata.upper()
        arrival_iata = arrival_iata.upper()

        if not date:
            date = datetime.now(self.vietnam_tz).strftime("%Y-%m-%d")

        if departure_iata not in VIETNAM_AIRPORTS or arrival_iata not in VIETNAM_AIRPORTS:
            return {"success": False, "error": "Invalid airport code", "flights": []}

        if departure_iata == arrival_iata:
            return {"success": False, "error": "Same departure and arrival", "flights": []}

        flights = self.generator.generate_flights(
            departure_iata=departure_iata,
            arrival_iata=arrival_iata,
            date=date,
            days_ahead=1,
            limit=limit
        )

        return {
            "success": True,
            "departure": {
                "iata": departure_iata,
                "city": VIETNAM_AIRPORTS[departure_iata]["city"],
                "airport": VIETNAM_AIRPORTS[departure_iata]["name"]
            },
            "arrival": {
                "iata": arrival_iata,
                "city": VIETNAM_AIRPORTS[arrival_iata]["city"],
                "airport": VIETNAM_AIRPORTS[arrival_iata]["name"]
            },
            "date": date,
            "total": len(flights),
            "flights": flights
        }

    async def book_flight(
        self,
        flight_id: str,
        passenger_name: str,
        passenger_phone: str,
        passenger_email: str,
        seat_class: str = "economy",
        num_passengers: int = 1,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Đặt vé máy bay và lưu vào PostgreSQL"""
        if seat_class not in ("economy", "business", "first_class"):
            return {"success": False, "error": "Hạng ghế không hợp lệ. Hỗ trợ: economy, business, first_class"}
        if num_passengers < 1:
            return {"success": False, "error": "Số hành khách phải >= 1"}

        result = self.generator.generate_flight_booking(
            flight_id=flight_id,
            passenger_name=passenger_name,
            passenger_phone=passenger_phone,
            passenger_email=passenger_email,
            seat_class=seat_class,
            num_passengers=num_passengers
        )

        if not result.get("success"):
            return result

        try:
            with psycopg2.connect(settings.DATABASE_URL, cursor_factory=RealDictCursor) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO flight_bookings (booking_id, flight_id, user_id, passenger_name, passenger_phone, passenger_email, seat_class, num_passengers, total_price, status, payment_status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (booking_id) DO NOTHING",
                        (result["booking_id"], flight_id, user_id, passenger_name, passenger_phone, passenger_email, seat_class, num_passengers, result["total_price"], "pending_payment", "unpaid")
                    )
                    conn.commit()
        except Exception as e:
            return {"success": False, "error": f"Lưu booking thất bại: {str(e)}"}

        result["booking_type"] = "flight"
        result["payment_status"] = "unpaid"
        result["next_action"] = "create_transport_payment"
        return result


def register_flight_tools(mcp: FastMCP):
    """Register flight tools với FastMCP server"""

    flight_service = FlightService()

    @mcp.tool()
    async def search_flights(
        departure_iata: str,
        arrival_iata: str,
        date: str = "",
        limit: int = 5,
    ) -> str:
        """
        Tìm kiếm chuyến bay nội địa Việt Nam.

        Args:
            departure_iata: Mã sân bay đi (SGN, HAN, DAD, CXR, PQC, DLI, ...)
            arrival_iata: Mã sân bay đến
            date: Ngày bay (YYYY-MM-DD), để trống = hôm nay
            limit: Số kết quả tối đa (1-10)

        Returns:
            Danh sách chuyến bay với giá vé, thời gian, hãng bay
        """
        return await flight_service.search_flights(
            departure_iata=departure_iata,
            arrival_iata=arrival_iata,
            date=date if date else None,
            limit=limit
        )

    @mcp.tool()
    async def search_flights_json(
        departure_iata: str,
        arrival_iata: str,
        date: str = "",
        limit: int = 5,
    ) -> Dict[str, Any]:
        """
        Tìm kiếm chuyến bay - trả về JSON cho frontend.

        Args:
            departure_iata: Mã sân bay đi
            arrival_iata: Mã sân bay đến
            date: Ngày bay (YYYY-MM-DD)
            limit: Số kết quả tối đa
        """
        return await flight_service.search_flights_json(
            departure_iata=departure_iata,
            arrival_iata=arrival_iata,
            date=date if date else None,
            limit=limit
        )

    @mcp.tool()
    async def book_flight(
        flight_id: str,
        passenger_name: str,
        passenger_phone: str,
        passenger_email: str,
        seat_class: str = "economy",
        num_passengers: int = 1,
        user_id: Optional[str] = None
    ) -> str:
        """
        Đặt vé máy bay.

        Args:
            flight_id: ID chuyến bay từ kết quả search
            passenger_name: Họ tên hành khách
            passenger_phone: Số điện thoại
            passenger_email: Email
            seat_class: Hạng ghế (economy/business/first_class)
            num_passengers: Số hành khách
            user_id: ID user (tự động inject nếu có)

        Returns:
            Thông tin đặt vé và mã booking
        """
        result = await flight_service.book_flight(
            flight_id=flight_id,
            passenger_name=passenger_name,
            passenger_phone=passenger_phone,
            passenger_email=passenger_email,
            seat_class=seat_class,
            num_passengers=num_passengers,
            user_id=user_id
        )

        if result["success"]:
            return f"""
✅ ĐẶT VÉ MÁY BAY THÀNH CÔNG!
{'=' * 40}
📋 Mã đặt chỗ: {result['booking_id']}
✈️  Chuyến bay: {result['flight_id']}

👤 Hành khách: {result['passenger']['name']}
📱 Điện thoại: {result['passenger']['phone']}
📧 Email: {result['passenger']['email']}

💺 Hạng ghế: {result['seat_class'].title()}
👥 Số người: {result['num_passengers']}
💰 Tổng tiền: {result['total_price']:,} VND

⏰ Trạng thái: Chờ thanh toán
🔔 Tiếp theo: Gọi create_transport_payment(booking_type="flight", booking_id="{result['booking_id']}") để tạo link thanh toán.
{'=' * 40}
"""
        else:
            return f"❌ Đặt vé thất bại: {result.get('error', 'Unknown error')}"

    @mcp.tool()
    async def get_airports() -> str:
        """
        Lấy danh sách sân bay Việt Nam được hỗ trợ.

        Returns:
            Danh sách mã sân bay và thông tin
        """
        result = "🛫 DANH SÁCH SÂN BAY VIỆT NAM\n"
        result += "=" * 40 + "\n\n"

        for code, info in VIETNAM_AIRPORTS.items():
            result += f"✈️  {code} - {info['name']}\n"
            result += f"   📍 {info['city']}\n"
            result += f"   🏢 Terminal: {', '.join(info['terminals'])}\n\n"

        return result
