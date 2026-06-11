"""
Seed Transport Data Script
Tạo dữ liệu Flight & Train dựa trên ngày hiện tại và insert vào PostgreSQL.
Có thể chạy lại hàng ngày để refresh data.

Usage:
    cd Backend
    python -m scripts.seed_transport_data
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "app" / "v1" / "mcp"))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

import psycopg2
from psycopg2.extras import execute_values

from src.mock_data.generator import MockDataGenerator
from src.mock_data.flight_data import (
    VIETNAM_AIRPORTS, VIETNAM_AIRLINES, FLIGHT_ROUTES,
)
from src.mock_data.train_data import (
    TRAIN_STATIONS, TRAIN_TYPES, TRAIN_ROUTES, SEAT_TYPES
)
from src.mock_data.bus_data import (
    BUS_COMPANIES, BUS_STATIONS, BUS_TYPES, BUS_SEAT_TYPES, BUS_ROUTES
)

VIETNAM_TZ = timezone(timedelta(hours=7))
DAYS_AHEAD = 14


def get_connection():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL must be set in .env")
        sys.exit(1)
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    return conn


def seed_airports(cur):
    print("  Seeding airports...")
    rows = []
    for code, info in VIETNAM_AIRPORTS.items():
        rows.append((
            code, info["name"], info["city"], info.get("region", "central"),
            info["terminals"], True
        ))
    execute_values(cur, """
        INSERT INTO airports (airport_id, name, city, region, terminals, is_active)
        VALUES %s
        ON CONFLICT (airport_id) DO UPDATE SET
            name = EXCLUDED.name, city = EXCLUDED.city,
            region = EXCLUDED.region, terminals = EXCLUDED.terminals
    """, rows)
    print(f"    -> {len(rows)} airports")


def seed_airlines(cur):
    print("  Seeding airlines...")
    rows = []
    for airline in VIETNAM_AIRLINES:
        rows.append((
            airline["code"], airline["name"], airline["logo"],
            airline["baggage_carry"], airline["baggage_checked"], True
        ))
    execute_values(cur, """
        INSERT INTO airlines (airline_id, name, logo_url, baggage_carry, baggage_checked, is_active)
        VALUES %s
        ON CONFLICT (airline_id) DO UPDATE SET
            name = EXCLUDED.name, logo_url = EXCLUDED.logo_url,
            baggage_carry = EXCLUDED.baggage_carry, baggage_checked = EXCLUDED.baggage_checked
    """, rows)
    print(f"    -> {len(rows)} airlines")


def seed_flight_routes(cur):
    print("  Seeding flight routes...")
    rows = []
    for (dep, arr), info in FLIGHT_ROUTES.items():
        rows.append((
            dep, arr, info["base_price"], info["duration"], info["flights_per_day"], True
        ))
    execute_values(cur, """
        INSERT INTO flight_routes (departure_airport, arrival_airport, base_price, duration_minutes, flights_per_day, is_active)
        VALUES %s
        ON CONFLICT (departure_airport, arrival_airport) DO UPDATE SET
            base_price = EXCLUDED.base_price, duration_minutes = EXCLUDED.duration_minutes,
            flights_per_day = EXCLUDED.flights_per_day
    """, rows)
    print(f"    -> {len(rows)} flight routes")


def seed_train_stations(cur):
    print("  Seeding train stations...")
    rows = []
    for code, info in TRAIN_STATIONS.items():
        rows.append((
            code, info["name"], info["city"], info["region"], info["address"], True
        ))
    execute_values(cur, """
        INSERT INTO train_stations (station_id, name, city, region, address, is_active)
        VALUES %s
        ON CONFLICT (station_id) DO UPDATE SET
            name = EXCLUDED.name, city = EXCLUDED.city,
            region = EXCLUDED.region, address = EXCLUDED.address
    """, rows)
    print(f"    -> {len(rows)} train stations")


def seed_train_types(cur):
    print("  Seeding train types...")
    rows = []
    for code, info in TRAIN_TYPES.items():
        rows.append((
            code, info["name"], info["description"], info["speed"], info["amenities"], True
        ))
    execute_values(cur, """
        INSERT INTO train_types (type_id, name, description, speed, amenities, is_active)
        VALUES %s
        ON CONFLICT (type_id) DO UPDATE SET
            name = EXCLUDED.name, description = EXCLUDED.description,
            speed = EXCLUDED.speed, amenities = EXCLUDED.amenities
    """, rows)
    print(f"    -> {len(rows)} train types")


def seed_seat_types(cur):
    print("  Seeding seat types...")
    rows = []
    for code, info in SEAT_TYPES.items():
        rows.append((
            code, info["name"], info["code"], info["description"],
            info["price_multiplier"], True
        ))
    execute_values(cur, """
        INSERT INTO seat_types (seat_type_id, name, code, description, price_multiplier, is_active)
        VALUES %s
        ON CONFLICT (seat_type_id) DO UPDATE SET
            name = EXCLUDED.name, code = EXCLUDED.code,
            description = EXCLUDED.description, price_multiplier = EXCLUDED.price_multiplier
    """, rows)
    print(f"    -> {len(rows)} seat types")


def seed_train_routes(cur):
    print("  Seeding train routes...")
    rows = []
    for (dep, arr), info in TRAIN_ROUTES.items():
        rows.append((
            dep, arr, info["base_price"], info["duration_hours"],
            info["trains_per_day"], info["train_types"], True
        ))
    execute_values(cur, """
        INSERT INTO train_routes (departure_station, arrival_station, base_price, duration_hours, trains_per_day, train_types, is_active)
        VALUES %s
        ON CONFLICT (departure_station, arrival_station) DO UPDATE SET
            base_price = EXCLUDED.base_price, duration_hours = EXCLUDED.duration_hours,
            trains_per_day = EXCLUDED.trains_per_day, train_types = EXCLUDED.train_types
    """, rows)
    print(f"    -> {len(rows)} train routes")


def seed_flights(cur, generator: MockDataGenerator):
    print(f"  Seeding flights ({DAYS_AHEAD} days)...")
    today = datetime.now(VIETNAM_TZ).strftime("%Y-%m-%d")
    total = 0

    for (dep, arr), route_info in FLIGHT_ROUTES.items():
        flights_data = generator.generate_flights(
            departure_iata=dep,
            arrival_iata=arr,
            date=today,
            days_ahead=DAYS_AHEAD,
            limit=route_info["flights_per_day"]
        )

        if not flights_data:
            continue

        rows = []
        for f in flights_data:
            rows.append((
                f["flight_id"],
                f["flight_number"],
                f["airline"]["code"],
                f["departure"]["iata"],
                f["arrival"]["iata"],
                f["departure"]["scheduled"],
                f["arrival"]["scheduled"],
                f["duration_minutes"],
                f["aircraft"],
                f["price"]["economy"],
                f["price"]["business"],
                f["price"]["first_class"],
                f["available_seats"],
                max(5, f["available_seats"] // 8),
                0,
                "scheduled",
                True
            ))

        if rows:
            execute_values(cur, """
                INSERT INTO flights (
                    flight_id, flight_number, airline_id, departure_airport, arrival_airport,
                    departure_time, arrival_time, duration_minutes, aircraft,
                    economy_price, business_price, first_class_price,
                    economy_seats, business_seats, first_class_seats, status, is_active
                ) VALUES %s
                ON CONFLICT (flight_id) DO UPDATE SET
                    economy_price = EXCLUDED.economy_price,
                    business_price = EXCLUDED.business_price,
                    first_class_price = EXCLUDED.first_class_price,
                    economy_seats = EXCLUDED.economy_seats,
                    status = EXCLUDED.status
            """, rows)
            total += len(rows)

    print(f"    -> {total} flights across {len(FLIGHT_ROUTES)} routes")


def seed_trains(cur, generator: MockDataGenerator):
    print(f"  Seeding trains ({DAYS_AHEAD} days)...")
    today = datetime.now(VIETNAM_TZ).strftime("%Y-%m-%d")
    total_trains = 0
    total_seat_prices = 0

    for (dep, arr), route_info in TRAIN_ROUTES.items():
        trains_data = generator.generate_trains(
            departure_station=dep,
            arrival_station=arr,
            date=today,
            days_ahead=DAYS_AHEAD,
            limit=route_info["trains_per_day"]
        )

        if not trains_data:
            continue

        train_rows = []
        seat_price_rows = []

        for t in trains_data:
            train_rows.append((
                t["train_id"],
                t["train_number"],
                t["train_type"]["code"],
                t["departure"]["code"],
                t["arrival"]["code"],
                t["departure"]["scheduled"],
                t["arrival"]["scheduled"],
                t["duration_hours"],
                "scheduled",
                True
            ))

            for seat_code, seat_info in t["seats"].items():
                available = t["availability"].get(seat_code, 0)
                seat_price_rows.append((
                    t["train_id"],
                    seat_code,
                    seat_info["price"],
                    available
                ))

        if train_rows:
            execute_values(cur, """
                INSERT INTO trains (
                    train_id, train_number, train_type_id, departure_station, arrival_station,
                    departure_time, arrival_time, duration_hours, status, is_active
                ) VALUES %s
                ON CONFLICT (train_id) DO UPDATE SET
                    status = EXCLUDED.status
            """, train_rows)
            total_trains += len(train_rows)

        if seat_price_rows:
            execute_values(cur, """
                INSERT INTO train_seat_prices (train_id, seat_type_id, price, available_seats)
                VALUES %s
                ON CONFLICT (train_id, seat_type_id) DO UPDATE SET
                    price = EXCLUDED.price, available_seats = EXCLUDED.available_seats
            """, seat_price_rows)
            total_seat_prices += len(seat_price_rows)

    print(f"    -> {total_trains} trains across {len(TRAIN_ROUTES)} routes")
    print(f"    -> {total_seat_prices} seat price entries")


def seed_bus_companies(cur):
    print("  Seeding bus companies...")
    rows = []
    for company in BUS_COMPANIES:
        rows.append((
            company["code"], company["name"], company.get("logo"),
            company.get("phone"), company.get("amenities", []), company.get("rating", 4.0), True
        ))
    execute_values(cur, """
        INSERT INTO bus_companies (company_id, name, logo_url, phone, amenities, rating, is_active)
        VALUES %s
        ON CONFLICT (company_id) DO UPDATE SET
            name = EXCLUDED.name, logo_url = EXCLUDED.logo_url,
            phone = EXCLUDED.phone, amenities = EXCLUDED.amenities, rating = EXCLUDED.rating
    """, rows)
    print(f"    -> {len(rows)} bus companies")


def seed_bus_stations(cur):
    print("  Seeding bus stations...")
    rows = []
    for code, info in BUS_STATIONS.items():
        rows.append((
            code, info["name"], info["city"], info["region"],
            info["address"], True
        ))
    execute_values(cur, """
        INSERT INTO bus_stations (station_id, name, city, region, address, is_active)
        VALUES %s
        ON CONFLICT (station_id) DO UPDATE SET
            name = EXCLUDED.name, city = EXCLUDED.city,
            region = EXCLUDED.region, address = EXCLUDED.address
    """, rows)
    print(f"    -> {len(rows)} bus stations")


def seed_bus_types(cur):
    print("  Seeding bus types...")
    rows = []
    for code, info in BUS_TYPES.items():
        rows.append((
            code, info["name"], info["description"],
            info["capacity"], info.get("amenities", []), True
        ))
    execute_values(cur, """
        INSERT INTO bus_types (type_id, name, description, capacity, amenities, is_active)
        VALUES %s
        ON CONFLICT (type_id) DO UPDATE SET
            name = EXCLUDED.name, description = EXCLUDED.description,
            capacity = EXCLUDED.capacity, amenities = EXCLUDED.amenities
    """, rows)
    print(f"    -> {len(rows)} bus types")


def seed_bus_seat_types(cur):
    print("  Seeding bus seat types...")
    rows = []
    for code, info in BUS_SEAT_TYPES.items():
        rows.append((
            code, info["name"], info["code"], info["description"],
            info["price_multiplier"], True
        ))
    execute_values(cur, """
        INSERT INTO bus_seat_types (seat_type_id, name, code, description, price_multiplier, is_active)
        VALUES %s
        ON CONFLICT (seat_type_id) DO UPDATE SET
            name = EXCLUDED.name, code = EXCLUDED.code,
            description = EXCLUDED.description, price_multiplier = EXCLUDED.price_multiplier
    """, rows)
    print(f"    -> {len(rows)} bus seat types")


def seed_bus_routes(cur):
    print("  Seeding bus routes...")
    rows = []
    for (dep, arr), info in BUS_ROUTES.items():
        rows.append((
            dep, arr, info["base_price"], info["duration_hours"],
            info["buses_per_day"], info["bus_types"], True
        ))
    execute_values(cur, """
        INSERT INTO bus_routes (departure_station, arrival_station, base_price, duration_hours, buses_per_day, bus_types, is_active)
        VALUES %s
        ON CONFLICT (departure_station, arrival_station) DO UPDATE SET
            base_price = EXCLUDED.base_price, duration_hours = EXCLUDED.duration_hours,
            buses_per_day = EXCLUDED.buses_per_day, bus_types = EXCLUDED.bus_types
    """, rows)
    print(f"    -> {len(rows)} bus routes")


def seed_buses(cur, generator: MockDataGenerator):
    print(f"  Seeding buses ({DAYS_AHEAD} days)...")
    today = datetime.now(VIETNAM_TZ).strftime("%Y-%m-%d")
    total = 0

    for (dep, arr), route_info in BUS_ROUTES.items():
        buses_data = generator.generate_buses(
            departure_station=dep,
            arrival_station=arr,
            date=today,
            days_ahead=DAYS_AHEAD,
            limit=route_info["buses_per_day"]
        )

        if not buses_data:
            continue

        rows = []
        for b in buses_data:
            rows.append((
                b["bus_id"],
                b["bus_number"],
                b["company"]["code"],
                b["bus_type"]["code"],
                b["departure"]["code"],
                b["arrival"]["code"],
                b["departure"]["scheduled"],
                b["arrival"]["scheduled"],
                b["duration_hours"],
                b["total_seats"],
                b["available_seats"],
                b["seats"].get("standard", {}).get("price", 0) if isinstance(b.get("seats"), dict) else 0,
                "scheduled",
                True
            ))

        if rows:
            execute_values(cur, """
                INSERT INTO buses (
                    bus_id, bus_number, company_id, bus_type_id, departure_station, arrival_station,
                    departure_time, arrival_time, duration_hours, total_seats, available_seats,
                    base_price, status, is_active
                ) VALUES %s
                ON CONFLICT (bus_id) DO UPDATE SET
                    available_seats = EXCLUDED.available_seats,
                    base_price = EXCLUDED.base_price,
                    status = EXCLUDED.status
            """, rows)
            total += len(rows)

    print(f"    -> {total} buses across {len(BUS_ROUTES)} routes")


def cleanup_old_data(cur):
    print("  Cleaning up expired data...")
    now = datetime.now(VIETNAM_TZ).isoformat()
    # Delete bookings referencing expired transports first (FK constraints)
    cur.execute("DELETE FROM train_bookings WHERE train_id IN (SELECT train_id FROM trains WHERE departure_time < %s)", (now,))
    cur.execute("DELETE FROM train_seat_prices WHERE train_id IN (SELECT train_id FROM trains WHERE departure_time < %s)", (now,))
    cur.execute("DELETE FROM trains WHERE departure_time < %s", (now,))
    cur.execute("DELETE FROM flight_bookings WHERE flight_id IN (SELECT flight_id FROM flights WHERE departure_time < %s)", (now,))
    cur.execute("DELETE FROM flights WHERE departure_time < %s", (now,))
    cur.execute("DELETE FROM bus_bookings WHERE bus_id IN (SELECT bus_id FROM buses WHERE departure_time < %s)", (now,))
    cur.execute("DELETE FROM buses WHERE departure_time < %s", (now,))
    print("    -> Done")


def main():
    print("=" * 60)
    print("  SEED TRANSPORT DATA")
    print(f"  Date: {datetime.now(VIETNAM_TZ).strftime('%Y-%m-%d %H:%M')}")
    print(f"  Generating data for next {DAYS_AHEAD} days")
    print("=" * 60)

    conn = get_connection()
    cur = conn.cursor()
    generator = MockDataGenerator()

    # Step 1: Seed reference/static data
    print("\n[1/3] Seeding reference data...")
    seed_airports(cur)
    seed_airlines(cur)
    seed_flight_routes(cur)
    seed_train_stations(cur)
    seed_train_types(cur)
    seed_seat_types(cur)
    seed_train_routes(cur)
    seed_bus_companies(cur)
    seed_bus_stations(cur)
    seed_bus_types(cur)
    seed_bus_seat_types(cur)
    seed_bus_routes(cur)

    # Step 2: Cleanup old data
    print("\n[2/3] Cleaning up old data...")
    cleanup_old_data(cur)

    # Step 3: Seed dynamic data (flights, trains & buses)
    print("\n[3/3] Seeding dynamic transport data...")
    seed_flights(cur, generator)
    seed_trains(cur, generator)
    seed_buses(cur, generator)

    cur.close()
    conn.close()

    print("\n" + "=" * 60)
    print("  DONE! All transport data seeded successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()
