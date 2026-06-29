"""
Dataset tĩnh các lễ hội / sự kiện tiêu biểu của Việt Nam.
- Là "lưới an toàn" (safety-net) đảm bảo trang lễ hội luôn có nội dung kể cả khi
  Wikidata SPARQL / Wikipedia API bị rate-limit hoặc downtime.
- Dữ liệu mở (tổng hợp từ kiến thức phổ biến / Wikipedia), không phụ thuộc bên thứ 3.
- `month` = tháng DƯƠNG lịch xấp xỉ (để lọc); nhiều lễ theo âm lịch nên mô tả ghi rõ.
- `region`: 'north' | 'central' | 'south' | '' (cả nước).
- `image_url`: ảnh đại diện từ Wikimedia Commons (open-source, key-free). Có thể None.
"""
from typing import Any, Dict, List, Optional

# Mỗi mục: name, month (1-12 dương lịch xấp xỉ), region, location, description, lunar, image_url,
#   months (tuỳ chọn: list int — cho lễ hội trải dài nhiều tháng, vd Tết Nguyên Đán cuối T1 – đầu T2).
VN_FESTIVALS: List[Dict[str, Any]] = [
    {"name": "Tết Dương lịch (Năm mới)", "month": 1, "region": "", "location": "Toàn quốc",
     "description": "Đón năm mới Dương lịch (1/1) — pháo hoa và đêm đếm ngược tưng bừng tại các đô thị lớn.",
     "lunar": "1 tháng 1 dương lịch", "image_url": None},
    {"name": "Lễ hội Then", "month": 1, "region": "north", "location": "Hà Giang / Cao Bằng / Lạng Sơn",
     "description": "Lễ hội Then của người Tày, Nùng với đàn tính và lời ca Then, di sản văn hóa phi vật thể.",
     "lunar": "Tháng Giêng âm lịch", "image_url": None},
    {"name": "Lễ hội Lồng Tồng", "month": 1, "region": "north", "location": "Tuyên Quang / Hà Giang",
     "description": "Lễ hội xuống đồng của người Tày, cầu mưa thuận gió hòa, mùa màng bội thu.",
     "lunar": "Các ngày Thìn tháng Giêng âm lịch", "image_url": None},
    {"name": "Tết Nguyên Đán", "month": 2, "months": [1, 2], "region": "", "location": "Toàn quốc",
     "description": "Tết cổ truyền của dân tộc, đón năm mới âm lịch — lễ hội lớn nhất trong năm.",
     "lunar": "Tháng Giêng (cuối Tết dương tháng 1 – đầu tháng 2)", "image_url": None},
    {"name": "Hội Lim", "month": 2, "region": "north", "location": "Bắc Ninh",
     "description": "Lễ hội dân ca quan họ nổi tiếng, diễn ra vào tháng Giêng âm lịch.",
     "lunar": "12–13 tháng Giêng âm lịch",
     "image_url": "https://upload.wikimedia.org/wikipedia/commons/2/25/Ch%C3%B9a_Lim%2C_B%E1%BA%AFc_Ninh.JPG"},
    {"name": "Hội Gò Đống Đa", "month": 2, "region": "north", "location": "Hà Nội",
     "description": "Tưởng nhớ chiến thắng Ngọc Hồi - Đống Đa của vua Quang Trung (1789).",
     "lunar": "Mùng 5 tháng Giêng âm lịch", "image_url": None},
    {"name": "Lễ hội Yên Tử", "month": 2, "region": "north", "location": "Quảng Ninh (Uông Bí)",
     "description": "Hành hương danh thắng Yên Tử — cái nôi của Thiền phái Trúc Lâm do vua Trần Nhân Tông sáng lập.",
     "lunar": "Từ mùng 9 tháng Giêng đến hết tháng 3 âm lịch", "image_url": None},
    {"name": "Lễ hội Bà Chúa Kho", "month": 2, "region": "north", "location": "Bắc Ninh",
     "description": "Lễ hội xin lộc vay tiền đầu năm tại đền Bà Chúa Kho, đông đúc khách hành hương.",
     "lunar": "4 tháng Giêng âm lịch",
     "image_url": "https://upload.wikimedia.org/wikipedia/commons/b/be/TamquandenBaChuaKho.jpg"},
    {"name": "Lễ hội Cổ Loa", "month": 2, "region": "north", "location": "Hà Nội (Đông Anh)",
     "description": "Tưởng nhớ An Dương Vương và công cuộc dựng nước Âu Lạc với kinh thành Cổ Loa.",
     "lunar": "Rằm tháng Giêng âm lịch",
     "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/62/An_Duong_Vuong_Temple_Gate_Co_Loa.jpg/1280px-An_Duong_Vuong_Temple_Gate_Co_Loa.jpg"},
    {"name": "Lễ hội Roóng Poọc", "month": 2, "region": "north", "location": "Lào Cai (Sa Pa - Tả Van)",
     "description": "Lễ hội xuống đồng của người Giáy ở thôn Tả Van, cầu mưa thuận gió hòa, mùa màng tốt tươi.",
     "lunar": "Tháng Tư âm lịch (khoảng tháng Giêng – Hai dương)",
     "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f8/Thacbac3.jpg/1280px-Thacbac3.jpg"},
    {"name": "Hội Đền Trần (Khai ấn)", "month": 2, "region": "north", "location": "Nam Định",
     "description": "Lễ khai ấn Đền Trần đầu năm, cầu tài lộc, tưởng nhớ các vị vua nhà Trần.",
     "lunar": "Đêm 14 rạng sáng 15 tháng Giêng âm lịch", "image_url": None},
    {"name": "Hội Chùa Hương", "month": 3, "region": "north", "location": "Hà Nội (Mỹ Đức)",
     "description": "Lễ hội hành hương lớn nhất Việt Nam, kéo dài suốt 3 tháng mùa xuân.",
     "lunar": "Từ mùng 6 tháng Giêng đến hết tháng 3 âm lịch",
     "image_url": "https://upload.wikimedia.org/wikipedia/commons/5/57/Ch%C3%B9a_H%C6%B0%C6%A1ng.jpg"},
    {"name": "Lễ hội Quan Thế Âm", "month": 3, "region": "central", "location": "Đà Nẵng (Ngũ Hành Sơn)",
     "description": "Lễ hội Phật giáo quy mô lớn tại danh thắng Ngũ Hành Sơn.",
     "lunar": "19 tháng 2 âm lịch",
     "image_url": "https://upload.wikimedia.org/wikipedia/commons/e/e8/Khasarpana_Lokesvara.jpg"},
    {"name": "Lễ hội chùa Bà (Núi Bà Đen)", "month": 3, "region": "south", "location": "Tây Ninh",
     "description": "Lễ hội hành hương lớn miền Nam tại núi Bà Đen.",
     "lunar": "Rằm tháng Giêng âm lịch",
     "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ae/Dau_Tieng_Lake_-_50766650163.png/1280px-Dau_Tieng_Lake_-_50766650163.png"},
    {"name": "Lễ hội Tháp Bà Po Nagar", "month": 3, "region": "central", "location": "Khánh Hòa (Nha Trang)",
     "description": "Lễ hội của người Chăm tại tháp Po Nagar, tôn vinh nữ thần Yang Ino Pô Nagar.",
     "lunar": "20–23 tháng 3 âm lịch",
     "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5c/Nha_Trang%2C_Kh%C3%A1nh_H%C3%B2a.png/1280px-Nha_Trang%2C_Kh%C3%A1nh_H%C3%B2a.png"},
    {"name": "Hội đua voi Buôn Đôn", "month": 3, "region": "central", "location": "Đắk Lắk (Buôn Đôn)",
     "description": "Lễ hội đua voi đặc sắc của đồng bào dân tộc thiểu số Tây Nguyên.",
     "lunar": "Tháng 3 âm lịch",
     "image_url": "https://upload.wikimedia.org/wikipedia/commons/1/1b/Srepok_Ban_Don.JPG"},
    {"name": "Tết Hàn Thực", "month": 4, "region": "north", "location": "Phía Bắc Việt Nam",
     "description": "Lễ làm bánh trôi, bánh chay tưởng nhớ tổ tiên.",
     "lunar": "Mùng 3 tháng 3 âm lịch", "image_url": None},
    {"name": "Hội Đền Hùng (Giỗ tổ Hùng Vương)", "month": 4, "region": "north", "location": "Phú Thọ",
     "description": "Quốc giỗ tưởng nhớ các vua Hùng — ngày lễ trọng đại của cả nước.",
     "lunar": "Mùng 10 tháng 3 âm lịch",
     "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f8/Mausoleum_of_Hung_King.JPG/1280px-Mausoleum_of_Hung_King.JPG"},
    {"name": "Lễ hội Chol Chnam Thmay", "month": 4, "region": "south", "location": "Trà Vinh / Sóc Trăng",
     "description": "Tết cổ truyền của đồng bào Khmer Nam Bộ.", "lunar": "Giữa tháng 4 dương lịch", "image_url": None},
    {"name": "Hue Festival", "month": 4, "region": "central", "location": "Thừa Thiên - Huế",
     "description": "Liên hoan văn hóa - nghệ thuật quốc tế hàng đầu tại cố đô, tổ chức 2 năm/lần.",
     "lunar": "",
     "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cc/Ngomon2.jpg/1280px-Ngomon2.jpg"},
    {"name": "Lễ hội Cầu Ngư", "month": 2, "region": "central", "location": "Thừa Thiên - Huế",
     "description": "Lễ hội cầu ngư của ngư dân làng Thái Dương, mong một năm ra khơi bội thu.",
     "lunar": "12 tháng Giêng âm lịch",
     "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cc/Ngomon2.jpg/1280px-Ngomon2.jpg"},
    {"name": "Hội Gióng", "month": 5, "region": "north", "location": "Hà Nội (Sóc Sơn / Gia Lâm)",
     "description": "Tưởng nhớ Thánh Gióng đánh giặc Ân, di sản văn hóa phi vật thể quốc gia.",
     "lunar": "9 tháng 1 (đền Phù Đổng) và 6–8 tháng 1 (đền Sóc) âm lịch",
     "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4c/H%E1%BB%99i_Gi%C3%B3ng1.jpg/1280px-H%E1%BB%99i_Gi%C3%B3ng1.jpg"},
    {"name": "Lễ hội Điện Biên Phủ", "month": 5, "region": "north", "location": "Điện Biên",
     "description": "Kỷ niệm Chiến thắng Điện Biên Phủ lịch sử (7/5/1954).", "lunar": "",
     "image_url": "https://upload.wikimedia.org/wikipedia/commons/f/f2/%C4%90i%E1%BB%87n_Bi%C3%AAn_Ph%E1%BB%A7.JPG"},
    {"name": "Hội Áo Dài", "month": 5, "region": "central", "location": "Thừa Thiên - Huế",
     "description": "Festival tôn vinh tà áo dài truyền thống tại cố đô Huế.", "lunar": "",
     "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cc/Ngomon2.jpg/1280px-Ngomon2.jpg"},
    {"name": "Liên hoan pháo hoa quốc tế Đà Nẵng (DIFF)", "month": 6, "region": "central", "location": "Đà Nẵng",
     "description": "Liên hoan pháo hoa quốc tế thường niên tại sông Hàn, thu hút khách khắp nơi.",
     "lunar": "Tháng 6 dương lịch", "image_url": None},
    {"name": "Tết Đoan Ngọ", "month": 6, "region": "", "location": "Toàn quốc (đậm ở miền Bắc)",
     "description": "Tết giết sâu bọ, ăn bánh tro, trái cây đầu mùa.", "lunar": "Mùng 5 tháng 5 âm lịch", "image_url": None},
    {"name": "Ngày Thương binh - Liệt sĩ", "month": 7, "region": "", "location": "Toàn quốc",
     "description": "Ngày tri ân (27/7) các thương binh, liệt sĩ đã hy sinh vì nền độc lập dân tộc.",
     "lunar": "27 tháng 7 dương lịch", "image_url": None},
    {"name": "Lễ hội Bà Núi Sam", "month": 5, "region": "south", "location": "An Giang (Châu Đốc)",
     "description": "Một trong ba lễ hội lớn miền Nam, hành hương Vi Bà Núi Sam.",
     "lunar": "22–27 tháng 4 âm lịch",
     "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/18/Nh%C3%A0_ngh%E1%BB%89_tr%C3%AAn_N%C3%BAi_Sam%2C_th%C3%A0nh_ph%E1%BB%91_Ch%C3%A2u_%C4%90%E1%BB%91c.jpg/1280px-Nh%C3%A0_ngh%E1%BB%89_tr%C3%AAn_N%C3%BAi_Sam%2C_th%C3%A0nh_ph%E1%BB%91_Ch%C3%A2u_%C4%90%E1%BB%91c.jpg"},
    {"name": "Lễ Vu Lan", "month": 8, "region": "", "location": "Toàn quốc",
     "description": "Lễ báo hiếu cha mẹ (Rằm tháng Bảy), cài hoa hồng lên áo.",
     "lunar": "Rằm tháng 7 âm lịch",
     "image_url": "https://upload.wikimedia.org/wikipedia/commons/b/bd/Buddhism_Mass_in_Ghost_Festival.JPG"},
    {"name": "Lễ hội Nghinh Ông", "month": 8, "region": "south", "location": "Bà Rịa - Vũng Tàu",
     "description": "Lễ cúng cá Ông của ngư dân miền biển, cầu bình an đi biển.",
     "lunar": "16–18 tháng 8 âm lịch", "image_url": None},
    {"name": "Sene Dolta", "month": 9, "region": "south", "location": "Trà Vinh / Sóc Trăng",
     "description": "Lễ cầu siêu tưởng nhớ ông bà của người Khmer.", "lunar": "Cuối tháng 9 dương lịch", "image_url": None},
    {"name": "Hội Đền Kiếp Bạc", "month": 9, "region": "north", "location": "Hải Dương",
     "description": "Lễ giỗ Đức Thánh Trần (Trần Hưng Đạo), một trong những lễ hội lớn nhất Việt Nam.",
     "lunar": "20 tháng 8 âm lịch",
     "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/ea/Ki%E1%BA%BFp_B%E1%BA%A1c_temple_in_1904.jpg/1280px-Ki%E1%BA%BFp_B%E1%BA%A1c_temple_in_1904.jpg"},
    {"name": "Tết Trung Thu", "month": 9, "region": "", "location": "Toàn quốc (đặc biệt Hội An, Hà Nội)",
     "description": "Tết đoàn viên thiếu nhi — rước đèn ông sao, múa lân, ăn bánh nướng.",
     "lunar": "Rằm tháng 8 âm lịch",
     "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d5/Mid-Autumn_Festival-beijing.jpg/1280px-Mid-Autumn_Festival-beijing.jpg"},
    {"name": "Hội Mid-Autumn Hội An", "month": 9, "region": "central", "location": "Quảng Nam (Hội An)",
     "description": "Phố cổ Hội An rực sáng đêm Trung Thu, tôn vinh di sản giao thương.",
     "lunar": "Rằm tháng 8 âm lịch",
     "image_url": "https://upload.wikimedia.org/wikipedia/commons/f/f3/PhoCoHoiAn.jpg"},
    {"name": "Hội Kate", "month": 10, "region": "south", "location": "Ninh Thuận / Bình Thuận",
     "description": "Tết cổ truyền của người Chăm, đón năm mới theo lịch Chăm.",
     "lunar": "Đầu tháng 7 lịch Chăm (khoảng tháng 10 dương)", "image_url": None},
    {"name": "Ok Om Bok", "month": 11, "region": "south", "location": "Trà Vinh / Sóc Trăng",
     "description": "Lễ hội cúng trăng, đua ghe ngo của người Khmer.", "lunar": "Rằm tháng 10 âm lịch", "image_url": None},
    {"name": "Lễ hội hoa Đà Lạt", "month": 12, "region": "central", "location": "Lâm Đồng (Đà Lạt)",
     "description": "Liên hoan hoa quốc tế tôn vinh thành phố ngàn hoa.", "lunar": "",
     "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e2/Da_Lat_-_Viet_Nam.jpg/1280px-Da_Lat_-_Viet_Nam.jpg"},
    {"name": "Giáng sinh & chờ đón năm mới", "month": 12, "region": "", "location": "Toàn quốc",
     "description": "Khắp các đô thị lên đèn lung linh, phố đi bộ tưng bừng cuối năm.",
     "lunar": "", "image_url": None},
]


