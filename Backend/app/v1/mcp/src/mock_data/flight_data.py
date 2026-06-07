"""
Flight Mock Data Configuration
Cấu hình dữ liệu cho chuyến bay nội địa Việt Nam
"""

# Các hãng hàng không Việt Nam
VIETNAM_AIRLINES = [
    {"code": "VN", "name": "Vietnam Airlines", "logo": "vietnam-airlines.png", "baggage_checked": "23kg", "baggage_carry": "7kg"},
    {"code": "VJ", "name": "VietJet Air", "logo": "vietjet.png", "baggage_checked": "20kg", "baggage_carry": "7kg"},
    {"code": "QH", "name": "Bamboo Airways", "logo": "bamboo.png", "baggage_checked": "20kg", "baggage_carry": "7kg"},
    {"code": "BL", "name": "Pacific Airlines", "logo": "pacific.png", "baggage_checked": "23kg", "baggage_carry": "7kg"},
]

# Sân bay Việt Nam
VIETNAM_AIRPORTS = {
    "SGN": {"name": "Tân Sơn Nhất", "city": "Hồ Chí Minh", "terminals": ["1", "2"], "region": "south"},
    "HAN": {"name": "Nội Bài", "city": "Hà Nội", "terminals": ["1", "2"], "region": "north"},
    "DAD": {"name": "Đà Nẵng", "city": "Đà Nẵng", "terminals": ["1"], "region": "central"},
    "CXR": {"name": "Cam Ranh", "city": "Nha Trang", "terminals": ["1"], "region": "central"},
    "PQC": {"name": "Phú Quốc", "city": "Phú Quốc", "terminals": ["1"], "region": "south"},
    "DLI": {"name": "Liên Khương", "city": "Đà Lạt", "terminals": ["1"], "region": "central"},
    "VDO": {"name": "Vân Đồn", "city": "Quảng Ninh", "terminals": ["1"], "region": "north"},
    "HPH": {"name": "Cát Bi", "city": "Hải Phòng", "terminals": ["1"], "region": "north"},
    "HUI": {"name": "Phú Bài", "city": "Huế", "terminals": ["1"], "region": "central"},
    "VCA": {"name": "Cần Thơ", "city": "Cần Thơ", "terminals": ["1"], "region": "south"},
    "UIH": {"name": "Phù Cát", "city": "Quy Nhơn", "terminals": ["1"], "region": "central"},
    "VII": {"name": "Vinh", "city": "Vinh", "terminals": ["1"], "region": "north"},
    "THD": {"name": "Thọ Xuân", "city": "Thanh Hóa", "terminals": ["1"], "region": "north"},
    "VCL": {"name": "Chu Lai", "city": "Quảng Nam", "terminals": ["1"], "region": "central"},
    "BMV": {"name": "Buôn Ma Thuột", "city": "Đắk Lắk", "terminals": ["1"], "region": "central"},
}

# Các tuyến bay phổ biến với giá cơ bản và thời gian bay (phút)
FLIGHT_ROUTES = {
    # Tuyến Bắc - Nam
    ("SGN", "HAN"): {"base_price": 1500000, "duration": 120, "flights_per_day": 15},
    ("HAN", "SGN"): {"base_price": 1500000, "duration": 120, "flights_per_day": 15},

    # Tuyến từ SGN
    ("SGN", "DAD"): {"base_price": 900000, "duration": 75, "flights_per_day": 10},
    ("DAD", "SGN"): {"base_price": 900000, "duration": 75, "flights_per_day": 10},
    ("SGN", "CXR"): {"base_price": 700000, "duration": 60, "flights_per_day": 8},
    ("CXR", "SGN"): {"base_price": 700000, "duration": 60, "flights_per_day": 8},
    ("SGN", "PQC"): {"base_price": 600000, "duration": 55, "flights_per_day": 12},
    ("PQC", "SGN"): {"base_price": 600000, "duration": 55, "flights_per_day": 12},
    ("SGN", "DLI"): {"base_price": 500000, "duration": 45, "flights_per_day": 6},
    ("DLI", "SGN"): {"base_price": 500000, "duration": 45, "flights_per_day": 6},
    ("SGN", "HUI"): {"base_price": 800000, "duration": 80, "flights_per_day": 5},
    ("HUI", "SGN"): {"base_price": 800000, "duration": 80, "flights_per_day": 5},
    ("SGN", "VII"): {"base_price": 1000000, "duration": 90, "flights_per_day": 4},
    ("VII", "SGN"): {"base_price": 1000000, "duration": 90, "flights_per_day": 4},
    ("SGN", "BMV"): {"base_price": 600000, "duration": 50, "flights_per_day": 4},
    ("BMV", "SGN"): {"base_price": 600000, "duration": 50, "flights_per_day": 4},

    # Tuyến từ HAN
    ("HAN", "DAD"): {"base_price": 800000, "duration": 80, "flights_per_day": 8},
    ("DAD", "HAN"): {"base_price": 800000, "duration": 80, "flights_per_day": 8},
    ("HAN", "CXR"): {"base_price": 1200000, "duration": 100, "flights_per_day": 5},
    ("CXR", "HAN"): {"base_price": 1200000, "duration": 100, "flights_per_day": 5},
    ("HAN", "PQC"): {"base_price": 1400000, "duration": 130, "flights_per_day": 4},
    ("PQC", "HAN"): {"base_price": 1400000, "duration": 130, "flights_per_day": 4},
    ("HAN", "DLI"): {"base_price": 1100000, "duration": 90, "flights_per_day": 4},
    ("DLI", "HAN"): {"base_price": 1100000, "duration": 90, "flights_per_day": 4},
    ("HAN", "HUI"): {"base_price": 600000, "duration": 70, "flights_per_day": 5},
    ("HUI", "HAN"): {"base_price": 600000, "duration": 70, "flights_per_day": 5},
    ("HAN", "HPH"): {"base_price": 400000, "duration": 35, "flights_per_day": 3},
    ("HPH", "HAN"): {"base_price": 400000, "duration": 35, "flights_per_day": 3},
    ("HAN", "VDO"): {"base_price": 500000, "duration": 45, "flights_per_day": 3},
    ("VDO", "HAN"): {"base_price": 500000, "duration": 45, "flights_per_day": 3},

    # Tuyến từ DAD
    ("DAD", "CXR"): {"base_price": 500000, "duration": 50, "flights_per_day": 3},
    ("CXR", "DAD"): {"base_price": 500000, "duration": 50, "flights_per_day": 3},
    ("DAD", "DLI"): {"base_price": 450000, "duration": 45, "flights_per_day": 3},
    ("DLI", "DAD"): {"base_price": 450000, "duration": 45, "flights_per_day": 3},
}

# Máy bay sử dụng
AIRCRAFT_TYPES = [
    {"model": "Airbus A321", "capacity": 184},
    {"model": "Boeing 787-9", "capacity": 274},
    {"model": "Airbus A350-900", "capacity": 305},
    {"model": "ATR 72-500", "capacity": 68},
    {"model": "Airbus A320", "capacity": 162},
]

# Giờ khởi hành phổ biến
DEPARTURE_HOURS = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22]
