"""
Seed Activity Packages Data
Tạo dữ liệu hoạt động du lịch theo buổi (sáng/trưa/chiều) cho các điểm đến phổ biến.

Usage:
    cd Backend
    python -m scripts.seed_activity_packages
"""

import os
import sys
import io
from pathlib import Path

# Fix Windows encoding for emoji output
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

import psycopg2

from scripts.activity_seed_extra import EXTRA_ACTIVITIES


def normalize_db_url(db_url: str) -> str:
    """Convert asyncpg-style URL to psycopg2-compatible URL."""
    return (
        db_url.replace("postgresql+asyncpg://", "postgresql://")
        .replace("postgres+asyncpg://", "postgresql://")
    )


def get_connection():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL must be set in .env")
        sys.exit(1)
    conn = psycopg2.connect(normalize_db_url(db_url))
    conn.autocommit = True
    return conn


def merge_activities() -> dict:
    """Merge base and extended activity data."""
    merged = {dest: list(items) for dest, items in ACTIVITIES.items()}
    for destination, activities in EXTRA_ACTIVITIES.items():
        merged.setdefault(destination, [])
        merged[destination].extend(activities)
    return merged


# ============================================================
# Activity data per destination
# Each activity has: name, description, time_slot, category,
#   duration_hours, price, difficulty, location, included_services
# ============================================================

