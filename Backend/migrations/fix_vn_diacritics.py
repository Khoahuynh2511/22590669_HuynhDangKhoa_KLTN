import psycopg2
import sys
import json
sys.stdout.reconfigure(encoding='utf-8')
from psycopg2.extras import RealDictCursor
from app.v1.core.config import settings

conn = psycopg2.connect(settings.DATABASE_URL)
with conn.cursor() as cur:
    updates = [
        ("Mường Thanh Luxury Đà Nẵng", "Đà Nẵng, Việt Nam", "Khách sạn 5 sao sang trọng nằm ngay bãi biển Mỹ Khê, tầm nhìn tuyệt đẹp ra biển Đông. Đầy đủ tiện ích cao cấp.", "K599/60 Nguyễn Tất Thành, Đà Nẵng, Việt Nam", "ARRAY['Hồ bơi ngoài trời', 'Spa & Massage', 'Nhà hàng', 'WiFi miễn phí', 'Bãi biển riêng', 'Fitness']", "Muong Thanh Luxury Da Nang"),
        ("Vinpearl Resort & Spa Phú Quốc", "Phú Quốc, Việt Nam", "Resort 5 sao trên đảo ngọc Phú Quốc, khuôn viên rộng lớn với bãi biển dài, hồ bơi vô cực và dịch vụ all-inclusive.", "Bãi Dài, Gành Dầu, Phú Quốc, Kiên Giang, Việt Nam", "ARRAY['Hồ bơi vô cực', 'Spa', 'Nhà hàng', 'Bãi biển', 'Kids Club', 'Thể thao nước']", "Vinpearl Resort & Spa Phu Quoc"),
        ("Sofitel Legend Metropole Hà Nội", "Hà Nội, Việt Nam", "Khách sạn lịch sử biểu tượng của Hà Nội từ năm 1901, nằm giữa trung tâm phố cổ, kiến trúc Pháp cổ điển.", "15 Ngô Quyền, Hoàn Kiếm, Hà Nội, Việt Nam", "ARRAY['Nhà hàng Pháp', 'Spa Le Spa', 'Bar Pool', 'WiFi', 'Lễ tân 24h', 'Butler service']", "Sofitel Legend Metropole Hanoi"),
        ("Azerai La Residence Huế", "Huế, Việt Nam", "Resort nghệ thuật bên dòng sông Hương, phong cách Art Deco kết hợp kiến trúc cung đình Huế.", "5 Lê Lợi, Huế, Thừa Thiên Huế, Việt Nam", "ARRAY['Hồ bơi mặn', 'Spa Azerai', 'Nhà hàng', 'Sông Hương view', 'WiFi', 'Cho thuê xe đạp']", "Azerai La Residence Hue"),
        ("InterContinental Nha Trang", "Nha Trang, Việt Nam", "Khách sạn 5 sao tại trung tâm Nha Trang, ngay bãi biển Trần Phú với tầm nhìn tuyệt đẹp ra vịnh.", "32-34 Trần Phú, Nha Trang, Khánh Hòa, Việt Nam", "ARRAY['Hồ bơi', 'Spa', 'Nhà hàng', 'Bãi biển', 'Trung tâm lặn', 'WiFi']", "InterContinental Nha Trang"),
        ("Đà Lạt Edensee Lake Resort", "Đà Lạt, Việt Nam", "Resort yên bình bên hồ Tuyền Lâm, không khí trong lành của Đà Lạt, phù hợp cho kỳ nghỉ thư giãn.", "Khu 3, Hồ Tuyền Lâm, Đà Lạt, Lâm Đồng, Việt Nam", "ARRAY['Hồ bơi', 'Kayak', 'Nhà hàng', 'Lò sưởi', 'WiFi', 'Vườn']", "Dalat Edensee Lake Resort"),
        ("Victoria Cần Thơ Resort", "Cần Thơ, Việt Nam", "Resort phong cách thuộc địa bên sông Hậu, cổ điển và lãng mạn, điểm khởi đầu lý tưởng cho tour chợ nổi Cái Răng.", "Phường Cái Khế, Cần Thơ, Việt Nam", "ARRAY['View sông', 'Nhà hàng', 'Hồ bơi', 'Spa', 'WiFi', 'Tour thuyền']", "Victoria Can Tho Resort"),
    ]
    for name, loc, desc, addr, amenities, old_name in updates:
        cur.execute(f"""
            UPDATE hotels SET hotel_name = %s, location = %s, description = %s, address = %s, amenities = {amenities}
            WHERE hotel_name = %s
        """, (name, loc, desc, addr, old_name))
    conn.commit()

cur2 = conn.cursor(cursor_factory=RealDictCursor)
cur2.execute('SELECT hotel_name, location FROM hotels ORDER BY price')
for r in cur2.fetchall():
    print(json.dumps(dict(r), ensure_ascii=False))
conn.close()
print('Updated!')
