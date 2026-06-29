"""
Train Tools - MCP Tools cho tìm kiếm và đặt vé tàu hỏa
Sử dụng Mock Data Generator
"""

from fastmcp import FastMCP
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
from app.v1.core.config import settings
from app.v1.services.train_search_service import TrainSearchService

try:
    from ..mock_data.generator import get_generator
    from ..mock_data.train_data import TRAIN_STATIONS, SEAT_TYPES
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from mock_data.generator import get_generator
    from mock_data.train_data import TRAIN_STATIONS, SEAT_TYPES


def get_or_create_user_id(passenger_phone: str, passenger_email: str, user_id: Optional[str] = None) -> str:
    """Resolve user_id from passenger info or create a new user profile if not exists"""
    import uuid
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from app.v1.core.config import settings
    
    phone_digits = ''.join(filter(str.isdigit, passenger_phone))
    if len(phone_digits) == 10:
        passenger_phone = phone_digits
        
    try:
        with psycopg2.connect(settings.DATABASE_URL, cursor_factory=RealDictCursor) as conn:
            with conn.cursor() as cur:
                # 1. Try to find user by user_id
                if user_id:
                    cur.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
                    row = cur.fetchone()
                    if row:
                        return str(row['user_id'])
                
                # 2. Try to find user by phone_number
                cur.execute("SELECT user_id FROM users WHERE phone_number = %s", (passenger_phone,))
                row = cur.fetchone()
                if row:
                    return str(row['user_id'])
                
                # 3. Try to find user by email
                cur.execute("SELECT user_id FROM users WHERE email = %s", (passenger_email,))
                row = cur.fetchone()
                if row:
                    return str(row['user_id'])
                
                # 4. Create new user
                new_id = user_id or str(uuid.uuid4())
                cur.execute(
                    "INSERT INTO users (user_id, phone_number, full_name, email) VALUES (%s, %s, %s, %s) RETURNING user_id",
                    (new_id, passenger_phone, f"Khách hàng {passenger_phone[-4:]}", passenger_email)
                )
                conn.commit()
                row = cur.fetchone()
                if row:
                    return str(row['user_id'])
                return new_id
    except Exception as e:
        return user_id or str(uuid.uuid4())


