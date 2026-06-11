"""
Flight Search Service - Public search cho chuyen bay
Su dung psycopg2 truc tiep, query DB that thay vi mock data
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
from app.v1.core.config import settings

VIETNAM_TZ = timezone(timedelta(hours=7))


class FlightSearchService:
    def __init__(self):
        self.db_url = settings.DATABASE_URL

    def _get_conn(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    def get_airports(self) -> Dict[str, Any]:
        """Lay danh sach san bay active"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT airport_id as code, name, city, region, terminals
                        FROM airports WHERE is_active = TRUE
                        ORDER BY city, name
                    """)
                    rows = cur.fetchall()
                    airports = []
                    for r in rows:
                        airports.append({
                            "code": r["code"],
                            "name": r["name"],
                            "city": r["city"],
                            "region": r["region"],
                            "terminals": r["terminals"] if r["terminals"] else []
                        })
            return {"EC": 0, "EM": "Success", "data": airports}
        except Exception as e:
            return {"EC": 2, "EM": f"Loi server: {str(e)}", "data": []}

    def get_airlines(self) -> Dict[str, Any]:
        """Lay danh sach hang bay active"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT airline_id as code, name, logo_url as logo,
                               baggage_carry, baggage_checked
                        FROM airlines WHERE is_active = TRUE
                        ORDER BY name
                    """)
                    rows = cur.fetchall()
                    airlines = []
                    for r in rows:
                        airlines.append({
                            "code": r["code"],
                            "name": r["name"],
                            "logo": r["logo"] or "",
                            "baggage_carry": r["baggage_carry"] or "7kg",
                            "baggage_checked": r["baggage_checked"] or "20kg"
                        })
            return {"EC": 0, "EM": "Success", "data": airlines}
        except Exception as e:
            return {"EC": 2, "EM": f"Loi server: {str(e)}", "data": []}

    def search_flights(
        self,
        departure: str,
        arrival: str,
        date: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Tim kiem chuyen bay tu DB that"""
        departure = departure.upper()
        arrival = arrival.upper()

        # Validate airports exist
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT airport_id FROM airports WHERE airport_id = %s AND is_active = TRUE", (departure,))
                    if not cur.fetchone():
                        return {"EC": 1, "EM": f"Khong tim thay san bay {departure}", "data": None}
                    cur.execute("SELECT airport_id FROM airports WHERE airport_id = %s AND is_active = TRUE", (arrival,))
                    if not cur.fetchone():
                        return {"EC": 1, "EM": f"Khong tim thay san bay {arrival}", "data": None}
        except Exception as e:
            return {"EC": 2, "EM": f"Loi server: {str(e)}", "data": None}

        if departure == arrival:
            return {"EC": 1, "EM": "San bay di va den khong duoc trung nhau", "data": None}

        if not date:
            date = datetime.now(VIETNAM_TZ).strftime("%Y-%m-%d")

        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Query flights with joins
                    cur.execute("""
                        SELECT f.*,
                            dep_airport.name as dep_airport_name,
                            dep_airport.city as dep_city,
                            dep_airport.terminals as dep_terminals,
                            arr_airport.name as arr_airport_name,
                            arr_airport.city as arr_city,
                            arr_airport.terminals as arr_terminals,
                            al.name as airline_name,
                            al.logo_url as airline_logo,
                            al.baggage_carry,
                            al.baggage_checked
                        FROM flights f
                        JOIN airports dep_airport ON f.departure_airport = dep_airport.airport_id
                        JOIN airports arr_airport ON f.arrival_airport = arr_airport.airport_id
                        JOIN airlines al ON f.airline_id = al.airline_id
                        WHERE f.departure_airport = %s
                          AND f.arrival_airport = %s
                          AND f.is_active = TRUE
                          AND f.status != 'cancelled'
                          AND DATE(f.departure_time) = %s
                        ORDER BY f.departure_time
                        LIMIT %s
                    """, (departure, arrival, date, limit))

                    rows = cur.fetchall()

                    # Get airport info for wrapper
                    cur.execute("SELECT name, city FROM airports WHERE airport_id = %s", (departure,))
                    dep_info = cur.fetchone()
                    cur.execute("SELECT name, city FROM airports WHERE airport_id = %s", (arrival,))
                    arr_info = cur.fetchone()

            # Build nested format matching mock generator output
            flights = []
            for r in rows:
                dep_time = r["departure_time"]
                arr_time = r["arrival_time"]
                if dep_time.tzinfo is None:
                    dep_time = dep_time.replace(tzinfo=VIETNAM_TZ)
                if arr_time.tzinfo is None:
                    arr_time = arr_time.replace(tzinfo=VIETNAM_TZ)

                dep_terminals = r["dep_terminals"] or ["T1"]
                arr_terminals = r["arr_terminals"] or ["T1"]

                duration = r["duration_minutes"] or 0
                flight = {
                    "flight_id": r["flight_id"],
                    "flight_number": r["flight_number"],
                    "airline": {
                        "code": r["airline_id"],
                        "name": r["airline_name"],
                        "logo": r["airline_logo"] or ""
                    },
                    "departure": {
                        "airport": r["dep_airport_name"],
                        "city": r["dep_city"],
                        "iata": departure,
                        "terminal": dep_terminals[0] if dep_terminals else "T1",
                        "scheduled": dep_time.isoformat(),
                        "date": dep_time.strftime("%Y-%m-%d"),
                        "time": dep_time.strftime("%H:%M")
                    },
                    "arrival": {
                        "airport": r["arr_airport_name"],
                        "city": r["arr_city"],
                        "iata": arrival,
                        "terminal": arr_terminals[0] if arr_terminals else "T1",
                        "scheduled": arr_time.isoformat(),
                        "date": arr_time.strftime("%Y-%m-%d"),
                        "time": arr_time.strftime("%H:%M")
                    },
                    "duration_minutes": duration,
                    "duration_formatted": f"{duration // 60}h {duration % 60}m",
                    "price": {
                        "economy": r["economy_price"] or 0,
                        "business": r["business_price"] or 0,
                        "first_class": r["first_class_price"] or 0,
                        "currency": "VND"
                    },
                    "available_seats": r["economy_seats"] or 0,
                    "aircraft": r["aircraft"] or "",
                    "status": r["status"] or "scheduled",
                    "baggage": {
                        "carry_on": r["baggage_carry"] or "7kg",
                        "checked": r["baggage_checked"] or "20kg"
                    }
                }
                flights.append(flight)

            return {
                "EC": 0,
                "EM": "Success",
                "data": {
                    "departure": {
                        "iata": departure,
                        "city": dep_info["city"] if dep_info else "",
                        "airport": dep_info["name"] if dep_info else ""
                    },
                    "arrival": {
                        "iata": arrival,
                        "city": arr_info["city"] if arr_info else "",
                        "airport": arr_info["name"] if arr_info else ""
                    },
                    "date": date,
                    "total": len(flights),
                    "flights": flights
                }
            }
        except Exception as e:
            return {"EC": 2, "EM": f"Loi server: {str(e)}", "data": None}


def get_flight_search_service() -> FlightSearchService:
    """Dependency injection for FlightSearchService"""
    return FlightSearchService()