ACTIVITIES = {
    "Đà Lạt": [
        # === MORNING ===
        {
            "name": "Thác Prenn - Khám phá thiên nhiên",
            "description": "Khám phá thác Prenn tuyệt đẹp giữa rừng thông bát ngát. Trải nghiệm đi bộ trên cầu treo, ngắm thác nước từ trên cao và hòa mình vào thiên nhiên.",
            "time_slot": "morning",
            "category": "nature",
            "duration_hours": 3.0,
            "price": 150000,
            "difficulty": "easy",
            "location": "Thác Prenn, TP. Đà Lạt",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Vé vào cổng", "Hướng dẫn viên", "Nước uống"],
        },
        {
            "name": "Hồ Xuân Hương - Chèo thuyền",
            "description": "Tận hưởng buổi sáng thanh bình trên Hồ Xuân Hương bằng thuyền đạp vịt, ngắm cảnh hai bên hồ và pháo đài cổ.",
            "time_slot": "morning",
            "category": "relax",
            "duration_hours": 2.0,
            "price": 80000,
            "difficulty": "easy",
            "location": "Hồ Xuân Hương, Trung tâm TP. Đà Lạt",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Thuê thuyền 1 tiếng"],
        },
        {
            "name": "Ga Đà Lạt - Đi tàu cổ",
            "description": "Trải nghiệm đi tàu hỏa cổ từ Ga Đà Lạt đến Trại Mát, ngắm cảnh đồi chè và vườn hoa dọc đường.",
            "time_slot": "morning",
            "category": "culture",
            "duration_hours": 2.5,
            "price": 120000,
            "difficulty": "easy",
            "location": "Ga Đà Lạt, Phường 10",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Vé tàu khứ hồi", "Hướng dẫn"],
        },
        {
            "name": "Đồi chè Cầu Đất - Tham quan",
            "description": "Tham quan đồi chè trăm năm, tìm hiểu quy trình sản xuất trà và thưởng thức trà tươi tại vườn.",
            "time_slot": "morning",
            "category": "nature",
            "duration_hours": 3.0,
            "price": 100000,
            "difficulty": "easy",
            "location": "Đồi chè Cầu Đất, Cầu Đất",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Vé tham quan", "Thưởng trà miễn phí"],
        },
        {
            "name": "Trekking Bidoup - Khám phá rừng nguyên sinh",
            "description": "Khám phá vườn quốc gia Bidoup Núi Bà với rừng nguyên sinh, thác nước và hệ sinh thái đa dạng.",
            "time_slot": "morning",
            "category": "adventure",
            "duration_hours": 5.0,
            "price": 350000,
            "difficulty": "hard",
            "location": "VQG Bidoup Núi Bà, Lạc Dương",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Vé vào cổng", "Hướng dẫn viên", "Bữa trưa nhẹ", "Nước uống"],
        },
        # === AFTERNOON ===
        {
            "name": "Đồi Mộng Mơ - Vườn hoa & Hồ cá",
            "description": "Tham quan khu du lịch Đồi Mộng Mơ với vườn hoa bốn mùa, hồ cá Koi và nhà rông Tây Nguyên.",
            "time_slot": "afternoon",
            "category": "relax",
            "duration_hours": 2.5,
            "price": 100000,
            "difficulty": "easy",
            "location": "Đồi Mộng Mơ, Phường 5",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Vé vào cổng"],
        },
        {
            "name": "Vườn dâu Dalat Strawberries",
            "description": "Tự hái dâu tươi tại vườn, thưởng thức sữa dâu và mua đặc sản về làm quà.",
            "time_slot": "afternoon",
            "category": "nature",
            "duration_hours": 2.0,
            "price": 80000,
            "difficulty": "easy",
            "location": "Vườn dâu, Trại Mát",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Khay dâu hái miễn phí 500g"],
        },
        {
            "name": "Thiền Viện Trúc Lâm - Thiền & Ngắm cảnh",
            "description": "Tham quan Thiền Viện Trúc Lâm trên đồi Phượng Hoàng, chiêm bái và ngắm cảnh hồ Tuyền Lâm.",
            "time_slot": "afternoon",
            "category": "spiritual",
            "duration_hours": 2.0,
            "price": 0,
            "difficulty": "easy",
            "location": "Thiền Viện Trúc Lâm, Phường 3",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Miễn phí"],
        },
        {
            "name": "Cáp treo Đà Lạt - Ngắm thành phố",
            "description": "Ngắm toàn cảnh Đà Lạt từ trên cao với hệ thống cáp treo dài nhất Việt Nam.",
            "time_slot": "afternoon",
            "category": "adventure",
            "duration_hours": 1.5,
            "price": 200000,
            "difficulty": "easy",
            "location": "Ga cáp treo Robin Hill",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Vé cáp treo khứ hồi"],
        },
        # === EVENING ===
        {
            "name": "Chợ đêm Đà Lạt - Ẩm thực & Mua sắm",
            "description": "Khám phá chợ đêm sầm uất, thưởng thức đặc sản lẩu bò, bánh căn, sữa đậu nành và mua sắm đồ lưu niệm.",
            "time_slot": "evening",
            "category": "food",
            "duration_hours": 2.5,
            "price": 150000,
            "difficulty": "easy",
            "location": "Chợ đêm Đà Lạt, Phường 1",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Voucher ăn uống 100k"],
        },
        {
            "name": "Lẩu bò Ba Toa - Ẩm thực đặc sản",
            "description": "Thưởng thức lẩu bò ngon nhất Đà Lạt với thịt bò tươi, rau rừng và nước dùng đậm đà.",
            "time_slot": "evening",
            "category": "food",
            "duration_hours": 1.5,
            "price": 180000,
            "difficulty": "easy",
            "location": "Lẩu bò Ba Toa, Phường 3",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Suất lẩu bò", "Nước uống"],
        },
        {
            "name": "Cafe view đẹp - Trải nghiệm cà phê",
            "description": "Thưởng thức cà phê Đà Lạt tại quán cafe có view nhìn toàn thành phố, check-in sống ảo.",
            "time_slot": "evening",
            "category": "relax",
            "duration_hours": 1.5,
            "price": 60000,
            "difficulty": "easy",
            "location": "The Oberoi Cafe, Phường 10",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["1 ly cà phê"],
        },
    ],
    "Hội An": [
        # === MORNING ===
        {
            "name": "Phố cổ Hội An - Walking Tour",
            "description": "Khám phá phố cổ Hội An với kiến trúc cổ, nhà hội quán và chùa Cầu. Tìm hiểu lịch sử văn hóa hàng trăm năm.",
            "time_slot": "morning",
            "category": "culture",
            "duration_hours": 3.0,
            "price": 120000,
            "difficulty": "easy",
            "location": "Phố cổ Hội An",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Vé tham quan phố cổ", "Hướng dẫn viên"],
        },
        {
            "name": "Cù Lao Chàm - Lặn ngắm san hô",
            "description": "Khám phá đảo Cù Lao Chàm, lặn biển ngắm san hô và thưởng thức hải sản tươi.",
            "time_slot": "morning",
            "category": "adventure",
            "duration_hours": 5.0,
            "price": 450000,
            "difficulty": "moderate",
            "location": "Cù Lao Chàm, Hội An",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Tàu thuyền", "Dụng cụ lặn", "Bữa trưa hải sản", "Hướng dẫn viên"],
        },
        {
            "name": "Lớp nấu ăn - Nấu ăn Việt Nam",
            "description": "Học nấu các món Việt Nam từ đầu bếp bản địa. Đi chợ mua nguyên liệu và tự tay chế biến.",
            "time_slot": "morning",
            "category": "culture",
            "duration_hours": 4.0,
            "price": 350000,
            "difficulty": "easy",
            "location": "Green Tangerine Cooking School",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Nguyên liệu", "Apron", "Công thức nấu ăn", "Bữa ăn tự nấu"],
        },
        # === AFTERNOON ===
        {
            "name": "Thánh địa Mỹ Sơn - Di sản thế giới",
            "description": "Tham quan di sản văn hóa thế giới Mỹ Sơn, quần thể đền tháp Chăm Pa cổ đại.",
            "time_slot": "afternoon",
            "category": "culture",
            "duration_hours": 3.0,
            "price": 150000,
            "difficulty": "easy",
            "location": "Thánh địa Mỹ Sơn, Duy Xuyên",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Vé vào cổng", "Xe đưa đón", "Hướng dẫn"],
        },
        {
            "name": "Làng gốm Thanh Hà - Trải nghiệm",
            "description": "Trải nghiệm nặn gốm tại làng gộm Thanh Hà 500 năm tuổi. Tự tay tạo sản phẩm gốm mang về.",
            "time_slot": "afternoon",
            "category": "culture",
            "duration_hours": 2.0,
            "price": 80000,
            "difficulty": "easy",
            "location": "Làng gốm Thanh Hà",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Đất sét", "Hướng dẫn nặn gốm", "Sản phẩm mang về"],
        },
        {
            "name": "Cửa đại Beach - Tắm biển",
            "description": "Tận hưởng bãi biển Cửa Đại cát trắng, nước trong xanh. Tắm biển và ăn hải sản.",
            "time_slot": "afternoon",
            "category": "relax",
            "duration_hours": 3.0,
            "price": 50000,
            "difficulty": "easy",
            "location": "Bãi biển Cửa Đại",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Ghế nằm", "Ô dù"],
        },
        # === EVENING ===
        {
            "name": "Phố đèn lồng - Đạp thuyền sông Hoài",
            "description": "Ngắm phố cổ về đêm với hàng ngàn chiếc đèn lồng. Trải nghiệm đạp thuyền trên sông Hoài và thả hoa đăng.",
            "time_slot": "evening",
            "category": "culture",
            "duration_hours": 2.0,
            "price": 100000,
            "difficulty": "easy",
            "location": "Sông Hoài, Phố cổ",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample4.jpg",
            "included_services": ["Thuê thuyền", "Hoa đăng"],
        },
        {
            "name": "Chợ đêm Hội An - Ẩm thực",
            "description": "Thưởng thức đặc sản Hội An: Cao Lầu, Mì Quảng, Bánh Bao Bánh Vạc và chè bắp.",
            "time_slot": "evening",
            "category": "food",
            "duration_hours": 2.0,
            "price": 120000,
            "difficulty": "easy",
            "location": "Chợ đêm Nguyễn Hoàng",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Voucher ăn uống 80k"],
        },
    ],
    "Nha Trang": [
        # === MORNING ===
        {
            "name": "VinWonders - Công viên giải trí",
            "description": "Trải nghiệm hàng chục trò chơi cảm giác mạnh, công viên nước và thủy cung lớn nhất Đông Nam Á.",
            "time_slot": "morning",
            "category": "adventure",
            "duration_hours": 5.0,
            "price": 650000,
            "difficulty": "easy",
            "location": "Đảo Hòn Tre",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Vé vào cổng", "Cáp treo khứ hồi"],
        },
        {
            "name": "Lặn biển - Khám phá san hô",
            "description": "Lặn biển khám phá rạn san hô đầy màu sắc, bơi cùng cá nhiệt đới tại Hòn Mun.",
            "time_slot": "morning",
            "category": "adventure",
            "duration_hours": 4.0,
            "price": 500000,
            "difficulty": "moderate",
            "location": "Hòn Mun, Vịnh Nha Trang",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Tàu thuyền", "Dụng cụ lặn", "Hướng dẫn viên", "Bữa trưa"],
        },
        {
            "name": "Tháp Bà Ponagar - Di tích lịch sử",
            "description": "Tham quan quần thể tháp Chăm Pa cổ đại, tìm hiểu lịch sử và kiến trúc độc đáo.",
            "time_slot": "morning",
            "category": "culture",
            "duration_hours": 2.0,
            "price": 60000,
            "difficulty": "easy",
            "location": "Tháp Bà Ponagar",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Vé tham quan", "Hướng dẫn"],
        },
        # === AFTERNOON ===
        {
            "name": "Tắm bùn khoáng - Spa thiên nhiên",
            "description": "Trải nghiệm tắm bùn khoáng nóng tự nhiên, thư giãn và chăm sóc sức khỏe.",
            "time_slot": "afternoon",
            "category": "relax",
            "duration_hours": 3.0,
            "price": 300000,
            "difficulty": "easy",
            "location": "Tháp Bà Hot Spring",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Tắm bùn", "Tắm khoáng", "Khăn tắm"],
        },
        {
            "name": "Hòn Chồng - Ngắm cảnh",
            "description": "Khám phá danh thắng Hòn Chồng với ghềnh đá kỳ vĩ và view nhìn ra biển tuyệt đẹp.",
            "time_slot": "afternoon",
            "category": "nature",
            "duration_hours": 2.0,
            "price": 30000,
            "difficulty": "easy",
            "location": "Hòn Chồng, Nha Trang",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Vé vào cổng"],
        },
        # === EVENING ===
        {
            "name": "Chợ Đầm - Hải sản tươi sống",
            "description": "Thưởng thức hải sản tươi sống tại chợ hải sản lớn nhất Nha Trang. Tôm hùm, ghẹ, ốc đỏ...",
            "time_slot": "evening",
            "category": "food",
            "duration_hours": 2.0,
            "price": 200000,
            "difficulty": "easy",
            "location": "Chợ Đầm, Nha Trang",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Voucher hải sản 150k"],
        },
        {
            "name": "Nightlife - Bar & Club",
            "description": "Trải nghiệm cuộc sống về đêm tại các quán bar và club bên bờ biển Nha Trang.",
            "time_slot": "evening",
            "category": "relax",
            "duration_hours": 3.0,
            "price": 150000,
            "difficulty": "easy",
            "location": "Trần Phú, Nha Trang",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["1 ly cocktail welcome"],
        },
    ],
    "Sapa": [
        # === MORNING ===
        {
            "name": "Fansipan - Chinh phục đỉnh cao",
            "description": "Chinh phục 'Nóc nhà Đông Dương' bằng cáp treo hoặc trekking, ngắm biển mây tuyệt đẹp.",
            "time_slot": "morning",
            "category": "adventure",
            "duration_hours": 5.0,
            "price": 600000,
            "difficulty": "hard",
            "location": "Fansipan, Sapa",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Vé cáp treo khứ hồi", "Vé vào cổng"],
        },
        {
            "name": "Bản Cát Cát - Khám phá bản làng",
            "description": "Trekking đến bản Cát Cát, tìm hiểu đời sống người H'Mông, thác Cát Cát và nghề dệt nhuộm.",
            "time_slot": "morning",
            "category": "culture",
            "duration_hours": 3.5,
            "price": 80000,
            "difficulty": "moderate",
            "location": "Bản Cát Cát, Sapa",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Hướng dẫn bản địa", "Vé tham quan"],
        },
        {
            "name": "Ruộng bậc thang - Trekking",
            "description": "Trekking qua những thửa ruộng bậc thang tuyệt đẹp, chụp ảnh và ngắm cảnh núi rừng Tây Bắc.",
            "time_slot": "morning",
            "category": "nature",
            "duration_hours": 4.0,
            "price": 150000,
            "difficulty": "moderate",
            "location": "Mường Hoa, Sapa",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Hướng dẫn trekking", "Nước uống"],
        },
        # === AFTERNOON ===
        {
            "name": "Bản Tả Van - Trải nghiệm homestay",
            "description": "Ghé thăm bản Tả Van, trải nghiệm sinh hoạt cùng người dân tộc, thưởng thức đặc sản Tây Bắc.",
            "time_slot": "afternoon",
            "category": "culture",
            "duration_hours": 3.0,
            "price": 120000,
            "difficulty": "easy",
            "location": "Bản Tả Van, Sapa",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Hướng dẫn", "Thưởng trà đặc sản"],
        },
        {
            "name": "Núi Hàm Rồng - Vườn hoa & Đá",
            "description": "Leo núi Hàm Rồng, ngắm vườn hoa phong lan, sân mây và toàn cảnh thị trấn Sapa.",
            "time_slot": "afternoon",
            "category": "nature",
            "duration_hours": 2.5,
            "price": 100000,
            "difficulty": "moderate",
            "location": "Núi Hàm Rồng, Sapa",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Vé vào cổng"],
        },
        # === EVENING ===
        {
            "name": "Chợ tình Sapa - Ẩm thực & Văn hóa",
            "description": "Tham gia phiên chợ đêm, thưởng thức thắng cố, rượu táo mèo và mua đồ thổ cẩm.",
            "time_slot": "evening",
            "category": "food",
            "duration_hours": 2.0,
            "price": 100000,
            "difficulty": "easy",
            "location": "Thị trấn Sapa",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Suất ăn đặc sản"],
        },
    ],
    "Phú Quốc": [
        # === MORNING ===
        {
            "name": "Lặn ngắm san hô - Bãi sao",
            "description": "Lặn biển ngắm san hô tại vùng biển trong xanh nhất Phú Quốc, bơi cùng cá nhiệt đới.",
            "time_slot": "morning",
            "category": "adventure",
            "duration_hours": 4.0,
            "price": 450000,
            "difficulty": "moderate",
            "location": "Bãi Sao, Phú Quốc",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Tàu thuyền", "Dụng cụ lặn", "Bữa trưa", "Nước uống"],
        },
        {
            "name": "Vinpearl Safari - Động vật hoang dã",
            "description": "Khám phá sở thú bán hoang dã lớn nhất Việt Nam với hơn 3000 con vật.",
            "time_slot": "morning",
            "category": "nature",
            "duration_hours": 4.0,
            "price": 550000,
            "difficulty": "easy",
            "location": "Vinpearl Safari, Gành Dầu",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Vé vào cổng", "Xe buýt Safari"],
        },
        {
            "name": "Câu cá đêm - Trải nghiệm ngư dân",
            "description": "Ra khơi cùng ngư dân, học cách câu cá mực và thưởng thức hải sản tươi bắt ngay trên tàu.",
            "time_slot": "morning",
            "category": "adventure",
            "duration_hours": 4.0,
            "price": 400000,
            "difficulty": "moderate",
            "location": "Cảng Dương Đông",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Tàu thuyền", "Dụng cụ câu", "Nướng hải sản"],
        },
        # === AFTERNOON ===
        {
            "name": "Làng chài Hàm Ninh - Hải sản",
            "description": "Ghé thăm làng chài truyền thống, thưởng thức hải sản tươi và ngắm cảnh biển.",
            "time_slot": "afternoon",
            "category": "food",
            "duration_hours": 2.5,
            "price": 150000,
            "difficulty": "easy",
            "location": "Làng chài Hàm Ninh",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Voucher hải sản 100k"],
        },
        {
            "name": "Trải nghiệm sản xuất nước mắm",
            "description": "Tham quan nhà looming nước mắm truyền thống, tìm hiểu quy trình ủ chượp 200 năm.",
            "time_slot": "afternoon",
            "category": "culture",
            "duration_hours": 2.0,
            "price": 50000,
            "difficulty": "easy",
            "location": "Nhà đèn Phụ Quốc, Dương Đông",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Hướng dẫn tham quan", "Thử nếm nước mắm"],
        },
        {
            "name": "Bãi Sao - Tắm biển",
            "description": "Tận hưởng bãi biển đẹp nhất Phú Quốc với cát trắng mịn và nước biển trong xanh.",
            "time_slot": "afternoon",
            "category": "relax",
            "duration_hours": 3.0,
            "price": 30000,
            "difficulty": "easy",
            "location": "Bãi Sao, An Thới",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Ghế nằm", "Ô dù"],
        },
        # === EVENING ===
        {
            "name": "Chợ đêm Phú Quốc - Ẩm thực",
            "description": "Khám phá chợ đêm Dinh Cậu, thưởng thức bánh mì Phú Quốc, buffet hải sản và mua sắm.",
            "time_slot": "evening",
            "category": "food",
            "duration_hours": 2.0,
            "price": 150000,
            "difficulty": "easy",
            "location": "Chợ đêm Phú Quốc, Dương Đông",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["Voucher ăn uống 100k"],
        },
        {
            "name": "Ngắm hoàng hôn tại Sunset Sanato",
            "description": "Ngắm hoàng hôn tuyệt đẹp tại Sunset Sanato Beach Club với cocktail và nhạc acoustic.",
            "time_slot": "evening",
            "category": "relax",
            "duration_hours": 2.0,
            "price": 120000,
            "difficulty": "easy",
            "location": "Sunset Sanato, Ông Lang",
            "image_url": "https://res.cloudinary.com/demo/image/upload/v1312461204/sample.jpg",
            "included_services": ["1 ly cocktail welcome"],
        },
    ],
}


