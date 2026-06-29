r"""
Fetch ảnh phong cảnh cho tour_packages + activity_packages từ Wikimedia Commons
(open-source, key-free). Idempotent.

- Build cache {place: thumb_url} cho ~30 địa điểm VN tiêu biểu (search Commons).
- tour_packages: prepend ảnh Wikimedia vào image_urls (frontend lấy split('|')[0]).
- activity_packages: set image_url (thay placeholder Cloudinary).

Dùng:
    cd Backend
    python scripts/seed_place_images.py
    python scripts/seed_place_images.py --dry-run    # chỉ fetch + in cache, không update DB
"""
from __future__ import annotations
import argparse
import os
import re
import sys
import io
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

# (vi_name, [keywords để match trong destination/name tour — lowercase])
# vi_name dùng để search Wikimedia (có dấu → kết quả tốt hơn).
PLACES = [
    ("Đà Lạt", ["đà lạt", "da lat"]),
    ("Đà Nẵng", ["đà nẵng", "da nang"]),
    ("Hội An", ["hội an", "hoi an"]),
    ("Huế", ["huế", "hue "]),
    ("Hà Nội", ["hà nội", "ha noi"]),
    ("Thành phố Hồ Chí Minh", ["hồ chí minh", "sài gòn", "sai gon", "ho chi minh"]),
    ("Sa Pa", ["sapa", "sa pa", "fansipan"]),
    ("Vịnh Hạ Long", ["hạ long", "ha long"]),
    ("Nha Trang", ["nha trang"]),
    ("Phú Quốc", ["phú quốc", "phu quoc"]),
    ("Vũng Tàu", ["vũng tàu", "vung tau"]),
    ("Mũi Né", ["mũi né", "phan thiết", "mui ne", "phan thiet"]),
    ("Quy Nhơn", ["quy nhơn", "eo gió", "ky co", "quy nhon"]),
    ("Phú Yên", ["phú yên", "ghềnh đá dĩa", "phu yen"]),
    ("Cần Thơ", ["cần thơ", "chợ nổi", "can tho"]),
    ("Buôn Ma Thuột", ["buôn ma thuột", "dray nur", "buon ma thuot"]),
    ("Tây Ninh", ["tây ninh", "núi bà đen", "tay ninh"]),
    ("Hà Giang", ["hà giang", "đồng văn", "mã pí lèng", "lũng cú", "ha giang"]),
    ("Mù Cang Chải", ["mù cang chải", "mu cang chai"]),
    ("Mộc Châu", ["mộc châu", "moc chau"]),
    ("Điện Biên Phủ", ["điện biên", "dien bien"]),
    ("Côn Đảo", ["côn đảo", "con dao"]),
    ("Tràng An", ["tràng an", "ninh bình", "bái đính", "trang an", "ninh binh"]),
    ("Thác Bản Giốc", ["bản giốc", "cao bằng", "ban gioc"]),
    ("Cầu Vàng", ["cầu vàng", "bà nà", "son trà", "cau vang", "ba na"]),
    ("Chùa Thiên Mụ", ["chùa thiên mụ", "thien mu"]),
    ("Phong Nha Kẻ Bàng", ["phong nha", "thiên đường", "phong nha"]),
    ("Đồng bằng sông Cửu Long", ["bến tre", "mỹ tho", "vườn trái cây", "ben tre"]),
    ("Lạng Sơn", ["lạng sơn", "lang son"]),
    ("An Giang", ["an giang", "rừng tràm trà sư", "châu đốc", "núi cấm"]),
]


def strip_diacritics(s: str) -> str:
    return re.sub(r"[àáạảãâầấậẩẫăằắặẳẵ]", "a",
           re.sub(r"[èéẹẻẽêềếệểễ]", "e",
           re.sub(r"[ìíịỉĩ]", "i",
           re.sub(r"[òóọỏõôồốộổỗơờớợởỡ]", "o",
           re.sub(r"[ùúụủũưừứựửữ]", "u",
           re.sub(r"[ỳýỵỷỹ]", "y",
           re.sub(r"[đĐ]", "d", s))))))).lower()


