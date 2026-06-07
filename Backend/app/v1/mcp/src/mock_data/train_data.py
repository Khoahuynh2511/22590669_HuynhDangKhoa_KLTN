"""
Train Mock Data Configuration
Cấu hình dữ liệu cho tàu hỏa Việt Nam
"""

# Các ga tàu chính
TRAIN_STATIONS = {
    "HNO": {"name": "Ga Hà Nội", "city": "Hà Nội", "region": "north", "address": "120 Lê Duẩn, Hoàn Kiếm"},
    "SGO": {"name": "Ga Sài Gòn", "city": "Hồ Chí Minh", "region": "south", "address": "1 Nguyễn Thông, Q.3"},
    "DNA": {"name": "Ga Đà Nẵng", "city": "Đà Nẵng", "region": "central", "address": "791 Hải Phòng, Thanh Khê"},
    "HUE": {"name": "Ga Huế", "city": "Huế", "region": "central", "address": "2 Bùi Thị Xuân, Phú Hội"},
    "NTR": {"name": "Ga Nha Trang", "city": "Nha Trang", "region": "central", "address": "17 Thái Nguyên, Phước Tân"},
    "QNH": {"name": "Ga Quy Nhơn", "city": "Quy Nhơn", "region": "central", "address": "Trần Hưng Đạo, Quy Nhơn"},
    "VIN": {"name": "Ga Vinh", "city": "Vinh", "region": "north", "address": "Phan Bội Châu, Vinh"},
    "THO": {"name": "Ga Thanh Hóa", "city": "Thanh Hóa", "region": "north", "address": "Phan Chu Trinh, Thanh Hóa"},
    "NBI": {"name": "Ga Ninh Bình", "city": "Ninh Bình", "region": "north", "address": "Trần Hưng Đạo, Ninh Bình"},
    "HPG": {"name": "Ga Hải Phòng", "city": "Hải Phòng", "region": "north", "address": "75 Lương Khánh Thiện"},
    "LCA": {"name": "Ga Lào Cai", "city": "Lào Cai", "region": "north", "address": "Phố Mới, Lào Cai"},
    "BTH": {"name": "Ga Biên Hòa", "city": "Biên Hòa", "region": "south", "address": "1 Hưng Đạo Vương, Biên Hòa"},
    "PTA": {"name": "Ga Phan Thiết", "city": "Phan Thiết", "region": "south", "address": "1 Trần Hưng Đạo, Phan Thiết"},
    "THA": {"name": "Ga Tháp Chàm", "city": "Ninh Thuận", "region": "central", "address": "Thống Nhất, Phan Rang"},
    "QNG": {"name": "Ga Quảng Ngãi", "city": "Quảng Ngãi", "region": "central", "address": "Quang Trung, Quảng Ngãi"},
    "DHA": {"name": "Ga Đồng Hới", "city": "Quảng Bình", "region": "central", "address": "Trần Hưng Đạo, Đồng Hới"},
}

# Loại tàu
TRAIN_TYPES = {
    "SE": {
        "name": "Tàu SE (Thống Nhất Nhanh)",
        "description": "Tàu tốc hành Bắc - Nam",
        "speed": "fast",
        "amenities": ["Điều hòa", "Nhà vệ sinh", "Toa ăn uống", "WiFi"]
    },
    "TN": {
        "name": "Tàu TN (Thống Nhất)",
        "description": "Tàu Bắc - Nam thường",
        "speed": "normal",
        "amenities": ["Điều hòa", "Nhà vệ sinh", "Toa ăn uống"]
    },
    "SP": {
        "name": "Tàu SP (Sapa)",
        "description": "Tàu Hà Nội - Lào Cai",
        "speed": "normal",
        "amenities": ["Điều hòa", "Nhà vệ sinh", "Giường nằm"]
    },
    "HP": {
        "name": "Tàu HP (Hải Phòng)",
        "description": "Tàu Hà Nội - Hải Phòng",
        "speed": "normal",
        "amenities": ["Điều hòa", "Nhà vệ sinh"]
    },
}

# Loại ghế/giường
SEAT_TYPES = {
    "hard_seat": {
        "name": "Ghế ngồi cứng",
        "code": "NC",
        "price_multiplier": 1.0,
        "description": "Ghế ngồi thường, không điều hòa"
    },
    "soft_seat": {
        "name": "Ghế ngồi mềm",
        "code": "NM",
        "price_multiplier": 1.3,
        "description": "Ghế ngồi êm, có điều hòa"
    },
    "hard_sleeper_6": {
        "name": "Giường nằm cứng 6 người",
        "code": "N6C",
        "price_multiplier": 1.8,
        "description": "Khoang 6 giường, 3 tầng"
    },
    "soft_sleeper_6": {
        "name": "Giường nằm mềm 6 người",
        "code": "N6M",
        "price_multiplier": 2.2,
        "description": "Khoang 6 giường, có điều hòa"
    },
    "soft_sleeper_4": {
        "name": "Giường nằm mềm 4 người",
        "code": "N4M",
        "price_multiplier": 2.8,
        "description": "Khoang 4 giường VIP, có điều hòa"
    },
    "vip_cabin": {
        "name": "Khoang VIP 2 người",
        "code": "VIP",
        "price_multiplier": 4.0,
        "description": "Khoang riêng 2 giường, tiện nghi cao cấp"
    },
}

