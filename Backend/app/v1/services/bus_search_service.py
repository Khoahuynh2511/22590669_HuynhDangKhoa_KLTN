"""
Bus Search Service - Public search cho xe khach
Su dung psycopg2 truc tiep, query DB that thay vi mock data
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
from app.v1.core.config import settings

VIETNAM_TZ = timezone(timedelta(hours=7))


class BusSearchService:
    def __init__(self):
        self.db_url = settings.DATABASE_URL

    def _get_conn(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    def get_stations(self) -> Dict[str, Any]:
        """Lay danh sach ben xe active"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT station_id as code, name, city, region, address
                        FROM bus_stations WHERE is_active = TRUE
                        ORDER BY city, name
                    """)
                    rows = cur.fetchall()
                    stations = []
                    for r in rows:
                        stations.append({
                            "code": r["code"],
                            "name": r["name"],
                            "city": r["city"],
                            "region": r["region"],
                            "address": r["address"] or ""
                        })
            return {"EC": 0, "EM": "Success", "data": stations}
        except Exception as e:
            return {"EC": 2, "EM": f"Loi server: {str(e)}", "data": []}

    def get_types(self) -> Dict[str, Any]:
        """Lay danh sach loai xe + loai ghe"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Bus types
                    cur.execute("""
                        SELECT type_id as code, name, description, capacity, amenities
                        FROM bus_types WHERE is_active = TRUE
                        ORDER BY name
                    """)
                    bus_types = {}
                    for r in cur.fetchall():
                        bus_types[r["code"]] = {
                            "code": r["code"],
                            "name": r["name"],
                            "description": r["description"] or "",
                            "capacity": r["capacity"] or 0,
                            "amenities": r["amenities"] or []
                        }

                    # Bus seat types
                    cur.execute("""
                        SELECT seat_type_id as code, name, code as seat_code,
                               description, price_multiplier
                        FROM bus_seat_types WHERE is_active = TRUE
                        ORDER BY price_multiplier
                    """)
                    seat_types = {}
                    for r in cur.fetchall():
                        seat_types[r["code"]] = {
                            "name": r["name"],
                            "code": r["seat_code"],
                            "description": r["description"] or "",
                            "price_multiplier": float(r["price_multiplier"]) if r["price_multiplier"] else 1.0
                        }

            return {"EC": 0, "EM": "Success", "data": {"bus_types": bus_types, "seat_types": seat_types}}
        except Exception as e:
            return {"EC": 2, "EM": f"Loi server: {str(e)}", "data": {"bus_types": {}, "seat_types": {}}}

    def search_buses(
        self,
        departure: str,
        arrival: str,
        date: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Tim kiem xe khach tu DB that"""
        departure = departure.upper()
        arrival = arrival.upper()

        # Validate stations exist
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT station_id FROM bus_stations WHERE station_id = %s AND is_active = TRUE", (departure,))
                    if not cur.fetchone():
                        return {"EC": 1, "EM": f"Khong tim thay ben xe {departure}", "data": None}
                    cur.execute("SELECT station_id FROM bus_stations WHERE station_id = %s AND is_active = TRUE", (arrival,))
                    if not cur.fetchone():
                        return {"EC": 1, "EM": f"Khong tim thay ben xe {arrival}", "data": None}
        except Exception as e:
            return {"EC": 2, "EM": f"Loi server: {str(e)}", "data": None}

        if departure == arrival:
            return {"EC": 1, "EM": "Ben di va ben den khong duoc trung nhau", "data": None}

        if not date:
            date = datetime.now(VIETNAM_TZ).strftime("%Y-%m-%d")

        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Get bus seat types for price computation
                    cur.execute("""
                        SELECT seat_type_id, name, code, description, price_multiplier
                        FROM bus_seat_types WHERE is_active = TRUE
                        ORDER BY price_multiplier
                    """)
                    bus_seat_types = cur.fetchall()

                    # Query buses with joins
                    cur.execute("""
                        SELECT b.*,
                            dep_s.name as dep_station_name,
                            dep_s.city as dep_city,
                            dep_s.address as dep_address,
                            arr_s.name as arr_station_name,
                            arr_s.city as arr_city,
                            arr_s.address as arr_address,
                            bc.name as company_name,
                            bc.logo_url as company_logo,
                            bc.phone as company_phone,
                            bc.rating as company_rating,
                            bc.amenities as company_amenities,
                            bt.name as type_name,
                            bt.description as type_desc,
                            bt.capacity as type_capacity,
                            bt.amenities as type_amenities
                        FROM buses b
                        JOIN bus_stations dep_s ON b.departure_station = dep_s.station_id
                        JOIN bus_stations arr_s ON b.arrival_station = arr_s.station_id
                        JOIN bus_companies bc ON b.company_id = bc.company_id
                        JOIN bus_types bt ON b.bus_type_id = bt.type_id
                        WHERE b.departure_station = %s
                          AND b.arrival_station = %s
                          AND b.is_active = TRUE
                          AND b.status != 'cancelled'
                          AND DATE(b.departure_time) = %s
                        ORDER BY b.departure_time
                        LIMIT %s
                    """, (departure, arrival, date, limit))

                    bus_rows = cur.fetchall()

                    buses = []
                    for r in bus_rows:
                        # Compute seat prices from base_price × multiplier
                        base_price = r["base_price"] or 0
                        seat_prices = {}
                        seat_availability = {}
                        for st in bus_seat_types:
                            price = int(base_price * float(st["price_multiplier"] or 1))
                            price = round(price, -3)  # round to thousand
                            seat_prices[st["seat_type_id"]] = {
                                "name": st["name"],
                                "code": st["code"],
                                "price": price,
                                "description": st["description"] or ""
                            }
                            # Distribute available seats across seat types proportionally
                            seat_availability[st["seat_type_id"]] = r["available_seats"] or 0

                        dep_time = r["departure_time"]
                        arr_time = r["arrival_time"]
                        if dep_time.tzinfo is None:
                            dep_time = dep_time.replace(tzinfo=VIETNAM_TZ)
                        if arr_time.tzinfo is None:
                            arr_time = arr_time.replace(tzinfo=VIETNAM_TZ)

                        duration = r["duration_hours"] or 0
                        bus = {
                            "bus_id": r["bus_id"],
                            "bus_number": r["bus_number"],
                            "company": {
                                "code": r["company_id"],
                                "name": r["company_name"],
                                "logo": r["company_logo"] or "",
                                "phone": r["company_phone"] or "",
                                "rating": float(r["company_rating"]) if r["company_rating"] else 4.0
                            },
                            "bus_type": {
                                "code": r["bus_type_id"],
                                "name": r["type_name"],
                                "description": r["type_desc"] or "",
                                "capacity": r["type_capacity"] or 0,
                                "amenities": r["type_amenities"] or []
                            },
                            "departure": {
                                "station": r["dep_station_name"],
                                "city": r["dep_city"],
                                "code": departure,
                                "address": r["dep_address"] or "",
                                "scheduled": dep_time.isoformat(),
                                "date": dep_time.strftime("%Y-%m-%d"),
                                "time": dep_time.strftime("%H:%M")
                            },
                            "arrival": {
                                "station": r["arr_station_name"],
                                "city": r["arr_city"],
                                "code": arrival,
                                "address": r["arr_address"] or "",
                                "scheduled": arr_time.isoformat(),
                                "date": arr_time.strftime("%Y-%m-%d"),
                                "time": arr_time.strftime("%H:%M")
                            },
                            "duration_hours": duration,
                            "duration_formatted": f"{int(duration)}h {int((duration % 1) * 60)}m",
                            "seats": seat_prices,
                            "availability": seat_availability,
                            "total_seats": r["total_seats"] or 0,
                            "available_seats": r["available_seats"] or 0,
                            "status": r["status"] or "scheduled",
                            "currency": "VND"
                        }
                        buses.append(bus)

                    # Get station info for wrapper
                    cur.execute("SELECT name, city FROM bus_stations WHERE station_id = %s", (departure,))
                    dep_info = cur.fetchone()
                    cur.execute("SELECT name, city FROM bus_stations WHERE station_id = %s", (arrival,))
                    arr_info = cur.fetchone()

                    # Get seat types for response
                    seat_types_resp = {}
                    for st in bus_seat_types:
                        seat_types_resp[st["seat_type_id"]] = {
                            "name": st["name"],
                            "code": st["code"],
                            "description": st["description"] or "",
                            "price_multiplier": float(st["price_multiplier"]) if st["price_multiplier"] else 1.0
                        }

            return {
                "EC": 0,
                "EM": "Success",
                "data": {
                    "departure": {
                        "code": departure,
                        "city": dep_info["city"] if dep_info else "",
                        "station": dep_info["name"] if dep_info else ""
                    },
                    "arrival": {
                        "code": arrival,
                        "city": arr_info["city"] if arr_info else "",
                        "station": arr_info["name"] if arr_info else ""
                    },
                    "date": date,
                    "total": len(buses),
                    "buses": buses,
                    "seat_types": seat_types_resp
                }
            }
        except Exception as e:
            return {"EC": 2, "EM": f"Loi server: {str(e)}", "data": None}


def get_bus_search_service() -> BusSearchService:
    """Dependency injection for BusSearchService"""
    return BusSearchService()
