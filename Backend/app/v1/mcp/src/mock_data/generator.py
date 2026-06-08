"""
Mock Data Generator
Tạo dữ liệu động cho Flight và Train dựa trên ngày hiện tại
"""

import random
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from .flight_data import (
    VIETNAM_AIRPORTS, VIETNAM_AIRLINES, FLIGHT_ROUTES,
    AIRCRAFT_TYPES, DEPARTURE_HOURS
)
from .train_data import (
    TRAIN_STATIONS, TRAIN_TYPES, TRAIN_ROUTES,
    SEAT_TYPES, TRAIN_DEPARTURE_HOURS
)
from .bus_data import (
    BUS_COMPANIES, BUS_STATIONS, BUS_TYPES, BUS_SEAT_TYPES,
    BUS_ROUTES, BUS_DEPARTURE_HOURS
)


class MockDataGenerator:
    """
    Generator tạo mock data động theo ngày.
    Sử dụng seed dựa trên ngày để đảm bảo data consistent trong cùng 1 ngày.
    """

    def __init__(self):
        self.vietnam_tz = timezone(timedelta(hours=7))

    def _get_seed(self, date_str: str, route: str) -> int:
        """Tạo seed từ ngày và tuyến đường để data consistent"""
        seed_string = f"{date_str}_{route}"
        return int(hashlib.md5(seed_string.encode()).hexdigest()[:8], 16)

    def _get_random(self, seed: int) -> random.Random:
        """Tạo random generator với seed cố định"""
        rng = random.Random()
        rng.seed(seed)
        return rng

    def _is_weekend(self, date: datetime) -> bool:
        """Kiểm tra có phải cuối tuần không"""
        return date.weekday() >= 5

    def _is_holiday(self, date: datetime) -> bool:
        """Kiểm tra có phải ngày lễ không (simplified)"""
        holidays = [
            (1, 1),   # Tết Dương lịch
            (4, 30),  # Giải phóng miền Nam
            (5, 1),   # Quốc tế Lao động
            (9, 2),   # Quốc khánh
        ]
        return (date.month, date.day) in holidays

    def _get_price_multiplier(self, date: datetime, rng: random.Random) -> float:
        """Tính hệ số giá dựa trên ngày"""
        multiplier = 1.0

        if self._is_weekend(date):
            multiplier *= 1.2  # Cuối tuần đắt hơn 20%

        if self._is_holiday(date):
            multiplier *= 1.5  # Ngày lễ đắt hơn 50%

        # Biến động ngẫu nhiên ±15%
        multiplier *= rng.uniform(0.85, 1.15)

        return multiplier

    # ==================== FLIGHT GENERATOR ====================

    def generate_flights(
        self,
        departure_iata: str,
        arrival_iata: str,
        date: Optional[str] = None,
        days_ahead: int = 1,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Tạo danh sách chuyến bay cho tuyến và ngày cụ thể.

        Args:
            departure_iata: Mã sân bay đi
            arrival_iata: Mã sân bay đến
            date: Ngày bắt đầu (YYYY-MM-DD), mặc định là hôm nay
            days_ahead: Số ngày tạo data (1 = chỉ ngày đó)
            limit: Số chuyến bay tối đa mỗi ngày

        Returns:
            List các chuyến bay
        """
        departure_iata = departure_iata.upper()
        arrival_iata = arrival_iata.upper()

        # Validate airports
        if departure_iata not in VIETNAM_AIRPORTS:
            return []
        if arrival_iata not in VIETNAM_AIRPORTS:
            return []
        if departure_iata == arrival_iata:
            return []

        # Parse date
        if not date:
            base_date = datetime.now(self.vietnam_tz)
        else:
            try:
                base_date = datetime.strptime(date, "%Y-%m-%d")
                base_date = base_date.replace(tzinfo=self.vietnam_tz)
            except ValueError:
                base_date = datetime.now(self.vietnam_tz)

        # Get route info
        route_key = (departure_iata, arrival_iata)
        if route_key not in FLIGHT_ROUTES:
            # Tạo route mặc định nếu không có
            route_info = {
                "base_price": 800000,
                "duration": 90,
                "flights_per_day": 5
            }
        else:
            route_info = FLIGHT_ROUTES[route_key]

        dep_airport = VIETNAM_AIRPORTS[departure_iata]
        arr_airport = VIETNAM_AIRPORTS[arrival_iata]

        all_flights = []

        for day_offset in range(days_ahead):
            current_date = base_date + timedelta(days=day_offset)
            date_str = current_date.strftime("%Y-%m-%d")

            # Seed cho ngày và tuyến này
            seed = self._get_seed(date_str, f"{departure_iata}_{arrival_iata}")
            rng = self._get_random(seed)

            # Số chuyến bay trong ngày
            num_flights = min(route_info["flights_per_day"], limit)

            # Chọn giờ khởi hành
            available_hours = DEPARTURE_HOURS.copy()
            rng.shuffle(available_hours)
            selected_hours = sorted(available_hours[:num_flights])

            for i, hour in enumerate(selected_hours):
                # Chọn hãng bay
                airline = rng.choice(VIETNAM_AIRLINES)

                # Tạo số hiệu chuyến bay
                flight_number = f"{airline['code']}{rng.randint(100, 999)}"

                # Tính giá
                price_multiplier = self._get_price_multiplier(current_date, rng)
                base_price = route_info["base_price"]
                economy_price = int(base_price * price_multiplier)
                economy_price = round(economy_price, -3)  # Làm tròn nghìn

                # Thời gian
                minute = rng.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55])
                dep_time = current_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                duration = route_info["duration"]
                arr_time = dep_time + timedelta(minutes=duration)

                # Máy bay
                aircraft = rng.choice(AIRCRAFT_TYPES)

                # Ghế còn lại
                available_seats = rng.randint(5, aircraft["capacity"] // 2)

                flight = {
                    "flight_id": f"FL{seed % 1000000:06d}{i:02d}",
                    "flight_number": flight_number,
                    "airline": {
                        "code": airline["code"],
                        "name": airline["name"],
                        "logo": airline["logo"]
                    },
                    "departure": {
                        "airport": dep_airport["name"],
                        "city": dep_airport["city"],
                        "iata": departure_iata,
                        "terminal": rng.choice(dep_airport["terminals"]),
                        "scheduled": dep_time.isoformat(),
                        "date": date_str,
                        "time": dep_time.strftime("%H:%M")
                    },
                    "arrival": {
                        "airport": arr_airport["name"],
                        "city": arr_airport["city"],
                        "iata": arrival_iata,
                        "terminal": rng.choice(arr_airport["terminals"]),
                        "scheduled": arr_time.isoformat(),
                        "date": arr_time.strftime("%Y-%m-%d"),
                        "time": arr_time.strftime("%H:%M")
                    },
                    "duration_minutes": duration,
                    "duration_formatted": f"{duration // 60}h {duration % 60}m",
                    "price": {
                        "economy": economy_price,
                        "business": int(economy_price * 2.5),
                        "first_class": int(economy_price * 4),
                        "currency": "VND"
                    },
                    "available_seats": available_seats,
                    "aircraft": aircraft["model"],
                    "status": "scheduled",
                    "baggage": {
                        "carry_on": airline["baggage_carry"],
                        "checked": airline["baggage_checked"]
                    }
                }
                all_flights.append(flight)

        return all_flights

    def generate_flights_multi_day(
        self,
        departure_iata: str,
        arrival_iata: str,
        start_date: Optional[str] = None,
        days: int = 7,
        limit_per_day: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Tạo chuyến bay cho nhiều ngày, grouped by date.

        Returns:
            Dict với key là ngày, value là list chuyến bay
        """
        if not start_date:
            start_date = datetime.now(self.vietnam_tz).strftime("%Y-%m-%d")

        result = {}
        base_date = datetime.strptime(start_date, "%Y-%m-%d")

        for day_offset in range(days):
            current_date = base_date + timedelta(days=day_offset)
            date_str = current_date.strftime("%Y-%m-%d")

            flights = self.generate_flights(
                departure_iata=departure_iata,
                arrival_iata=arrival_iata,
                date=date_str,
                days_ahead=1,
                limit=limit_per_day
            )
            result[date_str] = flights

        return result

    # ==================== TRAIN GENERATOR ====================

    def generate_trains(
        self,
        departure_station: str,
        arrival_station: str,
        date: Optional[str] = None,
        days_ahead: int = 1,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Tạo danh sách chuyến tàu cho tuyến và ngày cụ thể.

        Args:
            departure_station: Mã ga đi (HNO, SGO, DNA, ...)
            arrival_station: Mã ga đến
            date: Ngày (YYYY-MM-DD), mặc định là hôm nay
            days_ahead: Số ngày tạo data
            limit: Số chuyến tàu tối đa mỗi ngày

        Returns:
            List các chuyến tàu
        """
        departure_station = departure_station.upper()
        arrival_station = arrival_station.upper()

        # Validate stations
        if departure_station not in TRAIN_STATIONS:
            return []
        if arrival_station not in TRAIN_STATIONS:
            return []
        if departure_station == arrival_station:
            return []

        # Parse date
        if not date:
            base_date = datetime.now(self.vietnam_tz)
        else:
            try:
                base_date = datetime.strptime(date, "%Y-%m-%d")
                base_date = base_date.replace(tzinfo=self.vietnam_tz)
            except ValueError:
                base_date = datetime.now(self.vietnam_tz)

        # Get route info
        route_key = (departure_station, arrival_station)
        if route_key not in TRAIN_ROUTES:
            # Tạo route mặc định
            route_info = {
                "base_price": 300000,
                "duration_hours": 10,
                "trains_per_day": 3,
                "train_types": ["TN"]
            }
        else:
            route_info = TRAIN_ROUTES[route_key]

        dep_station = TRAIN_STATIONS[departure_station]
        arr_station = TRAIN_STATIONS[arrival_station]

        all_trains = []

        for day_offset in range(days_ahead):
            current_date = base_date + timedelta(days=day_offset)
            date_str = current_date.strftime("%Y-%m-%d")

            # Seed cho ngày và tuyến này
            seed = self._get_seed(date_str, f"TRAIN_{departure_station}_{arrival_station}")
            rng = self._get_random(seed)

            # Số chuyến tàu trong ngày
            num_trains = min(route_info["trains_per_day"], limit)

            for i in range(num_trains):
                # Chọn loại tàu
                train_type_code = rng.choice(route_info["train_types"])
                train_type = TRAIN_TYPES[train_type_code]

                # Tạo số hiệu tàu
                train_number = f"{train_type_code}{rng.randint(1, 20)}"

                # Giờ khởi hành
                available_hours = TRAIN_DEPARTURE_HOURS.get(train_type_code, [6, 12, 18])
                if i < len(available_hours):
                    hour = available_hours[i]
                else:
                    hour = rng.choice(available_hours)

                minute = rng.choice([0, 15, 30, 45])
                dep_time = current_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

                # Thời gian đến
                duration_hours = route_info["duration_hours"]
                arr_time = dep_time + timedelta(hours=duration_hours)

                # Tính giá cho các loại ghế
                base_price = route_info["base_price"]
                price_multiplier = self._get_price_multiplier(current_date, rng)

                seat_prices = {}
                seat_availability = {}
                for seat_code, seat_info in SEAT_TYPES.items():
                    price = int(base_price * seat_info["price_multiplier"] * price_multiplier)
                    price = round(price, -3)
                    seat_prices[seat_code] = {
                        "name": seat_info["name"],
                        "code": seat_info["code"],
                        "price": price,
                        "description": seat_info["description"]
                    }
                    seat_availability[seat_code] = rng.randint(0, 30)

                train = {
                    "train_id": f"TR{seed % 1000000:06d}{i:02d}",
                    "train_number": train_number,
                    "train_type": {
                        "code": train_type_code,
                        "name": train_type["name"],
                        "description": train_type["description"],
                        "amenities": train_type["amenities"]
                    },
                    "departure": {
                        "station": dep_station["name"],
                        "city": dep_station["city"],
                        "code": departure_station,
                        "address": dep_station["address"],
                        "scheduled": dep_time.isoformat(),
                        "date": date_str,
                        "time": dep_time.strftime("%H:%M")
                    },
                    "arrival": {
                        "station": arr_station["name"],
                        "city": arr_station["city"],
                        "code": arrival_station,
                        "address": arr_station["address"],
                        "scheduled": arr_time.isoformat(),
                        "date": arr_time.strftime("%Y-%m-%d"),
                        "time": arr_time.strftime("%H:%M")
                    },
                    "duration_hours": duration_hours,
                    "duration_formatted": f"{int(duration_hours)}h {int((duration_hours % 1) * 60)}m",
                    "seats": seat_prices,
                    "availability": seat_availability,
                    "status": "scheduled",
                    "currency": "VND"
                }
                all_trains.append(train)

        # Sắp xếp theo giờ khởi hành
        all_trains.sort(key=lambda x: x["departure"]["scheduled"])
        return all_trains

    def generate_trains_multi_day(
        self,
        departure_station: str,
        arrival_station: str,
        start_date: Optional[str] = None,
        days: int = 7,
        limit_per_day: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Tạo chuyến tàu cho nhiều ngày, grouped by date.
        """
        if not start_date:
            start_date = datetime.now(self.vietnam_tz).strftime("%Y-%m-%d")

        result = {}
        base_date = datetime.strptime(start_date, "%Y-%m-%d")

        for day_offset in range(days):
            current_date = base_date + timedelta(days=day_offset)
            date_str = current_date.strftime("%Y-%m-%d")

            trains = self.generate_trains(
                departure_station=departure_station,
                arrival_station=arrival_station,
                date=date_str,
                days_ahead=1,
                limit=limit_per_day
            )
            result[date_str] = trains

        return result

    # ==================== BUS GENERATOR ====================

    def generate_buses(
        self,
        departure_station: str,
        arrival_station: str,
        date: Optional[str] = None,
        days_ahead: int = 1,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Tạo danh sách chuyến xe khách cho tuyến và ngày cụ thể.
        """
        departure_station = departure_station.upper()
        arrival_station = arrival_station.upper()

        if departure_station not in BUS_STATIONS:
            return []
        if arrival_station not in BUS_STATIONS:
            return []
        if departure_station == arrival_station:
            return []

        if not date:
            base_date = datetime.now(self.vietnam_tz)
        else:
            try:
                base_date = datetime.strptime(date, "%Y-%m-%d")
                base_date = base_date.replace(tzinfo=self.vietnam_tz)
            except ValueError:
                base_date = datetime.now(self.vietnam_tz)

        route_key = (departure_station, arrival_station)
        if route_key not in BUS_ROUTES:
            route_info = {
                "base_price": 250000,
                "duration_hours": 8,
                "buses_per_day": 5,
                "bus_types": ["limousine_11", "sleeper_40"]
            }
        else:
            route_info = BUS_ROUTES[route_key]

        dep_station = BUS_STATIONS[departure_station]
        arr_station = BUS_STATIONS[arrival_station]

        all_buses = []

        for day_offset in range(days_ahead):
            current_date = base_date + timedelta(days=day_offset)
            date_str = current_date.strftime("%Y-%m-%d")

            seed = self._get_seed(date_str, f"BUS_{departure_station}_{arrival_station}")
            rng = self._get_random(seed)

            num_buses = min(route_info["buses_per_day"], limit)

            # Select departure hours
            bus_type_code = rng.choice(route_info["bus_types"])
            available_hours = BUS_DEPARTURE_HOURS.get(bus_type_code, [6, 12, 18])
            rng.shuffle(available_hours)
            selected_hours = sorted(available_hours[:num_buses])

            for i, hour in enumerate(selected_hours):
                # Rotate bus types
                bus_type_code = rng.choice(route_info["bus_types"])
                bus_type = BUS_TYPES[bus_type_code]

                # Choose company
                company = rng.choice(BUS_COMPANIES)

                # Bus number
                bus_number = f"{company['code']}{rng.randint(100, 999)}"

                # Price
                price_multiplier = self._get_price_multiplier(current_date, rng)
                base_price = route_info["base_price"]
                seat_prices = {}
                seat_availability = {}
                for seat_code, seat_info in BUS_SEAT_TYPES.items():
                    price = int(base_price * seat_info["price_multiplier"] * price_multiplier)
                    price = round(price, -3)
                    seat_prices[seat_code] = {
                        "name": seat_info["name"],
                        "code": seat_info["code"],
                        "price": price,
                        "description": seat_info["description"]
                    }
                    seat_availability[seat_code] = rng.randint(0, bus_type["capacity"] // 2)

                # Times
                minute = rng.choice([0, 15, 30, 45])
                dep_time = current_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                duration_hours = route_info["duration_hours"]
                arr_time = dep_time + timedelta(hours=duration_hours)

                total_seats = bus_type["capacity"]
                available_seats = rng.randint(2, total_seats // 2)

                bus = {
                    "bus_id": f"BS{seed % 1000000:06d}{i:02d}",
                    "bus_number": bus_number,
                    "company": {
                        "code": company["code"],
                        "name": company["name"],
                        "logo": company["logo"],
                        "phone": company["phone"],
                        "rating": company["rating"]
                    },
                    "bus_type": {
                        "code": bus_type_code,
                        "name": bus_type["name"],
                        "description": bus_type["description"],
                        "capacity": bus_type["capacity"],
                        "amenities": bus_type["amenities"]
                    },
                    "departure": {
                        "station": dep_station["name"],
                        "city": dep_station["city"],
                        "code": departure_station,
                        "address": dep_station["address"],
                        "scheduled": dep_time.isoformat(),
                        "date": date_str,
                        "time": dep_time.strftime("%H:%M")
                    },
                    "arrival": {
                        "station": arr_station["name"],
                        "city": arr_station["city"],
                        "code": arrival_station,
                        "address": arr_station["address"],
                        "scheduled": arr_time.isoformat(),
                        "date": arr_time.strftime("%Y-%m-%d"),
                        "time": arr_time.strftime("%H:%M")
                    },
                    "duration_hours": duration_hours,
                    "duration_formatted": f"{int(duration_hours)}h {int((duration_hours % 1) * 60)}m",
                    "seats": seat_prices,
                    "availability": seat_availability,
                    "total_seats": total_seats,
                    "available_seats": available_seats,
                    "status": "scheduled",
                    "currency": "VND"
                }
                all_buses.append(bus)

        all_buses.sort(key=lambda x: x["departure"]["scheduled"])
        return all_buses

    # ==================== BOOKING GENERATORS ====================

    def generate_flight_booking(
        self,
        flight_id: str,
        passenger_name: str,
        passenger_phone: str,
        passenger_email: str,
        seat_class: str = "economy",
        num_passengers: int = 1
    ) -> Dict[str, Any]:
        """Tạo booking cho chuyến bay"""
        seed = self._get_seed(datetime.now().isoformat(), flight_id)
        rng = self._get_random(seed)

        booking_id = f"FBK{rng.randint(100000, 999999)}"

        # Mock price based on seat class
        base_price = rng.randint(500000, 2000000)
        if seat_class == "business":
            base_price = int(base_price * 2.5)
        elif seat_class == "first_class":
            base_price = int(base_price * 4)

        total_price = base_price * num_passengers

        return {
            "success": True,
            "booking_id": booking_id,
            "booking_type": "flight",
            "flight_id": flight_id,
            "passenger": {
                "name": passenger_name,
                "phone": passenger_phone,
                "email": passenger_email
            },
            "seat_class": seat_class,
            "num_passengers": num_passengers,
            "total_price": total_price,
            "currency": "VND",
            "status": "pending_payment",
            "expires_at": (datetime.now(self.vietnam_tz) + timedelta(minutes=30)).isoformat(),
            "created_at": datetime.now(self.vietnam_tz).isoformat()
        }

    def generate_train_booking(
        self,
        train_id: str,
        passenger_name: str,
        passenger_phone: str,
        passenger_email: str,
        seat_type: str = "soft_seat",
        num_passengers: int = 1
    ) -> Dict[str, Any]:
        """Tạo booking cho chuyến tàu"""
        seed = self._get_seed(datetime.now().isoformat(), train_id)
        rng = self._get_random(seed)

        booking_id = f"TBK{rng.randint(100000, 999999)}"

        # Get seat price multiplier
        seat_info = SEAT_TYPES.get(seat_type, SEAT_TYPES["soft_seat"])
        base_price = rng.randint(200000, 800000)
        price = int(base_price * seat_info["price_multiplier"])
        total_price = price * num_passengers

        return {
            "success": True,
            "booking_id": booking_id,
            "booking_type": "train",
            "train_id": train_id,
            "passenger": {
                "name": passenger_name,
                "phone": passenger_phone,
                "email": passenger_email
            },
            "seat_type": {
                "code": seat_type,
                "name": seat_info["name"]
            },
            "num_passengers": num_passengers,
            "total_price": total_price,
            "currency": "VND",
            "status": "pending_payment",
            "expires_at": (datetime.now(self.vietnam_tz) + timedelta(minutes=30)).isoformat(),
            "created_at": datetime.now(self.vietnam_tz).isoformat()
        }

    def generate_bus_booking(
        self,
        bus_id: str,
        passenger_name: str,
        passenger_phone: str,
        passenger_email: str,
        seat_type: str = "standard",
        num_passengers: int = 1
    ) -> Dict[str, Any]:
        """Tạo booking cho chuyến xe khách"""
        seed = self._get_seed(datetime.now().isoformat(), bus_id)
        rng = self._get_random(seed)

        booking_id = f"BBK{rng.randint(100000, 999999)}"

        seat_info = BUS_SEAT_TYPES.get(seat_type, BUS_SEAT_TYPES["standard"])
        base_price = rng.randint(150000, 600000)
        price = int(base_price * seat_info["price_multiplier"])
        total_price = price * num_passengers

        return {
            "success": True,
            "booking_id": booking_id,
            "booking_type": "bus",
            "bus_id": bus_id,
            "passenger": {
                "name": passenger_name,
                "phone": passenger_phone,
                "email": passenger_email
            },
            "seat_type": {
                "code": seat_type,
                "name": seat_info["name"]
            },
            "num_passengers": num_passengers,
            "total_price": total_price,
            "currency": "VND",
            "status": "pending_payment",
            "expires_at": (datetime.now(self.vietnam_tz) + timedelta(minutes=30)).isoformat(),
            "created_at": datetime.now(self.vietnam_tz).isoformat()
        }


# Singleton instance
_generator_instance = None


def get_generator() -> MockDataGenerator:
    """Get singleton instance of MockDataGenerator"""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = MockDataGenerator()
    return _generator_instance
