r"""
Seed khách sạn toàn quốc 63 tỉnh (2 KS/tỉnh) + ảnh Wikimedia Commons + province_id.
- Đọc bảng `provinces` (63 dòng) -> mỗi tỉnh 2 KS (1 cao cấp + 1 tầm trung).
- Ảnh thật: tái dụng fetch_image() Wikimedia (key-free). Fallback nhiều tầng.
- Idempotent: skip KS đã tồn tại theo hotel_name; backfill province_id cho KS cũ.

Dùng:
    cd Backend
    uv run python scripts/seed_provincial_hotels.py --dry-run   # chỉ fetch ảnh + in, chưa ghi DB
    uv run python scripts/seed_provincial_hotels.py             # fetch ảnh + insert
    uv run python scripts/seed_provincial_hotels.py --no-images # bỏ fetch ảnh (dùng fallback), nhanh
"""
from __future__ import annotations
import argparse
import io
import os
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ENV = Path(__file__).resolve().parent.parent / ".env"
if ENV.exists():
    for line in ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

import httpx
import psycopg2

COMMONS = "https://commons.wikimedia.org/w/api.php"
UA = "KLTN-TourBooking/1.0 (educational; contact: uittraveling@example.com)"

# Fallback nhiều tầng nếu không fetch được ảnh tỉnh.
PLACEHOLDER = "img/hotel.jpeg"

# --------------------------- Wikimedia fetch (tái dụng seed_place_images) -----
def strip_diacritics(s: str) -> str:
    return re.sub(r"[àáạảãâầấậẩẫăằắặẳẵ]", "a",
           re.sub(r"[èéẹẻẽêềếệểễ]", "e",
           re.sub(r"[ìíịỉĩ]", "i",
           re.sub(r"[òóọỏõôồốộổỗơờớợởỡ]", "o",
           re.sub(r"[ùúụủũưừứựửữ]", "u",
           re.sub(r"[ỳýỵỷỹ]", "y",
           re.sub(r"[đĐ]", "d", s))))))).lower()


def _wiki_pageimage(lang: str, title: str) -> str | None:
    try:
        r = httpx.get(f"https://{lang}.wikipedia.org/w/api.php", params={
            "action": "query", "format": "json", "prop": "pageimages",
            "titles": title, "pithumbsize": 1000, "redirects": 1,
        }, headers={"User-Agent": UA}, timeout=20)
        pages = (r.json().get("query") or {}).get("pages") or {}
        for pg in pages.values():
            thumb = (pg.get("thumbnail") or {}).get("source")
            if thumb and "noimage" not in thumb and "placeholder" not in thumb:
                return thumb
    except Exception:
        pass
    return None


def fetch_image(place_vi: str) -> str | None:
    for lang, title in (("vi", place_vi), ("en", place_vi)):
        url = _wiki_pageimage(lang, title)
        if url:
            return url
    BAD = ("seal", "logo", "map", "coat_of_arms", "coat of arms", "location_of",
           "flag", "emblem", "symbol", ".svg", "herald", "blank", "icon", "sign")
    for query in (f"{place_vi} Vietnam", place_vi):
        try:
            r = httpx.get(COMMONS, params={
                "action": "query", "format": "json",
                "generator": "search", "gsrsearch": query,
                "gsrnamespace": 6, "gsrlimit": 12,
                "prop": "imageinfo", "iiprop": "url|mime", "iiurlwidth": 1000,
            }, headers={"User-Agent": UA}, timeout=20)
            pages = (r.json().get("query") or {}).get("pages") or {}
            cands = []
            place_nd = strip_diacritics(place_vi)
            for pg in pages.values():
                title = (pg.get("title") or "").lower()
                if any(b in title for b in BAD):
                    continue
                ii = (pg.get("imageinfo") or [{}])[0]
                mime = (ii.get("mime") or "").lower()
                if "svg" in mime or "gif" in mime or "pdf" in mime:
                    continue
                url = ii.get("thumburl") or ii.get("url")
                if not url:
                    continue
                score = 2 if ("jpeg" in mime or "jpg" in mime) else 0
                if place_nd and place_nd in strip_diacritics(title):
                    score += 5
                score += sum(1 for kw in ("landscape", "view", "panoram", "beach",
                                          "temple", "mountain", "river", "pagoda",
                                          "bridge", "bay", "island", "hotel") if kw in title)
                cands.append((score, url))
            if cands:
                cands.sort(key=lambda x: -x[0])
                return cands[0][1]
        except Exception:
            continue
    return None