# Các tuyến tàu chính với giá cơ bản và thời gian (giờ)
TRAIN_ROUTES = {
    # Tuyến Bắc - Nam (Thống Nhất)
    ("HNO", "SGO"): {"base_price": 800000, "duration_hours": 33, "trains_per_day": 5, "train_types": ["SE", "TN"]},
    ("SGO", "HNO"): {"base_price": 800000, "duration_hours": 33, "trains_per_day": 5, "train_types": ["SE", "TN"]},

    # Tuyến Hà Nội - Đà Nẵng
    ("HNO", "DNA"): {"base_price": 450000, "duration_hours": 16, "trains_per_day": 4, "train_types": ["SE", "TN"]},
    ("DNA", "HNO"): {"base_price": 450000, "duration_hours": 16, "trains_per_day": 4, "train_types": ["SE", "TN"]},

    # Tuyến Hà Nội - Huế
    ("HNO", "HUE"): {"base_price": 380000, "duration_hours": 13, "trains_per_day": 4, "train_types": ["SE", "TN"]},
    ("HUE", "HNO"): {"base_price": 380000, "duration_hours": 13, "trains_per_day": 4, "train_types": ["SE", "TN"]},

    # Tuyến Hà Nội - Vinh
    ("HNO", "VIN"): {"base_price": 200000, "duration_hours": 6, "trains_per_day": 6, "train_types": ["SE", "TN"]},
    ("VIN", "HNO"): {"base_price": 200000, "duration_hours": 6, "trains_per_day": 6, "train_types": ["SE", "TN"]},

    # Tuyến Hà Nội - Lào Cai (Sapa)
    ("HNO", "LCA"): {"base_price": 250000, "duration_hours": 8, "trains_per_day": 4, "train_types": ["SP"]},
    ("LCA", "HNO"): {"base_price": 250000, "duration_hours": 8, "trains_per_day": 4, "train_types": ["SP"]},

    # Tuyến Hà Nội - Hải Phòng
    ("HNO", "HPG"): {"base_price": 80000, "duration_hours": 2.5, "trains_per_day": 6, "train_types": ["HP"]},
    ("HPG", "HNO"): {"base_price": 80000, "duration_hours": 2.5, "trains_per_day": 6, "train_types": ["HP"]},

    # Tuyến Sài Gòn - Nha Trang
    ("SGO", "NTR"): {"base_price": 300000, "duration_hours": 8, "trains_per_day": 4, "train_types": ["SE", "TN"]},
    ("NTR", "SGO"): {"base_price": 300000, "duration_hours": 8, "trains_per_day": 4, "train_types": ["SE", "TN"]},

    # Tuyến Sài Gòn - Đà Nẵng
    ("SGO", "DNA"): {"base_price": 500000, "duration_hours": 17, "trains_per_day": 4, "train_types": ["SE", "TN"]},
    ("DNA", "SGO"): {"base_price": 500000, "duration_hours": 17, "trains_per_day": 4, "train_types": ["SE", "TN"]},

    # Tuyến Sài Gòn - Huế
    ("SGO", "HUE"): {"base_price": 550000, "duration_hours": 20, "trains_per_day": 4, "train_types": ["SE", "TN"]},
    ("HUE", "SGO"): {"base_price": 550000, "duration_hours": 20, "trains_per_day": 4, "train_types": ["SE", "TN"]},

    # Tuyến Sài Gòn - Phan Thiết
    ("SGO", "PTA"): {"base_price": 120000, "duration_hours": 4, "trains_per_day": 3, "train_types": ["TN"]},
    ("PTA", "SGO"): {"base_price": 120000, "duration_hours": 4, "trains_per_day": 3, "train_types": ["TN"]},

    # Tuyến Đà Nẵng - Huế
    ("DNA", "HUE"): {"base_price": 80000, "duration_hours": 2.5, "trains_per_day": 6, "train_types": ["SE", "TN"]},
    ("HUE", "DNA"): {"base_price": 80000, "duration_hours": 2.5, "trains_per_day": 6, "train_types": ["SE", "TN"]},

    # Tuyến Đà Nẵng - Nha Trang
    ("DNA", "NTR"): {"base_price": 250000, "duration_hours": 9, "trains_per_day": 4, "train_types": ["SE", "TN"]},
    ("NTR", "DNA"): {"base_price": 250000, "duration_hours": 9, "trains_per_day": 4, "train_types": ["SE", "TN"]},

    # Tuyến Huế - Nha Trang
    ("HUE", "NTR"): {"base_price": 300000, "duration_hours": 11, "trains_per_day": 4, "train_types": ["SE", "TN"]},
    ("NTR", "HUE"): {"base_price": 300000, "duration_hours": 11, "trains_per_day": 4, "train_types": ["SE", "TN"]},

    # Tuyến Nha Trang - Quy Nhơn
    ("NTR", "QNH"): {"base_price": 150000, "duration_hours": 4, "trains_per_day": 3, "train_types": ["TN"]},
    ("QNH", "NTR"): {"base_price": 150000, "duration_hours": 4, "trains_per_day": 3, "train_types": ["TN"]},
}

# Giờ khởi hành phổ biến cho tàu
TRAIN_DEPARTURE_HOURS = {
    "SE": [6, 9, 14, 19, 22],  # Tàu nhanh
    "TN": [5, 8, 13, 18, 23],  # Tàu thường
    "SP": [20, 21, 22],        # Tàu đêm đi Sapa
    "HP": [6, 9, 14, 17, 19],  # Tàu Hải Phòng
}