class TrainService:
    """Train Service - query DB thật qua TrainSearchService"""

    def __init__(self):
        self.search_service = TrainSearchService()
        self.vietnam_tz = timezone(timedelta(hours=7))

    def _format_train_info(self, train: Dict[str, Any], index: int, total: int) -> str:
        """Format train info thành string đẹp"""
        result = f"🚂 Chuyến tàu {index}/{total}\n"
        result += "─" * 50 + "\n"
        result += f"🚃 {train['train_number']} - {train['train_type']['name']}\n"
        result += f"📅 {train['departure']['date']}\n\n"

        result += f"🚉 Ga đi: {train['departure']['time']}\n"
        result += f"   {train['departure']['station']} ({train['departure']['code']})\n"
        result += f"   📍 {train['departure']['address']}\n\n"

        result += f"🏁 Ga đến: {train['arrival']['time']}"
        if train['departure']['date'] != train['arrival']['date']:
            result += " (+1 ngày)"
        result += "\n"
        result += f"   {train['arrival']['station']} ({train['arrival']['code']})\n"
        result += f"   📍 {train['arrival']['address']}\n\n"

        result += f"⏱️  Thời gian: {train['duration_formatted']}\n"
        result += f"🎯 Tiện ích: {', '.join(train['train_type']['amenities'])}\n\n"

        result += "💰 Giá vé:\n"
        for seat_code, seat_info in train['seats'].items():
            available = train['availability'].get(seat_code, 0)
            status = f"({available} chỗ)" if available > 0 else "(Hết chỗ)"
            result += f"   • {seat_info['name']}: {seat_info['price']:,} VND {status}\n"

        return result

    def _get_station_list(self) -> str:
        """Trả về danh sách ga tàu"""
        result = "📋 Danh sách ga tàu hỗ trợ:\n"
        for code, info in TRAIN_STATIONS.items():
            result += f"   • {code}: {info['name']} ({info['city']})\n"
        return result

    def _get_seat_types_info(self) -> str:
        """Trả về thông tin các loại ghế"""
        result = "💺 Các loại ghế/giường:\n"
        for code, info in SEAT_TYPES.items():
            result += f"   • {code}: {info['name']} - {info['description']}\n"
        return result

    async def search_trains(
        self,
        departure_station: str,
        arrival_station: str,
        date: Optional[str] = None,
        limit: int = 5
    ) -> str:
        """
        Tìm kiếm chuyến tàu

        Args:
            departure_station: Mã ga đi (HNO, SGO, DNA, ...)
            arrival_station: Mã ga đến
            date: Ngày đi (YYYY-MM-DD), mặc định là hôm nay
            limit: Số kết quả tối đa
        """
        departure_station = departure_station.upper()
        arrival_station = arrival_station.upper()
        limit = max(1, min(limit, 10))

        # Ngày mặc định là hôm nay
        if not date:
            date = datetime.now(self.vietnam_tz).strftime("%Y-%m-%d")

        # Validate stations
        if departure_station not in TRAIN_STATIONS:
            return f"❌ Không tìm thấy ga tàu với mã {departure_station}.\n\n" + self._get_station_list()

        if arrival_station not in TRAIN_STATIONS:
            return f"❌ Không tìm thấy ga tàu với mã {arrival_station}.\n\n" + self._get_station_list()

        if departure_station == arrival_station:
            return "❌ Ga đi và ga đến không được trùng nhau."

        # Query DB thật qua TrainSearchService (search & book dùng chung nguồn DB)
        result = self.search_service.search_trains(
            departure=departure_station,
            arrival=arrival_station,
            date=date,
            limit=limit
        )
        if result["EC"] != 0:
            return f"❌ {result['EM']}\n\n" + self._get_station_list()

        trains = result["data"].get("trains", []) if result.get("data") else []

        if not trains:
            return f"❌ Không tìm thấy chuyến tàu từ {departure_station} đến {arrival_station} ngày {date}.\n\n" + \
                "💡 Gợi ý: Thử các tuyến phổ biến như HNO-SGO, HNO-DNA, SGO-NTR"

        # Filter future trains only (for today)
        current_time = datetime.now(self.vietnam_tz)
        if date == current_time.strftime("%Y-%m-%d"):
            trains = [t for t in trains if datetime.fromisoformat(t["departure"]["scheduled"]) > current_time]

        if not trains:
            return f"❌ Không còn chuyến tàu nào từ {departure_station} đến {arrival_station} trong ngày {date}.\n" + \
                "💡 Gợi ý: Thử tìm cho ngày mai"

        # Format output
        dep_city = TRAIN_STATIONS[departure_station]["city"]
        arr_city = TRAIN_STATIONS[arrival_station]["city"]

        result = "🚂 KẾT QUẢ TÌM KIẾM CHUYẾN TÀU\n"
        result += "=" * 50 + "\n"
        result += f"📍 {dep_city} ({departure_station}) → {arr_city} ({arrival_station})\n"
        result += f"📅 Ngày: {date}\n"
        result += f"🔍 Tìm thấy: {len(trains)} chuyến tàu\n"
        result += "=" * 50 + "\n\n"

        for i, train in enumerate(trains, 1):
            result += self._format_train_info(train, i, len(trains))
            result += "\n"

        result += "=" * 50 + "\n"
        result += "💡 Gợi ý: Sử dụng book_train để đặt vé\n"
        result += self._get_seat_types_info()

        return result

    async def search_trains_json(
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

        if departure_station not in TRAIN_STATIONS or arrival_station not in TRAIN_STATIONS:
            return {"success": False, "error": "Invalid station code", "trains": []}

        if departure_station == arrival_station:
            return {"success": False, "error": "Same departure and arrival", "trains": []}

        result = self.search_service.search_trains(
            departure=departure_station,
            arrival=arrival_station,
            date=date,
            limit=limit
        )
        if result["EC"] != 0 or not result.get("data"):
            return {"success": False, "error": result.get("EM", "Search failed"), "trains": []}

        data = result["data"]
        return {
            "success": True,
            "departure": data.get("departure", {
                "code": departure_station,
                "city": TRAIN_STATIONS[departure_station]["city"],
                "station": TRAIN_STATIONS[departure_station]["name"]
            }),
            "arrival": data.get("arrival", {
                "code": arrival_station,
                "city": TRAIN_STATIONS[arrival_station]["city"],
                "station": TRAIN_STATIONS[arrival_station]["name"]
            }),
            "date": data.get("date", date),
            "total": data.get("total", len(data.get("trains", []))),
            "trains": data.get("trains", []),
            "seat_types": data.get("seat_types", SEAT_TYPES)
        }

    async def book_train(
        self,
        train_id: str,
        passenger_name: str,
        passenger_phone: str,
        passenger_email: str,
        seat_type: str = "soft_seat",
        num_passengers: int = 1,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Đặt vé tàu và lưu vào PostgreSQL"""
        if seat_type not in SEAT_TYPES:
            return {
                "success": False,
                "error": f"Loại ghế không hợp lệ. Các loại hỗ trợ: {', '.join(SEAT_TYPES.keys())}"
            }
        if num_passengers < 1:
            return {"success": False, "error": "Số hành khách phải >= 1"}

        # Resolve or create user profile to get a valid user_id
        resolved_user_id = get_or_create_user_id(passenger_phone, passenger_email, user_id)

        try:
            from app.v1.services.train_booking_service import TrainBookingService
            service = TrainBookingService()
            booking_res = await service.create_booking_with_otp({
                "train_id": train_id,
                "user_id": resolved_user_id,
                "passenger_name": passenger_name,
                "passenger_phone": passenger_phone,
                "passenger_email": passenger_email,
                "seat_type_id": seat_type,
                "num_passengers": num_passengers
            })
            
            if booking_res["EC"] != 0:
                return {"success": False, "error": booking_res["EM"]}
                
            data = booking_res["data"]
            return {
                "success": True,
                "booking_id": data["booking_id"],
                "train_id": train_id,
                "passenger": {
                    "name": passenger_name,
                    "phone": passenger_phone,
                    "email": passenger_email
                },
                "seat_type": {
                    "name": data.get("seat_type_name", seat_type)
                },
                "num_passengers": num_passengers,
                "total_price": data["total_price"],
                # otp_code chỉ có khi OTP_SHOW_IN_RESPONSE=true; dùng .get() để không crash khi false
                "otp_code": data.get("otp_code"),
                "awaiting_otp": True
            }
        except Exception as e:
            return {"success": False, "error": f"Lưu booking thất bại: {str(e)}"}


def register_train_tools(mcp: FastMCP):
    """Register train tools với FastMCP server"""

    train_service = TrainService()

    @mcp.tool()
    async def search_trains(
        departure_station: str,
        arrival_station: str,
        date: str = "",
        limit: int = 5,
    ) -> str:
        """
        Tìm kiếm chuyến tàu hỏa Việt Nam.

        Args:
            departure_station: Mã ga đi (HNO=Hà Nội, SGO=Sài Gòn, DNA=Đà Nẵng, HUE=Huế, NTR=Nha Trang, ...)
            arrival_station: Mã ga đến
            date: Ngày đi (YYYY-MM-DD), để trống = hôm nay
            limit: Số kết quả tối đa (1-10)

        Returns:
            Danh sách chuyến tàu với giá vé các loại ghế, thời gian, tiện ích
        """
        return await train_service.search_trains(
            departure_station=departure_station,
            arrival_station=arrival_station,
            date=date if date else None,
            limit=limit
        )

    @mcp.tool()
    async def search_trains_json(
        departure_station: str,
        arrival_station: str,
        date: str = "",
        limit: int = 5,
    ) -> Dict[str, Any]:
        """
        Tìm kiếm chuyến tàu - trả về JSON cho frontend.

        Args:
            departure_station: Mã ga đi
            arrival_station: Mã ga đến
            date: Ngày đi (YYYY-MM-DD)
            limit: Số kết quả tối đa
        """
        return await train_service.search_trains_json(
            departure_station=departure_station,
            arrival_station=arrival_station,
            date=date if date else None,
            limit=limit
        )

    @mcp.tool()
    async def book_train(
        train_id: str,
        passenger_name: str,
        passenger_phone: str,
        passenger_email: str,
        seat_type: str = "soft_seat",
        num_passengers: int = 1,
        user_id: Optional[str] = None
    ) -> str:
        """
        Đặt vé tàu hỏa.

        Args:
            train_id: ID chuyến tàu từ kết quả search
            passenger_name: Họ tên hành khách
            passenger_phone: Số điện thoại
            passenger_email: Email
            seat_type: Loại ghế (hard_seat, soft_seat, hard_sleeper_6, soft_sleeper_6, soft_sleeper_4, vip_cabin)
            num_passengers: Số hành khách
            user_id: ID user (tự động inject nếu có)

        Returns:
            Thông tin đặt vé và mã booking
        """
        result = await train_service.book_train(
            train_id=train_id,
            passenger_name=passenger_name,
            passenger_phone=passenger_phone,
            passenger_email=passenger_email,
            seat_type=seat_type,
            num_passengers=num_passengers,
            user_id=user_id
        )

        if result["success"]:
            return f"""
✅ ĐẶT VÉ TÀU THÀNH CÔNG (CHỜ XÁC THỰC OTP)!
{'=' * 40}
📋 Mã đặt chỗ: {result['booking_id']}
🚂 Chuyến tàu: {result['train_id']}

👤 Hành khách: {result['passenger']['name']}
📱 Điện thoại: {result['passenger']['phone']}
📧 Email: {result['passenger']['email']}

💺 Loại ghế: {result['seat_type']['name']}
👥 Số người: {result['num_passengers']}
💰 Tổng tiền: {result['total_price']:,} VND

⏰ Trạng thái: Chờ xác thực OTP
{f"🔑 Mã OTP: {result['otp_code']}" if result.get('otp_code') else "🔑 Mã OTP đã được gửi qua email — vui lòng kiểm tra hộp thư (kể cả mục Spam) để lấy mã."}
🔔 Tiếp theo: Nhập mã OTP để xác nhận đặt vé bằng verify_otp_and_confirm_booking(booking_id="{result['booking_id']}", otp_code="...").
{'=' * 40}
"""
        else:
            return f"❌ Đặt vé thất bại: {result.get('error', 'Unknown error')}"

    @mcp.tool()
    async def get_train_stations() -> str:
        """
        Lấy danh sách ga tàu Việt Nam được hỗ trợ.

        Returns:
            Danh sách mã ga và thông tin
        """
        result = "🚉 DANH SÁCH GA TÀU VIỆT NAM\n"
        result += "=" * 40 + "\n\n"

        # Group by region
        regions = {"north": "Miền Bắc", "central": "Miền Trung", "south": "Miền Nam"}

        for region_code, region_name in regions.items():
            result += f"📍 {region_name}:\n"
            for code, info in TRAIN_STATIONS.items():
                if info["region"] == region_code:
                    result += f"   🚉 {code} - {info['name']}\n"
                    result += f"      📍 {info['city']}\n"
                    result += f"      🏠 {info['address']}\n"
            result += "\n"

        return result

    @mcp.tool()
    async def get_seat_types() -> str:
        """
        Lấy thông tin các loại ghế/giường trên tàu.

        Returns:
            Danh sách loại ghế với mô tả và hệ số giá
        """
        result = "💺 CÁC LOẠI GHẾ/GIƯỜNG TRÊN TÀU\n"
        result += "=" * 40 + "\n\n"

        for code, info in SEAT_TYPES.items():
            result += f"🎫 {info['name']} ({info['code']})\n"
            result += f"   📝 {info['description']}\n"
            result += f"   💰 Hệ số giá: x{info['price_multiplier']}\n\n"

        result += "=" * 40 + "\n"
        result += "💡 Gợi ý: Giường nằm 4 người (N4M) thoải mái nhất cho chặng dài\n"

        return result
