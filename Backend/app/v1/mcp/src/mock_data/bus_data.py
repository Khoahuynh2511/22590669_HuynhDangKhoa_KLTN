"""
Bus Mock Data Configuration
Cấu hình dữ liệu cho xe khách nội địa Việt Nam
"""

# Các hãng xe khách Việt Nam
BUS_COMPANIES = [
    {"code": "SM", "name": "Xe Sao Mai", "logo": "sao-mai.png", "phone": "1900 6067", "amenities": ["WiFi", "A/C", "Nước uống", "Chăn mền"], "rating": 4.5},
    {"code": "PT", "name": "Phương Trang (FUTA)", "logo": "phuong-trang.png", "phone": "1900 6068", "amenities": ["WiFi", "A/C", "Nước uống", "Báo"], "rating": 4.3},
    {"code": "FT", "name": "Futabus", "logo": "futabus.png", "phone": "1900 6069", "amenities": ["WiFi", "A/C", "TV", "USB sạc"], "rating": 4.4},
    {"code": "KH", "name": "Kumho Saigon Express", "logo": "kumho.png", "phone": "1900 6070", "amenities": ["WiFi", "A/C", "Chăn mền", "Nước uống"], "rating": 4.6},
    {"code": "TB", "name": "Thành Bưởi", "logo": "thanh-buoi.png", "phone": "1900 6071", "amenities": ["A/C", "Nước uống"], "rating": 4.0},
    {"code": "HL", "name": "Hoàng Long", "logo": "hoang-long.png", "phone": "1900 6072", "amenities": ["A/C", "Nước uống", "Chăn mền"], "rating": 4.1},
]

# Bến xe Việt Nam
BUS_STATIONS = {
    "BXSG": {"name": "Bến xe Miền Đông", "city": "Hồ Chí Minh", "region": "south", "address": "292 Đinh Bộ Lĩnh, Bình Thạnh"},
    "BXHN": {"name": "Bến xe Giáp Bát", "city": "Hà Nội", "region": "north", "address": "20 Giáp Bát, Hoàng Mai"},
    "BXDN": {"name": "Bến xe Đà Nẵng", "city": "Đà Nẵng", "region": "central", "address": "Tôn Đức Thắng, Liên Chiểu"},
    "BXNT": {"name": "Bến xe Nha Trang", "city": "Nha Trang", "region": "central", "address": "23 Tháng 10, Nha Trang"},
    "BXDL": {"name": "Bến xe Đà Lạt", "city": "Đà Lạt", "region": "central", "address": "Tôn Thất Tùng, Đà Lạt"},
    "BXPT": {"name": "Bến xe Phan Thiết", "city": "Phan Thiết", "region": "south", "address": "Chu Văn An, Phan Thiết"},
    "BXVL": {"name": "Bến xe Vũng Tàu", "city": "Vũng Tàu", "region": "south", "address": "Nguyễn An Ninh, Vũng Tàu"},
    "BXCT": {"name": "Bến xe Cần Thơ", "city": "Cần Thơ", "region": "south", "address": "Nguyễn Trãi, Cần Thơ"},
    "BXHP": {"name": "Bến xe Niệm Nghĩa", "city": "Hải Phòng", "region": "north", "address": "Máy Tành, Hải Phòng"},
    "BXQN": {"name": "Bến xe Quy Nhơn", "city": "Quy Nhơn", "region": "central", "address": "Nguyễn Huệ, Quy Nhơn"},
    "BXHUE": {"name": "Bến xe Trung tâm Huế", "city": "Huế", "region": "central", "address": "An Dương Vương, Huế"},
    "BXLC": {"name": "Bến xe Lào Cai", "city": "Lào Cai", "region": "north", "address": "Điện Biên Phủ, Lào Cai"},
    "BXVIN": {"name": "Bến xe Vinh", "city": "Vinh", "region": "north", "address": "Lê Duẩn, Vinh"},
    "BXDH": {"name": "Bến xe Đồng Hới", "city": "Quảng Bình", "region": "central", "address": "Lý Thường Kiệt, Đồng Hới"},
    "BXNB": {"name": "Bến xe Ninh Bình", "city": "Ninh Bình", "region": "north", "address": "Trần Hưng Đạo, Ninh Bình"},
}