def filter_static_festivals(
    month: Optional[int] = None,
    province_norm: str = "",
    region: str = "",
) -> List[Dict[str, Any]]:
    """Lọc dataset tĩnh theo tháng (dương lịch), tỉnh (best-effort, đã strip dấu), và miền."""
    prov = (province_norm or "").strip()
    reg = (region or "").strip()
    out: List[Dict[str, Any]] = []
    for f in VN_FESTIVALS:
        if month:
            # Hỗ trợ lễ hội trải dài nhiều tháng (vd: Tết Nguyên Đán cuối T1 – đầu T2).
            months_of = [int(f["month"])] if f.get("month") else []
            extra = f.get("months")
            if isinstance(extra, list):
                months_of.extend(int(m) for m in extra)
            if int(month) not in months_of:
                continue
        if reg and f.get("region", "") and f.get("region", "") != reg:
            continue
        if prov:
            loc = _strip(f.get("location", "")) + " " + _strip(f.get("name", ""))
            if prov not in loc:
                continue
        out.append({
            "name": f["name"],
            "description": f.get("description"),
            "start_date": None,
            "end_date": None,
            "location": f.get("location"),
            "image_url": f.get("image_url"),
            "wikidata_url": None,
            "lunar": f.get("lunar") or "",
            "region": f.get("region", ""),
            "month": f.get("month"),
            "source": "curated",
        })
    return out


def _strip(text: str) -> str:
    """Bỏ dấu tiếng Việt + lower (bản nội bộ đơn giản, tránh import chéo)."""
    import re
    import unicodedata
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    s = "".join(c for c in nfkd if not unicodedata.combining(c))
    s = s.replace("đ", "d").replace("Đ", "d")
    return re.sub(r"\s+", " ", s).strip().lower()
