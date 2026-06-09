"""
Train API Endpoints
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'mcp', 'src')))

from mock_data.train_data import TRAIN_STATIONS, TRAIN_TYPES, SEAT_TYPES
from mock_data.generator import get_generator
from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime, timezone, timedelta

router = APIRouter()
vietnam_tz = timezone(timedelta(hours=7))
generator = get_generator()


@router.get("/stations")
async def get_stations():
    stations = []
    for code, info in TRAIN_STATIONS.items():
        stations.append({"code": code,
                         "name": info["name"],
                         "city": info["city"],
                         "region": info["region"],
                         "address": info["address"]})
    return {"EC": 0, "EM": "Success", "data": stations}


@router.get("/types")
async def get_train_types():
    return {"EC": 0, "EM": "Success", "data": {"train_types": TRAIN_TYPES, "seat_types": SEAT_TYPES}}


@router.get("/search")
async def search_trains(
    departure: str = Query(...),
    arrival: str = Query(...),
    date: Optional[str] = Query(None),
    limit: int = Query(
        10,
        ge=1,
        le=20)):
    departure = departure.upper()
    arrival = arrival.upper()
    if departure not in TRAIN_STATIONS:
        return {"EC": 1, "EM": f"Khong tim thay ga tau {departure}", "data": None}
    if arrival not in TRAIN_STATIONS:
        return {"EC": 1, "EM": f"Khong tim thay ga tau {arrival}", "data": None}
    if departure == arrival:
        return {"EC": 1, "EM": "Ga di va den khong duoc trung nhau", "data": None}
    if not date:
        date = datetime.now(vietnam_tz).strftime("%Y-%m-%d")
    trains = generator.generate_trains(
        departure_station=departure,
        arrival_station=arrival,
        date=date,
        days_ahead=1,
        limit=limit)
    return {
        "EC": 0,
        "EM": "Success",
        "data": {
            "departure": {
                "code": departure,
                "city": TRAIN_STATIONS[departure]["city"],
                "station": TRAIN_STATIONS[departure]["name"]},
            "arrival": {
                "code": arrival,
                "city": TRAIN_STATIONS[arrival]["city"],
                "station": TRAIN_STATIONS[arrival]["name"]},
            "date": date,
            "total": len(trains),
            "trains": trains,
            "seat_types": SEAT_TYPES}}
