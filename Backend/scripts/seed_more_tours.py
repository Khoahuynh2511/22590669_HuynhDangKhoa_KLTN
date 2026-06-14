import os
import sys
import uuid
import io
from pathlib import Path
from datetime import date, timedelta
import psycopg2

# Fix Windows encoding for emoji and Vietnamese output
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

def get_connection():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL must be set in .env")
        sys.exit(1)
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://").replace("postgres+asyncpg://", "postgresql://")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    return conn

NEW_TOURS = [
    # Đà Lạt
    {
        "package_name": "Tour Đà Lạt Premium - Trải Nghiệm Khách Sạn Colline 4 Sao",
        "destination": "Đà Lạt",
        "description": "Hành trình nghỉ dưỡng sang trọng tại trung tâm Đà Lạt. Ghé thăm các điểm check-in hot nhất như Cầu Đất Tea Hills, Dalat Fairytale Land, Dinh I Bảo Đại và thưởng thức ẩm thực Tây Nguyên.",
        "duration_days": 3,
        "price": 3850000,
        "available_slots": 15,
        "start_date": date.today() + timedelta(days=10),
        "end_date": date.today() + timedelta(days=13),
        "cuisine": "Lẩu gà lá é, Buffet rau Robin Hill, Đồ nướng ngói",
        "suitable_for": "Cặp đôi, Gia đình nhỏ",
        "image_urls": "https://s3-cmc.travel.com.vn/vtv-image/Images/TourFiles/6955/bmt city.jpg"
    },
    {
        "package_name": "Chinh Phục Đỉnh Langbiang - Cắm Trại Ngắm Sao Đêm Đà Lạt",
        "destination": "Đà Lạt",
        "description": "Tour mạo hiểm dã ngoại dành cho người thích phiêu lưu. Trekking lên đỉnh Langbiang, đốt lửa trại giao lưu cồng chiêng Tây Nguyên, cắm trại qua đêm giữa ngàn thông xanh.",
        "duration_days": 2,
        "price": 1950000,
        "available_slots": 10,
        "start_date": date.today() + timedelta(days=15),
        "end_date": date.today() + timedelta(days=17),
        "cuisine": "Cơm lam thịt nướng, Rượu cần Tây Nguyên, Khoai nướng lò",
        "suitable_for": "Nhóm bạn trẻ, Khách thích dã ngoại",
        "image_urls": "https://s3-cmc.travel.com.vn/vtv-image/Images/Tour/tfd__0_11104_beautiful-landscape-with-mountain-vi.jpg"
    },
    # Nha Trang
    {
        "package_name": "Nha Trang Bay Du Thuyền 5 Sao - Hoàng Hôn Lãng Mạn Emperor Cruise",
        "destination": "Nha Trang",
        "description": "Trải nghiệm đẳng cấp trên du thuyền Emperor Cruises tại vịnh Nha Trang. Ngắm hoàng hôn rực rỡ, thưởng thức tiệc cocktail hảo hạng, tham quan Hòn Mun và tắm biển.",
        "duration_days": 4,
        "price": 7200000,
        "available_slots": 20,
        "start_date": date.today() + timedelta(days=12),
        "end_date": date.today() + timedelta(days=16),
        "cuisine": "Tôm hùm nướng bơ tỏi, Hải sản sashimi, Bò beefsteak chuẩn Âu",
        "suitable_for": "Cặp đôi hưởng tuần trăng mật, Doanh nhân nghỉ dưỡng",
        "image_urls": "https://s3-cmc.travel.com.vn/vtv-image/Images/TourFiles/10459/GRAND WORLD (14).jpg"
    },
    {
        "package_name": "Tour Nha Trang - Khám Phá Hoang Đảo Robinson & Tắm Bùn Trăm Trứng",
        "destination": "Nha Trang",
        "description": "Vui chơi thả ga tại đảo Robinson hoang sơ, chèo thuyền Kayak, lặn ngắm rạn san hô tự nhiên, phục hồi sức khỏe bằng liệu pháp tắm bùn khoáng nóng trứ danh.",
        "duration_days": 3,
        "price": 2990000,
        "available_slots": 18,
        "start_date": date.today() + timedelta(days=8),
        "end_date": date.today() + timedelta(days=11),
        "cuisine": "Bún sứa Nha Trang, Bánh căn mực, Buffet nướng hải sản",
        "suitable_for": "Nhóm đông người, Công ty team building",
        "image_urls": "https://s3-cmc.travel.com.vn/vtv-image/Images/Tour/tfd__0_11454_shutterstock1604743951xxx.webp"
    },
    # Phú Quốc
    {
        "package_name": "Phú Quốc Nghỉ Dưỡng Grand World - Khám Phá Venice Thu Nhỏ",
        "destination": "Phú Quốc",
        "description": "Khám phá thành phố không ngủ Grand World Phú Quốc, xem show diễn thực cảnh 'Tinh hoa Việt Nam', đi thuyền trên sông Venice thu nhỏ, vui chơi tại VinWonders & Safari.",
        "duration_days": 4,
        "price": 5800000,
        "available_slots": 25,
        "start_date": date.today() + timedelta(days=14),
        "end_date": date.today() + timedelta(days=18),
        "cuisine": "Gỏi cá trích, Bún quậy Kiến Xây, Lẩu nấm tràm",
        "suitable_for": "Mọi đối tượng",
        "image_urls": "https://s3-cmc.travel.com.vn/vtv-image/Images/TourFiles/10459/GRAND WORLD (14).jpg"
    },
    {
        "package_name": "Tour Đảo Ngọc Phú Quốc - Khám Phá 4 Đảo & Cáp Treo Hòn Thơm",
        "destination": "Phú Quốc",
        "description": "Đi cáp treo vượt biển 3 dây dài nhất thế giới sang Hòn Thơm, tham gia cano tour khám phá Hòn Móng Tay, Hòn Mây Rút, lặn ngắm san hô bằng ống thở.",
        "duration_days": 3,
        "price": 3490000,
        "available_slots": 30,
        "start_date": date.today() + timedelta(days=6),
        "end_date": date.today() + timedelta(days=9),
        "cuisine": "Cơm ghẹ Hàm Nghi, Hải sản nướng mỡ hành",
        "suitable_for": "Gia đình, bạn trẻ thích tắm biển",
        "image_urls": "https://s3-cmc.travel.com.vn/vtv-image/Images/Tour/tfd__0_11454_shutterstock1604743951xxx.webp"
    },
    # Sapa
    {
        "package_name": "Sa Pa Săn Mây - Chinh Phục Fansipan & Cát Cát Ý Thơ",
        "destination": "Sapa",
        "description": "Khám phá vẻ đẹp sương mù Sa Pa. Trải nghiệm tàu hỏa leo núi Mường Hoa, đi cáp treo Fansipan ngắm thung lũng, dạo bước trong bản Cát Cát thơ mộng.",
        "duration_days": 3,
        "price": 3150000,
        "available_slots": 16,
        "start_date": date.today() + timedelta(days=5),
        "end_date": date.today() + timedelta(days=8),
        "cuisine": "Lẩu cá hồi Sapa, Thắng cố bản làng, Đồ nướng ngói Sa Pa",
        "suitable_for": "Du khách trong và ngoài nước",
        "image_urls": "https://s3-cmc.travel.com.vn/vtv-image/Images/Tour/tfd_240925113342_733533_XE LUA MUONG HOA.jpg"
    },
    {
        "package_name": "Trekking Bản Làng Sa Pa - Khám Phá Tả Van & Lao Chải Mộc Mạc",
        "destination": "Sapa",
        "description": "Trekking xuyên thung lũng Mường Hoa, đi qua các ruộng bậc thang chín vàng, lưu trú tại homestay người đồng bào H'Mông và Dao đỏ để cảm nhận văn hóa bản địa.",
        "duration_days": 4,
        "price": 2450000,
        "available_slots": 12,
        "start_date": date.today() + timedelta(days=20),
        "end_date": date.today() + timedelta(days=24),
        "cuisine": "Lợn bản cắp nách, Cơm lam, Gà đồi nướng mắc khén",
        "suitable_for": "Khách thích trải nghiệm, trekking",
        "image_urls": "https://s3-cmc.travel.com.vn/vtv-image/Images/Tour/tfd__0_11104_beautiful-landscape-with-mountain-vi.jpg"
    },
    # Đà Nẵng
    {
        "package_name": "Đà Nẵng - Hội An - Bà Nà Hills - Cầu Vàng Huyền Thoại",
        "destination": "Đà Nẵng",
        "description": "Chương trình tour du lịch miền Trung trọn gói. Khám phá bán đảo Sơn Trà, vui chơi tại Sun World Ba Na Hills với cây Cầu Vàng trứ danh, dạo chơi Phố cổ Hội An lung linh sắc màu.",
        "duration_days": 4,
        "price": 4990000,
        "available_slots": 22,
        "start_date": date.today() + timedelta(days=11),
        "end_date": date.today() + timedelta(days=15),
        "cuisine": "Bánh tráng cuốn thịt heo hai đầu da, Hải sản Năm Đảnh, Cao lầu Hội An",
        "suitable_for": "Gia đình có trẻ em & người lớn tuổi",
        "image_urls": "https://s3-cmc.travel.com.vn/vtv-image/Images/TourFiles/6955/bmt city.jpg"
    },
    # Vũng Tàu
    {
        "package_name": "Nghỉ Dưỡng Vũng Tàu - Tận Hưởng Biển Xanh & Resort Lan Rừng Phước Hải",
        "destination": "Vũng Tàu",
        "description": "Trốn phố thị ồn ào về với biển Vũng Tàu. Nghỉ mát tại resort Lan Rừng sang trọng phong cách Hy Lạp, thưởng thức buffet hải sản tươi sống và check-in ngọn hải đăng.",
        "duration_days": 2,
        "price": 2650000,
        "available_slots": 25,
        "start_date": date.today() + timedelta(days=3),
        "end_date": date.today() + timedelta(days=5),
        "cuisine": "Bánh khọt Cô Ba Vũng Tàu, Hải sản Gành Hào, Lẩu súng Phước Hải",
        "suitable_for": "Cuối tuần thư giãn cho gia đình",
        "image_urls": "https://s3-cmc.travel.com.vn/vtv-image/Images/Tour/tfd__0_11454_shutterstock1604743951xxx.webp"
    }
]

def seed_tours():
    conn = get_connection()
    cur = conn.cursor()
    
    total_inserted = 0
    for tour in NEW_TOURS:
        cur.execute("SELECT COUNT(*) FROM tour_packages WHERE package_name = %s", (tour["package_name"],))
        if cur.fetchone()[0] > 0:
            print(f"Skipped existing: {tour['package_name']}")
            continue
            
        package_id = str(uuid.uuid4())
        cur.execute(
            """
            INSERT INTO tour_packages 
                (package_id, package_name, destination, description, duration_days, price, 
                 available_slots, start_date, end_date, cuisine, suitable_for, image_urls, 
                 is_active, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, NOW(), NOW())
            """,
            (
                package_id,
                tour["package_name"],
                tour["destination"],
                tour["description"],
                tour["duration_days"],
                tour["price"],
                tour["available_slots"],
                tour["start_date"],
                tour["end_date"],
                tour["cuisine"],
                tour["suitable_for"],
                tour["image_urls"],
            )
        )
        print(f"Inserted: {tour['package_name']}")
        total_inserted += 1
        
    conn.commit()
    cur.close()
    conn.close()
    print(f"Done seeding! Inserted {total_inserted} new premium tours.")

if __name__ == "__main__":
    seed_tours()