# --------------------------- Dữ liệu sinh KS --------------------------------
# Tỉnh -> thành phố/địa danh tiêu biểu (dùng cho tên KS + search ảnh).
CITY_MAP = {
    "Hồ Chí Minh city": "Thành phố Hồ Chí Minh",
    "Thừa Thiên - Huế": "Huế",
    "Bà Rịa - Vũng Tàu": "Vũng Tàu",
    "Điện Biên": "Điện Biên Phủ",
    "Lâm Đồng": "Đà Lạt",
    "Khánh Hòa": "Nha Trang",
    "Quảng Nam": "Hội An",
    "Quảng Ninh": "Hạ Long",
    "Bình Thuận": "Phan Thiết",
    "Bình Định": "Quy Nhơn",
    "Phú Yên": "Tuy Hòa",
    "Nghệ An": "Vinh",
    "Gia Lai": "Pleiku",
    "Đắk Lắk": "Buôn Ma Thuột",
    "Đăk Nông": "Gia Nghĩa",
    "Phú Thọ": "Việt Trì",
    "Quảng Bình": "Đồng Hới",
    "Quảng Trị": "Đông Hà",
    "Bình Dương": "Thủ Dầu Một",
    "Đồng Nai": "Biên Hòa",
    "Long An": "Tân An",
    "Đồng Tháp": "Cao Lãnh",
    "An Giang": "Long Xuyên",
    "Kiên Giang": "Phú Quốc",
    "Hậu Giang": "Vị Thanh",
    "Tiền Giang": "Mỹ Tho",
    "Hà Nam": "Phủ Lý",
    "Hưng Yên": "Hưng Yên",
    "Lào Cai": "Sa Pa",
}

UPSCALE_BRANDS = [
    "Mường Thanh Luxury", "Vinpearl Resort & Spa", "Melia Hotels & Resorts",
    "InterContinental", "Sofitel", "Wyndham Grand", "Sheraton", "Lotus Boutique",
]
MID_TEMPLATES = [
    "{city} Central Hotel & Spa", "{city} Boutique Hotel",
    "Khách sạn {city} Plaza", "{city} Riverside Hotel",
]
STREETS = [
    "Đường Trần Hưng Đạo", "Đường Nguyễn Huệ", "Đường Lê Lợi", "Đường Phạm Văn Đồng",
    "Đường 30/4", "Quốc lộ 1A", "Đường Trần Phú", "Đường Hai Bà Trưng",
]
AMENITIES_POOL = [
    "Hồ bơi ngoài trời", "WiFi miễn phí", "Nhà hàng", "Spa & Massage", "Phòng gym",
    "Bãi đỗ xe miễn phí", "Đưa đón sân bay", "Bar/Lounge", "Dịch vụ phòng 24h",
    "Bữa sáng buffet", "Hồ bơi trong nhà", "Thuê xe máy/ô tô", "Trung tâm hội nghị",
    "Tủ lạnh & minibar", "Ban công view thành phố",
]
VIEWS = ["thành phố", "vịnh biển", "núi non", "sông hồ", "vườn nhiệt đới"]


def _pick(seq, i, salt=0):
    return seq[(i + salt) % len(seq)]


def _pick_subset(pool, n, i):
    """Chọn n phần tử deterministic từ pool theo index i (xoay vòng)."""
    n = min(n, len(pool))
    start = i % len(pool)
    out = []
    for k in range(n):
        out.append(pool[(start + k * 3) % len(pool)])  # bước 3 để rải đều
    return out


