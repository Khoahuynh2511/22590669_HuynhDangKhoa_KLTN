"""
Bus Tools - MCP Tools cho tìm kiếm và đặt vé xe khách
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
    from ..mock_data.bus_data import BUS_STATIONS, BUS_SEAT_TYPES
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from mock_data.generator import get_generator
    from mock_data.bus_data import BUS_STATIONS, BUS_SEAT_TYPES


class BusService:
    """Bus Service sử dụng Mock Data Generator"""

    def __init__(self):
        self.generator = get_generator()
        self.vietnam_tz = timezone(timedelta(hours=7))

    def _format_bus_info(self, bus: Dict[str, Any], index: int, total: int) -> str:
        """Format bus info thành string đẹp"""
        result = f"🚌 Chuyến xe {index}/{total}\n"
        result += "─" * 50 + "\n"
        result += f"🚍 {bus['bus_number']} - {bus['company']['name']}\n"
        result += f"📋 {bus['bus_type']['name']} ({bus['bus_type']['capacity']} chỗ)\n"
        result += f"📅 {bus['departure']['date']}\n\n"

        result += f"🚉 Bến đi: {bus['departure']['time']}\n"
        result += f"   {bus['departure']['station']} ({bus['departure']['code']})\n"
        result += f"   📍 {bus['departure']['address']}\n\n"

        result += f"🏁 Bến đến: {bus['arrival']['time']}"
        if bus['departure']['date'] != bus['arrival']['date']:
            result += " (+1 ngày)"
        result += "\n"
        result += f"   {bus['arrival']['station']} ({bus['arrival']['code']})\n"
        result += f"   📍 {bus['arrival']['address']}\n\n"

        result += f"⏱️  Thời gian: {bus['duration_formatted']}\n"
        result += f"🏢 Hãng xe: {bus['company']['name']} ⭐ {bus['company']['rating']}\n"
        result += f"🎯 Tiện ích: {', '.join(bus['bus_type']['amenities'])}\n"
        result += f"💺 Còn {bus['available_seats']}/{bus['total_seats']} chỗ\n\n"

        result += "💰 Giá vé:\n"
        for seat_code, seat_info in bus['seats'].items():
            available = bus['availability'].get(seat_code, 0)
            status = f"({available} chỗ)" if available > 0 else "(Hết chỗ)"
            result += f"   • {seat_info['name']}: {seat_info['price']:,} VND {status}\n"

        return result

    def _get_station_list(self) -> str:
        """Trả về danh sách bến xe"""
        result = "📋 Danh sách bến xe hỗ trợ:\n"
        for code, info in BUS_STATIONS.items():
            result += f"   • {code}: {info['name']} ({info['city']})\n"
        return result

    async def search_buses(
        self,
        departure_station: str,
        arrival_station: str,
        date: Optional[str] = None,
        limit: int = 5
    ) -> str:
        """Tìm kiếm chuyến xe khách"""
        departure_station = departure_station.upper()
        arrival_station = arrival_station.upper()
        limit = max(1, min(limit, 10))

        if not date:
            date = datetime.now(self.vietnam_tz).strftime("%Y-%m-%d")

        if departure_station not in BUS_STATIONS:
            return f"❌ Không tìm thấy bến xe với mã {departure_station}.\n\n" + self._get_station_list()

        if arrival_station not in BUS_STATIONS:
            return f"❌ Không tìm thấy bến xe với mã {arrival_station}.\n\n" + self._get_station_list()

        if departure_station == arrival_station:
            return "❌ Bến đi và bến đến không được trùng nhau."

        buses = self.generator.generate_buses(
            departure_station=departure_station,
            arrival_station=arrival_station,
            date=date,
            days_ahead=1,
            limit=limit
        )

        if not buses:
            return f"❌ Không tìm thấy chuyến xe từ {departure_station} đến {arrival_station} ngày {date}.\n\n" + \
                "💡 Gợi ý: Thử các tuyến phổ biến như BXSG-BXHN, BXSG-BXDL, BXHN-BXDN"

        # Filter future buses only (for today)
        current_time = datetime.now(self.vietnam_tz)
        if date == current_time.strftime("%Y-%m-%d"):
            buses = [b for b in buses if datetime.fromisoformat(b["departure"]["scheduled"]) > current_time]

        if not buses:
            return f"❌ Không còn chuyến xe nào từ {departure_station} đến {arrival_station} trong ngày {date}.\n" + \
                "💡 Gợi ý: Thử tìm cho ngày mai"

        dep_city = BUS_STATIONS[departure_station]["city"]
        arr_city = BUS_STATIONS[arrival_station]["city"]

        result = "🚌 KẾT QUẢ TÌM KIẾM CHUYẾN XE\n"
        result += "=" * 50 + "\n"
        result += f"📍 {dep_city} ({departure_station}) → {arr_city} ({arrival_station})\n"
        result += f"📅 Ngày: {date}\n"
        result += f"🔍 Tìm thấy: {len(buses)} chuyến xe\n"
        result += "=" * 50 + "\n\n"

        for i, bus in enumerate(buses, 1):
            result += self._format_bus_info(bus, i, len(buses))
            result += "\n"

        result += "=" * 50 + "\n"
        result += "💡 Gợi ý: Sử dụng book_bus để đặt vé\n"

        return result

    async def search_buses_json(
        self,
        departure_station: str,
        arrival_station: str,
        date: Optional[str] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """Trả về kết quả dạng JSON cho frontend"""
        departure_station = departure_station.upper()
        arrival_station = arrival_station.upper()

        if not date:
            date = datetime.now(self.vietnam_tz).strftime("%Y-%m-%d")

        if departure_station not in BUS_STATIONS or arrival_station not in BUS_STATIONS:
            return {"success": False, "error": "Invalid station code", "buses": []}

        if departure_station == arrival_station:
            return {"success": False, "error": "Same departure and arrival", "buses": []}

        buses = self.generator.generate_buses(
            departure_station=departure_station,
            arrival_station=arrival_station,
            date=date,
            days_ahead=1,
            limit=limit
        )

        return {
            "success": True,
            "departure": {
                "code": departure_station,
                "city": BUS_STATIONS[departure_station]["city"],
                "station": BUS_STATIONS[departure_station]["name"]
            },
            "arrival": {
                "code": arrival_station,
                "city": BUS_STATIONS[arrival_station]["city"],
                "station": BUS_STATIONS[arrival_station]["name"]
            },
            "date": date,
            "total": len(buses),
            "buses": buses,
            "seat_types": BUS_SEAT_TYPES
        }

    async def book_bus(
        self,
        bus_id: str,
        passenger_name: str,
        passenger_phone: str,
        passenger_email: str,
        seat_type: str = "standard",
        num_passengers: int = 1,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Đặt vé xe khách và lưu vào PostgreSQL"""
        if seat_type not in BUS_SEAT_TYPES:
            return {
                "success": False,
                "error": f"Loại ghế không hợp lệ. Các loại hỗ trợ: {', '.join(BUS_SEAT_TYPES.keys())}"
            }
        if num_passengers < 1:
            return {"success": False, "error": "Số hành khách phải >= 1"}

        result = self.generator.generate_bus_booking(
            bus_id=bus_id,
            passenger_name=passenger_name,
            passenger_phone=passenger_phone,
            passenger_email=passenger_email,
            seat_type=seat_type,
            num_passengers=num_passengers
        )

        if not result.get("success"):
            return result

        try:
            with psycopg2.connect(settings.DATABASE_URL, cursor_factory=RealDictCursor) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO bus_bookings (booking_id, bus_id, user_id, passenger_name, passenger_phone, passenger_email, seat_type_id, num_passengers, total_price, status, payment_status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (booking_id) DO NOTHING",
                        (result["booking_id"],
                         bus_id,
                         user_id,
                         passenger_name,
                         passenger_phone,
                         passenger_email,
                         seat_type,
                         num_passengers,
                         result["total_price"],
                            "pending_payment",
                            "unpaid"))
                    conn.commit()
        except Exception as e:
            return {"success": False, "error": f"Lưu booking thất bại: {str(e)}"}

        result["booking_type"] = "bus"
        result["payment_status"] = "unpaid"
        result["next_action"] = "payment_not_supported"
        return result