# Loại xe
BUS_TYPES = {
    "limousine_9": {
        "name": "Xe Limousine 9 chỗ",
        "description": "Xe limousine cao cấp, ghế ngả rộng, không gian riêng tư",
        "capacity": 9,
        "amenities": ["WiFi", "A/C", "TV", "USB sạc", "Nước uống", "Chăn mền"]
    },
    "limousine_11": {
        "name": "Xe Limousine 11 chỗ",
        "description": "Xe limousine tiêu chuẩn, thoải mái",
        "capacity": 11,
        "amenities": ["WiFi", "A/C", "TV", "USB sạc", "Nước uống"]
    },
    "sleeper_40": {
        "name": "Xe Giường Nằm 40 chỗ",
        "description": "Xe giường nằm 2 tầng, giường rộng",
        "capacity": 40,
        "amenities": ["A/C", "Chăn mền", "Nước uống", "Nhà vệ sinh"]
    },
    "sleeper_34": {
        "name": "Xe Giường Nằm 34 chỗ (Cabin)",
        "description": "Xe cabin cao cấp, giường riêng tư có rèm",
        "capacity": 34,
        "amenities": ["WiFi", "A/C", "TV", "Chăn mền", "Nước uống", "Nhà vệ sinh", "USB sạc"]
    },
}

# Loại ghế / giường
BUS_SEAT_TYPES = {
    "standard": {
        "name": "Ghế ngồi thường",
        "code": "GN",
        "price_multiplier": 1.0,
        "description": "Ghế ngồi tiêu chuẩn, có điều hòa"
    },
    "premium": {
        "name": "Ghế ngồi VIP",
        "code": "GV",
        "price_multiplier": 1.4,
        "description": "Ghế ngả sâu, rộng hơn, nhiều không gian hơn"
    },
    "single_sleeper": {
        "name": "Giường nằm đơn",
        "code": "GD",
        "price_multiplier": 2.0,
        "description": "Giường nằm riêng, không chia sẻ"
    },
    "double_sleeper": {
        "name": "Giường nằm đôi",
        "code": "GN",
        "price_multiplier": 1.6,
        "description": "Giường nằm 2 người, phù hợp cặp đôi"
    },
}

