"""
Train Search Service - Public search cho tau hoa
Su dung psycopg2 truc tiep, query DB that thay vi mock data
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
from app.v1.core.config import settings

VIETNAM_TZ = timezone(timedelta(hours=7))


class TrainSearchService:
    def __init__(self):
        self.db_url = settings.DATABASE_URL

    def _get_conn(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    def get_stations(self) -> Dict[str, Any]:
        """Lay danh sach ga tau active"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT station_id as code, name, city, region, address
                        FROM train_stations WHERE is_active = TRUE
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
        """Lay danh sach loai tau + loai ghe"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Train types
                    cur.execute("""
                        SELECT type_id as code, name, description, speed, amenities
                        FROM train_types WHERE is_active = TRUE
                        ORDER BY name
                    """)
                    train_types = {}
                    for r in cur.fetchall():
                        train_types[r["code"]] = {
                            "code": r["code"],
                            "name": r["name"],
                            "description": r["description"] or "",
                            "speed": r["speed"] or "",
                            "amenities": r["amenities"] or []
                        }

                    # Seat types
                    cur.execute("""
                        SELECT seat_type_id as code, name, code as seat_code,
                               description, price_multiplier
                        FROM seat_types WHERE is_active = TRUE
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

            return {"EC": 0, "EM": "Success", "data": {"train_types": train_types, "seat_types": seat_types}}
        except Exception as e:
            return {"EC": 2, "EM": f"Loi server: {str(e)}", "data": {"train_types": {}, "seat_types": {}}}

    def search_trains(
        self,
        departure: str,
        arrival: str,
        date: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Tim kiem tau hoa tu DB that"""
        departure = departure.upper()
        arrival = arrival.upper()

        # Validate stations exist
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT station_id FROM train_stations WHERE station_id = %s AND is_active = TRUE", (departure,))
                    if not cur.fetchone():
                        return {"EC": 1, "EM": f"Khong tim thay ga tau {departure}", "data": None}
                    cur.execute("SELECT station_id FROM train_stations WHERE station_id = %s AND is_active = TRUE", (arrival,))
                    if not cur.fetchone():
                        return {"EC": 1, "EM": f"Khong tim thay ga tau {arrival}", "data": None}
        except Exception as e:
            return {"EC": 2, "EM": f"Loi server: {str(e)}", "data": None}

        if departure == arrival:
            return {"EC": 1, "EM": "Ga di va den khong duoc trung nhau", "data": None}

        if not date:
            date = datetime.now(VIETNAM_TZ).strftime("%Y-%m-%d")

        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Query trains with joins
                    cur.execute("""
                        SELECT t.*,
                            dep_s.name as dep_station_name,
                            dep_s.city as dep_city,
                            dep_s.address as dep_address,
                            arr_s.name as arr_station_name,
                            arr_s.city as arr_city,
                            arr_s.address as arr_address,
                            tt.name as type_name,
                            tt.description as type_desc,
                            tt.amenities as type_amenities
                        FROM trains t
                        JOIN train_stations dep_s ON t.departure_station = dep_s.station_id
                        JOIN train_stations arr_s ON t.arrival_station = arr_s.station_id
                        JOIN train_types tt ON t.train_type_id = tt.type_id
                        WHERE t.departure_station = %s
                          AND t.arrival_station = %s
                          AND t.is_active = TRUE
                          AND t.status != 'cancelled'
                          AND DATE(t.departure_time) = %s
                        ORDER BY t.departure_time
                        LIMIT %s
                    """, (departure, arrival, date, limit))

                    train_rows = cur.fetchall()

                    # For each train, get seat prices
                    trains = []
                    for r in train_rows:
                        train_id = r["train_id"]

                        cur.execute("""
                            SELECT tsp.*, st.name as seat_name, st.code as seat_code,
                                   st.description as seat_desc
                            FROM train_seat_prices tsp
                            JOIN seat_types st ON tsp.seat_type_id = st.seat_type_id
                            WHERE tsp.train_id = %s
                            ORDER BY st.price_multiplier
                        """, (train_id,))
                        seat_rows = cur.fetchall()

                        seat_prices = {}
                        seat_availability = {}
                        for sr in seat_rows:
                            seat_prices[sr["seat_type_id"]] = {
                                "name": sr["seat_name"],
                                "code": sr["seat_code"],
                                "price": sr["price"] or 0,
                                "description": sr["seat_desc"] or ""
                            }
                            seat_availability[sr["seat_type_id"]] = sr["available_seats"] or 0

                        dep_time = r["departure_time"]
                        arr_time = r["arrival_time"]
                        if dep_time.tzinfo is None:
                            dep_time = dep_time.replace(tzinfo=VIETNAM_TZ)
                        if arr_time.tzinfo is None:
                            arr_time = arr_time.replace(tzinfo=VIETNAM_TZ)

                        duration = r["duration_hours"] or 0
                        train = {
                            "train_id": train_id,
                            "train_number": r["train_number"],
                            "train_type": {
                                "code": r["train_type_id"],
                                "name": r["type_name"],
                                "description": r["type_desc"] or "",
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
                            "status": r["status"] or "scheduled",
                            "currency": "VND"
                        }
                        trains.append(train)

                    # Get station info for wrapper
                    cur.execute("SELECT name, city FROM train_stations WHERE station_id = %s", (departure,))
                    dep_info = cur.fetchone()
                    cur.execute("SELECT name, city FROM train_stations WHERE station_id = %s", (arrival,))
                    arr_info = cur.fetchone()

                    # Get seat types for response
                    cur.execute("""
                        SELECT seat_type_id as code, name, code as seat_code,
                               description, price_multiplier
                        FROM seat_types WHERE is_active = TRUE ORDER BY price_multiplier
                    """)
                    seat_types = {}
                    for sr in cur.fetchall():
                        seat_types[sr["code"]] = {
                            "name": sr["name"],
                            "code": sr["seat_code"],
                            "description": sr["description"] or "",
                            "price_multiplier": float(sr["price_multiplier"]) if sr["price_multiplier"] else 1.0
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
                    "total": len(trains),
                    "trains": trains,
                    "seat_types": seat_types
                }
            }
        except Exception as e:
            return {"EC": 2, "EM": f"Loi server: {str(e)}", "data": None}


def get_train_search_service() -> TrainSearchService:
    """Dependency injection for TrainSearchService"""
    return TrainSearchService()