def register_bus_tools(mcp: FastMCP):
    """Register bus tools với FastMCP server"""

    bus_service = BusService()

    @mcp.tool()
    async def search_buses(
        departure_station: str,
        arrival_station: str,
        date: str = "",
        limit: int = 5,
    ) -> str:
        """
        Tìm kiếm chuyến xe khách Việt Nam.

        Args:
            departure_station: Mã bến xe đi (BXSG=HCM, BXHN=Hà Nội, BXDN=Đà Nẵng, BXNT=Nha Trang, BXDL=Đà Lạt, ...)
            arrival_station: Mã bến xe đến
            date: Ngày đi (YYYY-MM-DD), để trống = hôm nay
            limit: Số kết quả tối đa (1-10)

        Returns:
            Danh sách chuyến xe với giá vé, thời gian, tiện ích
        """
        return await bus_service.search_buses(
            departure_station=departure_station,
            arrival_station=arrival_station,
            date=date if date else None,
            limit=limit
        )

    @mcp.tool()
    async def search_buses_json(
        departure_station: str,
        arrival_station: str,
        date: str = "",
        limit: int = 5,
    ) -> Dict[str, Any]:
        """
        Tìm kiếm chuyến xe khách - trả về JSON cho frontend.
        """
        return await bus_service.search_buses_json(
            departure_station=departure_station,
            arrival_station=arrival_station,
            date=date if date else None,
            limit=limit
        )

    @mcp.tool()
    async def book_bus(
        bus_id: str,
        passenger_name: str,
        passenger_phone: str,
        passenger_email: str,
        seat_type: str = "standard",
        num_passengers: int = 1,
        user_id: Optional[str] = None
    ) -> str:
        """
        Đặt vé xe khách.

        Args:
            bus_id: ID chuyến xe từ kết quả search
            passenger_name: Họ tên hành khách
            passenger_phone: Số điện thoại
            passenger_email: Email
            seat_type: Loại ghế (standard, premium, single_sleeper, double_sleeper)
            num_passengers: Số hành khách
            user_id: ID user (tự động inject nếu có)

        Returns:
            Thông tin đặt vé và mã booking
        """
        result = await bus_service.book_bus(
            bus_id=bus_id,
            passenger_name=passenger_name,
            passenger_phone=passenger_phone,
            passenger_email=passenger_email,
            seat_type=seat_type,
            num_passengers=num_passengers,
            user_id=user_id
        )

        if result["success"]:
            return f"""
✅ ĐẶT VÉ XE THÀNH CÔNG!
{'=' * 40}
📋 Mã đặt chỗ: {result['booking_id']}
🚌 Chuyến xe: {result['bus_id']}

👤 Hành khách: {result['passenger']['name']}
📱 Điện thoại: {result['passenger']['phone']}
📧 Email: {result['passenger']['email']}

💺 Loại ghế: {result['seat_type']['name']}
👥 Số người: {result['num_passengers']}
💰 Tổng tiền: {result['total_price']:,} VND

⏰ Trạng thái: Chờ thanh toán
🔔 Tiếp theo: Thanh toán online cho vé xe bus chưa được hỗ trợ bởi create_transport_payment. Vui lòng chờ xử lý thanh toán.
{'=' * 40}
"""
        else:
            return f"❌ Đặt vé thất bại: {result.get('error', 'Unknown error')}"

    @mcp.tool()
    async def get_bus_stations() -> str:
        """
        Lấy danh sách bến xe Việt Nam được hỗ trợ.

        Returns:
            Danh sách mã bến xe và thông tin
        """
        result = "🚏 DANH SÁCH BẾN XE VIỆT NAM\n"
        result += "=" * 40 + "\n\n"

        regions = {"north": "Miền Bắc", "central": "Miền Trung", "south": "Miền Nam"}

        for region_code, region_name in regions.items():
            result += f"📍 {region_name}:\n"
            for code, info in BUS_STATIONS.items():
                if info["region"] == region_code:
                    result += f"   🚏 {code} - {info['name']}\n"
                    result += f"      📍 {info['city']}\n"
                    result += f"      🏠 {info['address']}\n"
            result += "\n"

        return result