def _wiki_pageimage(lang: str, title: str) -> str | None:
    """Lấy ảnh dẫn đầu của bài Wikipedia (thường là ảnh tiêu biểu của địa danh)."""
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
    """Ảnh cho địa danh: ưu tiên pageimage Wikipedia (đúng địa danh) -> fallback Commons search."""
    # 1) pageimage tiếng Việt, rồi tiếng Anh
    for lang, title in (("vi", place_vi), ("en", place_vi)):
        url = _wiki_pageimage(lang, title)
        if url:
            return url
    # 2) Commons search (ảnh phong cảnh)
    BAD = ("seal", "logo", "map", "coat_of_arms", "coat of arms", "location_of",
           "flag", "emblem", "symbol", ".svg", "herald", "blank", "icon", "sign")
    for query in (f"{place_vi} Vietnam", place_vi):
        try:
            r = httpx.get(COMMONS, params={
                "action": "query", "format": "json",
                "generator": "search", "gsrsearch": query,
                "gsrnamespace": 6, "gsrlimit": 15,
                "prop": "imageinfo", "iiprop": "url|mime", "iiurlwidth": 1000,
            }, headers={"User-Agent": UA}, timeout=20)
            pages = (r.json().get("query") or {}).get("pages") or {}
            candidates = []
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
                    score += 5  # tên file chứa tên địa danh -> rất ưu tiên
                score += sum(1 for kw in ("landscape", "view", "panoram", "beach",
                                          "temple", "mountain", "river", "pagoda",
                                          "bridge", "bay", "island") if kw in title)
                candidates.append((score, url))
            if candidates:
                candidates.sort(key=lambda x: -x[0])
                return candidates[0][1]
        except Exception:
            continue
    return None


def build_cache(verbose=True):
    cache = {}
    for vi, _kw in PLACES:
        url = fetch_image(vi)
        cache[vi] = url
        if verbose:
            print(f"  {vi:26s} -> {url[:75] + '...' if url and len(url) > 75 else (url or 'NO IMAGE')}")
    return cache


def match_place(text: str, cache: dict) -> str | None:
    """Find best matching place's image for a free-text destination."""
    if not text:
        return None
    low = text.lower()
    low_nd = strip_diacritics(low)
    for vi, _kw in PLACES:
        kws = [k for _v, ks in PLACES if _v == vi for k in ks]
        for kw in kws:
            if kw in low or strip_diacritics(kw) in low_nd:
                return cache.get(vi)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR: cần DATABASE_URL"); sys.exit(2)

    print("Fetching Wikimedia images for curated places...")
    cache = build_cache()
    found = sum(1 for v in cache.values() if v)
    print(f"  {found}/{len(cache)} places have images.\n")

    if args.dry_run:
        return

    conn = psycopg2.connect(dsn); conn.autocommit = True; cur = conn.cursor()

    # tour_packages: prepend wikimedia url
    cur.execute("SELECT package_id, destination, image_urls FROM tour_packages")
    rows = cur.fetchall()
    t_updated = 0
    for pid, dest, cur_imgs in rows:
        img = match_place(dest, cache)
        if not img:
            continue
        existing = (cur_imgs or "").strip()
        # idempotent: bỏ wikimedia url cũ nếu đã prepend
        parts = [p for p in existing.split("|") if p and p != img]
        new_val = img + ("|" + "|".join(parts) if parts else "")
        if new_val == existing:
            continue
        cur.execute("UPDATE tour_packages SET image_urls=%s WHERE package_id=%s", (new_val, pid))
        t_updated += 1
    print(f"tour_packages: updated {t_updated}/{len(rows)} rows.")

    # activity_packages: set image_url
    cur.execute("SELECT activity_id, destination, name FROM activity_packages")
    arows = cur.fetchall()
    a_updated = 0
    for aid, dest, name in arows:
        img = match_place(dest, cache) or match_place(name, cache)
        if not img:
            continue
        cur.execute("UPDATE activity_packages SET image_url=%s WHERE activity_id=%s", (img, aid))
        a_updated += 1
    print(f"activity_packages: updated {a_updated}/{len(arows)} rows.")
    conn.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
