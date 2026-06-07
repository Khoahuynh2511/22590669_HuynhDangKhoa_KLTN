"""
Mock Data Generator Module
Tạo dữ liệu giả lập cho Flight và Train booking
"""

from .generator import MockDataGenerator
from .flight_data import VIETNAM_AIRPORTS, VIETNAM_AIRLINES, FLIGHT_ROUTES
from .train_data import TRAIN_STATIONS, TRAIN_TYPES, TRAIN_ROUTES

__all__ = [
    "MockDataGenerator",
    "VIETNAM_AIRPORTS",
    "VIETNAM_AIRLINES",
    "FLIGHT_ROUTES",
    "TRAIN_STATIONS",
    "TRAIN_TYPES",
    "TRAIN_ROUTES",
]