# Các tuyến xe phổ biến với giá cơ bản và thời gian (giờ)
BUS_ROUTES = {
    # Tuyến Bắc - Nam
    ("BXSG", "BXHN"): {"base_price": 650000, "duration_hours": 36, "buses_per_day": 8, "bus_types": ["sleeper_40", "sleeper_34"]},
    ("BXHN", "BXSG"): {"base_price": 650000, "duration_hours": 36, "buses_per_day": 8, "bus_types": ["sleeper_40", "sleeper_34"]},

    # Tuyến từ HCM
    ("BXSG", "BXDN"): {"base_price": 350000, "duration_hours": 18, "buses_per_day": 10, "bus_types": ["sleeper_40", "limousine_11"]},
    ("BXDN", "BXSG"): {"base_price": 350000, "duration_hours": 18, "buses_per_day": 10, "bus_types": ["sleeper_40", "limousine_11"]},
    ("BXSG", "BXNT"): {"base_price": 280000, "duration_hours": 10, "buses_per_day": 12, "bus_types": ["sleeper_40", "limousine_9", "limousine_11"]},
    ("BXNT", "BXSG"): {"base_price": 280000, "duration_hours": 10, "buses_per_day": 12, "bus_types": ["sleeper_40", "limousine_9", "limousine_11"]},
    ("BXSG", "BXDL"): {"base_price": 300000, "duration_hours": 7, "buses_per_day": 15, "bus_types": ["limousine_9", "limousine_11", "sleeper_40"]},
    ("BXDL", "BXSG"): {"base_price": 300000, "duration_hours": 7, "buses_per_day": 15, "bus_types": ["limousine_9", "limousine_11", "sleeper_40"]},
    ("BXSG", "BXPT"): {"base_price": 180000, "duration_hours": 4.5, "buses_per_day": 20, "bus_types": ["limousine_9", "limousine_11"]},
    ("BXPT", "BXSG"): {"base_price": 180000, "duration_hours": 4.5, "buses_per_day": 20, "bus_types": ["limousine_9", "limousine_11"]},
    ("BXSG", "BXVL"): {"base_price": 150000, "duration_hours": 2.5, "buses_per_day": 25, "bus_types": ["limousine_9", "limousine_11"]},
    ("BXVL", "BXSG"): {"base_price": 150000, "duration_hours": 2.5, "buses_per_day": 25, "bus_types": ["limousine_9", "limousine_11"]},
    ("BXSG", "BXCT"): {"base_price": 220000, "duration_hours": 5, "buses_per_day": 10, "bus_types": ["limousine_11", "sleeper_40"]},
    ("BXCT", "BXSG"): {"base_price": 220000, "duration_hours": 5, "buses_per_day": 10, "bus_types": ["limousine_11", "sleeper_40"]},

    # Tuyến từ Hà Nội
    ("BXHN", "BXDN"): {"base_price": 400000, "duration_hours": 18, "buses_per_day": 6, "bus_types": ["sleeper_40", "sleeper_34"]},
    ("BXDN", "BXHN"): {"base_price": 400000, "duration_hours": 18, "buses_per_day": 6, "bus_types": ["sleeper_40", "sleeper_34"]},
    ("BXHN", "BXHP"): {"base_price": 120000, "duration_hours": 2.5, "buses_per_day": 20, "bus_types": ["limousine_9", "limousine_11"]},
    ("BXHP", "BXHN"): {"base_price": 120000, "duration_hours": 2.5, "buses_per_day": 20, "bus_types": ["limousine_9", "limousine_11"]},
    ("BXHN", "BXLC"): {"base_price": 350000, "duration_hours": 6, "buses_per_day": 8, "bus_types": ["sleeper_40", "limousine_11"]},
    ("BXLC", "BXHN"): {"base_price": 350000, "duration_hours": 6, "buses_per_day": 8, "bus_types": ["sleeper_40", "limousine_11"]},
    ("BXHN", "BXNB"): {"base_price": 100000, "duration_hours": 2, "buses_per_day": 15, "bus_types": ["limousine_9", "limousine_11"]},
    ("BXNB", "BXHN"): {"base_price": 100000, "duration_hours": 2, "buses_per_day": 15, "bus_types": ["limousine_9", "limousine_11"]},
    ("BXHN", "BXVIN"): {"base_price": 180000, "duration_hours": 4, "buses_per_day": 10, "bus_types": ["limousine_11", "sleeper_40"]},

    # Tuyến miền Trung
    ("BXDN", "BXHUE"): {"base_price": 120000, "duration_hours": 3, "buses_per_day": 12, "bus_types": ["limousine_9", "limousine_11"]},
    ("BXHUE", "BXDN"): {"base_price": 120000, "duration_hours": 3, "buses_per_day": 12, "bus_types": ["limousine_9", "limousine_11"]},
    ("BXDN", "BXQN"): {"base_price": 150000, "duration_hours": 4, "buses_per_day": 8, "bus_types": ["limousine_11", "sleeper_40"]},
    ("BXNT", "BXDL"): {"base_price": 180000, "duration_hours": 4, "buses_per_day": 10, "bus_types": ["limousine_9", "limousine_11"]},
    ("BXDL", "BXNT"): {"base_price": 180000, "duration_hours": 4, "buses_per_day": 10, "bus_types": ["limousine_9", "limousine_11"]},
}

# Giờ khởi hành theo loại xe
BUS_DEPARTURE_HOURS = {
    "limousine_9": [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22],
    "limousine_11": [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22],
    "sleeper_40": [5, 7, 9, 11, 13, 15, 17, 19, 21, 23],
    "sleeper_34": [6, 8, 10, 14, 18, 20, 22],
}