def gen_hotels(province: dict, i: int, images: list[str]) -> list[dict]:
    """Sinh 2 KS (cao cấp + tầm trung) cho 1 tỉnh."""
    pname = province["province_name"]
    city = CITY_MAP.get(pname, pname)
    region_vi = {"north": "miền Bắc", "central": "miền Trung", "south": "miền Nam"}.get(
        province.get("region"), "Việt Nam")

    upscale_name = f"{_pick(UPSCALE_BRANDS, i)} {city}"
    mid_name = _pick(MID_TEMPLATES, i + 1).format(city=city)

    star_u = round(4.5 + (i % 2) * 0.5, 1)             # 4.5 / 5.0
    star_m = round(3.0 + (i % 3) * 0.5, 1)             # 3.0 / 3.5 / 4.0
    score_u = round(8.6 + (i % 5) * 0.3, 1)
    score_m = round(7.4 + (i % 6) * 0.3, 1)

    price_u = 1_800_000 + (i * 41_000) % 2_700_000      # ~1.8tr–4.5tr
    price_m = 550_000 + (i * 23_000) % 650_000          # ~550k–1.2tr
    disc_u = 10 + (i % 4) * 5                            # 10–25
    disc_m = 5 + (i % 3) * 5                             # 5–15
    orig_u = round(price_u / (1 - disc_u / 100))
    orig_m = round(price_m / (1 - disc_m / 100))

    review_u = 180 + (i * 37) % 1200
    review_m = 90 + (i * 29) % 700
    rooms_u = 25 + (i % 5) * 10
    rooms_m = 40 + (i % 6) * 8

    view = _pick(VIEWS, i)
    street = _pick(STREETS, i)
    am_u = _pick_subset(AMENITIES_POOL, 7, i)
    am_m = _pick_subset(AMENITIES_POOL, 5, i + 2)

    desc_u = (f"Khách sạn {int(star_u)} sao cao cấp tọa lạc tại trung tâm {city}, {pname} ({region_vi}). "
              f"Thiết kế sang trọng, phòng nghỉ view {view}, hồ bơi vô cực, nhà hàng ẩm thực "
              f"đa dạng và spa chuyên nghiệp — điểm đến lý tưởng cho kỳ nghỉ đẳng cấp.")
    desc_m = (f"Khách sạn thân thiện gần trung tâm {city}, {pname}. Phòng ốc sạch sẽ, tiện nghi đầy đủ, "
              f"gần các điểm tham quan nổi bật, phù hợp cho cả du lịch công vụ và nghỉ dưỡng tiết kiệm.")

    img_str = "|".join(images) if images else PLACEHOLDER

    return [
        {
            "hotel_name": upscale_name, "location": pname, "province_id": province["province_id"],
            "description": desc_u, "address": f"{street}, {city}, {pname}",
            "star_rating": star_u, "review_score": score_u, "review_count": review_u,
            "price": price_u, "original_price": orig_u, "discount": disc_u,
            "amenities": am_u, "image_urls": img_str, "available_rooms": rooms_u, "is_active": True,
        },
        {
            "hotel_name": mid_name, "location": pname, "province_id": province["province_id"],
            "description": desc_m, "address": f"{_pick(STREETS, i+3)}, {city}, {pname}",
            "star_rating": star_m, "review_score": score_m, "review_count": review_m,
            "price": price_m, "original_price": orig_m, "discount": disc_m,
            "amenities": am_m, "image_urls": img_str, "available_rooms": rooms_m, "is_active": True,
        },
    ]


# --------------------------- Backfill KS cũ ----------------------------------
def backfill_province_id(cur) -> int:
    cur.execute("SELECT hotel_id, location FROM hotels WHERE province_id IS NULL")
    rows = cur.fetchall()
    if not rows:
        return 0
    cur.execute("SELECT province_id, province_name FROM provinces")
    provs = [(pid, strip_diacritics(pn), pn) for pid, pn in cur.fetchall()]
    updated = 0
    for hid, loc in rows:
        loc_nd = strip_diacritics(loc or "")
        match = None
        for pid, pn_nd, pn in provs:
            if pn_nd and (pn_nd in loc_nd or loc_nd in pn_nd) and len(pn_nd) >= 3:
                match = pid
                break
        if match:
            cur.execute("UPDATE hotels SET province_id=%s WHERE hotel_id=%s", (match, hid))
            updated += 1
    return updated