def seed_activities(conn):
    """Insert all activities using psycopg2."""
    total_inserted = 0
    total_skipped = 0
    cur = conn.cursor()
    all_activities = merge_activities()

    for destination, activities in all_activities.items():
        print(f"\nSeeding activities for {destination}...")

        # Check existing
        cur.execute(
            "SELECT name FROM activity_packages WHERE destination = %s AND is_ai_generated = FALSE",
            (destination,)
        )
        existing_names = {r[0] for r in cur.fetchall()}

        for activity in activities:
            if activity["name"] in existing_names:
                print(f"  SKIP (exists): {activity['name']}")
                total_skipped += 1
                continue

            cur.execute("""
                INSERT INTO activity_packages
                    (name, description, destination, time_slot, category,
                     duration_hours, price, difficulty, location, image_url,
                     gallery_urls, included_services, max_participants, min_participants,
                     is_active, is_ai_generated)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE, FALSE)
            """, (
                activity["name"],
                activity["description"],
                destination,
                activity["time_slot"],
                activity.get("category"),
                activity.get("duration_hours"),
                activity.get("price", 0),
                activity.get("difficulty", "easy"),
                activity.get("location"),
                activity.get("image_url"),
                activity.get("gallery_urls"),
                activity.get("included_services", []),
                activity.get("max_participants", 20),
                activity.get("min_participants", 1),
            ))

            print(f"  OK: {activity['name']} ({activity['time_slot']})")
            total_inserted += 1

    print(f"\n{'='*50}")
    print(f"Total inserted: {total_inserted}")
    print(f"Total skipped (already exists): {total_skipped}")

    # Summary
    print("\nSummary by destination:")
    for dest in sorted(all_activities.keys()):
        cur.execute(
            "SELECT COUNT(*) FROM activity_packages WHERE destination = %s AND is_active = TRUE",
            (dest,)
        )
        count = cur.fetchone()[0]
        print(f"  {dest}: {count} activities")

    cur.close()


if __name__ == "__main__":
    print("Seeding Activity Packages...")
    conn = get_connection()
    seed_activities(conn)
    conn.close()
    print("\nDone!")
