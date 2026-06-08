"""
Flight API Endpoints
"""
from mock_data.flight_data import VIETNAM_AIRPORTS, VIETNAM_AIRLINES
from mock_data.generator import get_generator
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timezone, timedelta
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'mcp', 'src')))

router = APIRouter()
vietnam_tz = timezone(timedelta(hours=7))
generator = get_generator()


@router.get("/airports")
async def get_airports():
    airports = []
    for code, info in VIETNAM_AIRPORTS.items():
        airports.append({"code": code,
                         "name": info["name"],
                         "city": info["city"],
                         "region": info["region"],
                         "terminals": info["terminals"]})
    return {"EC": 0, "EM": "Success", "data": airports}


@router.get("/airlines")
async def get_airlines():
    return {"EC": 0, "EM": "Success", "data": VIETNAM_AIRLINES}


@router.get("/search")
async def search_flights(
    departure: str = Query(...),
    arrival: str = Query(...),
    date: Optional[str] = Query(None),
    limit: int = Query(
        10,
        ge=1,
        le=20)):
    departure = departure.upper()
    arrival = arrival.upper()
    if departure not in VIETNAM_AIRPORTS:
        return {"EC": 1, "EM": f"Khong tim thay san bay {departure}", "data": None}
    if arrival not in VIETNAM_AIRPORTS:
        return {"EC": 1, "EM": f"Khong tim thay san bay {arrival}", "data": None}
    if departure == arrival:
        return {"EC": 1, "EM": "San bay di va den khong duoc trung nhau", "data": None}
    if not date:
        date = datetime.now(vietnam_tz).strftime("%Y-%m-%d")
    flights = generator.generate_flights(
        departure_iata=departure,
        arrival_iata=arrival,
        date=date,
        days_ahead=1,
        limit=limit)
    return {
        "EC": 0,
        "EM": "Success",
        "data": {
            "departure": {
                "iata": departure,
                "city": VIETNAM_AIRPORTS[departure]["city"],
                "airport": VIETNAM_AIRPORTS[departure]["name"]},
            "arrival": {
                "iata": arrival,
                "city": VIETNAM_AIRPORTS[arrival]["city"],
                "airport": VIETNAM_AIRPORTS[arrival]["name"]},
            "date": date,
            "total": len(flights),
            "flights": flights}}