# --------------------------- Main --------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Chỉ fetch ảnh + in, KHÔNG ghi DB")
    ap.add_argument("--no-images", action="store_true", help="Bỏ fetch ảnh (dùng fallback)")
    ap.add_argument("--limit", type=int, default=0, help="Giới hạn số tỉnh (debug)")
    args = ap.parse_args()

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR: cần DATABASE_URL trong .env"); sys.exit(2)

    # Lấy fallback ảnh (khách sạn chung) 1 lần.
    fallback_imgs: list[str] = []
    if not args.no_images:
        fb = fetch_image("luxury hotel resort Vietnam")
        if fb:
            fallback_imgs = [fb]
        print(f"[fallback] {'OK' if fb else 'KHÔNG lấy được'} -> dùng '{PLACEHOLDER}' nếu tỉnh nào fail")

    conn = psycopg2.connect(dsn); conn.autocommit = True
    cur = conn.cursor()

    cur.execute("SELECT province_id, province_name, province_name_en, region, latitude, longitude "
                "FROM provinces ORDER BY province_name")
    provinces = [dict(zip(["province_id", "province_name", "province_name_en", "region",
                           "latitude", "longitude"], r)) for r in cur.fetchall()]
    if args.limit:
        provinces = provinces[:args.limit]
    print(f"\n[provinces] {len(provinces)} tỉnh sẽ seed (2 KS/tỉnh = {len(provinces)*2} KS)\n")

    inserted, skipped, img_ok, img_fail = 0, 0, 0, 0
    for i, prov in enumerate(provinces):
        city = CITY_MAP.get(prov["province_name"], prov["province_name"])
        images = []
        if not args.no_images:
            img = fetch_image(f"{city} Vietnam")
            if img:
                images = [img]
                img_ok += 1
            else:
                img_fail += 1
                images = list(fallback_imgs)  # fallback (có thể rỗng -> placeholder)
        hotels = gen_hotels(prov, i, images)

        if args.dry_run:
            flag = "img✓" if images else ("fallback" if fallback_imgs else "NO-IMG")
            print(f"  [{i+1:2d}/{len(provinces)}] {prov['province_name']:22s} ({city:18s}) "
                  f"{flag:9s} :: {hotels[0]['hotel_name']}  +  {hotels[1]['hotel_name']}")
            continue

        for h in hotels:
            cur.execute("SELECT 1 FROM hotels WHERE hotel_name=%s", (h["hotel_name"],))
            if cur.fetchone():
                skipped += 1
                continue
            cur.execute("""
                INSERT INTO hotels (hotel_name, location, description, address, star_rating,
                    review_score, review_count, price, original_price, discount, amenities,
                    image_urls, available_rooms, is_active, province_id)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (h["hotel_name"], h["location"], h["description"], h["address"], h["star_rating"],
                  h["review_score"], h["review_count"], h["price"], h["original_price"], h["discount"],
                  h["amenities"], h["image_urls"], h["available_rooms"], h["is_active"], h["province_id"]))
            inserted += 1

    if not args.dry_run:
        bf = backfill_province_id(cur)
        print(f"\n[backfill] province_id cho {bf} KS cũ (match location -> province_name).")

    conn.close()

    print("\n=== Tóm tắt ===")
    if args.dry_run:
        print(f"  DRY-RUN: ảnh tỉnh OK {img_ok}/{len(provinces)} (fail {img_fail}, fallback dùng cho fail).")
        print("  Không ghi DB. Chạy lại không có --dry-run để seed thật.")
    else:
        print(f"  Inserted: {inserted} KS | Skipped (đã tồn tại): {skipped}")
        if not args.no_images:
            print(f"  Ảnh tỉnh fetch OK: {img_ok}/{len(provinces)} (fail dùng fallback: {img_fail})")


if __name__ == "__main__":
    main()
