"""
Dataset + resolver cho các quốc gia phổ biến (du lịch).
- Ánh xạ tên (tiếng Việt/Anh) hoặc mã ISO2 -> {iso2, qid, vi, en}.
- `qid` là thực thể Wikidata (cho truy vấn SPARQL lễ hội theo nước).
- `iso2` là mã quốc gia 2 chữ cái (cho Nager.Date public holidays).
Dữ liệu mở (Wikidata CC0), không phụ thuộc bên thứ 3.
"""
import re
import unicodedata
from typing import Any, Dict, Optional

# Mỗi mục: iso2 (Nager.Date), qid (Wikidata SPARQL), tên tiếng Việt + tiếng Anh.
WORLD_COUNTRIES = [
    {"iso2": "VN", "qid": "Q881", "vi": "Việt Nam", "en": "Vietnam"},
    {"iso2": "TH", "qid": "Q869", "vi": "Thái Lan", "en": "Thailand"},
    {"iso2": "JP", "qid": "Q17", "vi": "Nhật Bản", "en": "Japan"},
    {"iso2": "KR", "qid": "Q884", "vi": "Hàn Quốc", "en": "South Korea"},
    {"iso2": "CN", "qid": "Q148", "vi": "Trung Quốc", "en": "China"},
    {"iso2": "SG", "qid": "Q334", "vi": "Singapore", "en": "Singapore"},
    {"iso2": "MY", "qid": "Q833", "vi": "Malaysia", "en": "Malaysia"},
    {"iso2": "ID", "qid": "Q252", "vi": "Indonesia", "en": "Indonesia"},
    {"iso2": "PH", "qid": "Q928", "vi": "Philippines", "en": "Philippines"},
    {"iso2": "KH", "qid": "Q424", "vi": "Campuchia", "en": "Cambodia"},
    {"iso2": "LA", "qid": "Q819", "vi": "Lào", "en": "Laos"},
    {"iso2": "MM", "qid": "Q836", "vi": "Myanmar", "en": "Myanmar"},
    {"iso2": "IN", "qid": "Q668", "vi": "Ấn Độ", "en": "India"},
    {"iso2": "US", "qid": "Q30", "vi": "Hoa Kỳ", "en": "United States"},
    {"iso2": "CA", "qid": "Q16", "vi": "Canada", "en": "Canada"},
    {"iso2": "GB", "qid": "Q145", "vi": "Vương quốc Anh", "en": "United Kingdom"},
    {"iso2": "FR", "qid": "Q142", "vi": "Pháp", "en": "France"},
    {"iso2": "DE", "qid": "Q183", "vi": "Đức", "en": "Germany"},
    {"iso2": "IT", "qid": "Q38", "vi": "Ý", "en": "Italy"},
    {"iso2": "ES", "qid": "Q29", "vi": "Tây Ban Nha", "en": "Spain"},
    {"iso2": "PT", "qid": "Q45", "vi": "Bồ Đào Nha", "en": "Portugal"},
    {"iso2": "NL", "qid": "Q29999", "vi": "Hà Lan", "en": "Netherlands"},
    {"iso2": "BE", "qid": "Q31", "vi": "Bỉ", "en": "Belgium"},
    {"iso2": "CH", "qid": "Q39", "vi": "Thụy Sĩ", "en": "Switzerland"},
    {"iso2": "AT", "qid": "Q40", "vi": "Áo", "en": "Austria"},
    {"iso2": "GR", "qid": "Q41", "vi": "Hy Lạp", "en": "Greece"},
    {"iso2": "CZ", "qid": "Q213", "vi": "Séc", "en": "Czechia"},
    {"iso2": "HU", "qid": "Q28", "vi": "Hungary", "en": "Hungary"},
    {"iso2": "RU", "qid": "Q159", "vi": "Nga", "en": "Russia"},
    {"iso2": "SE", "qid": "Q34", "vi": "Thụy Điển", "en": "Sweden"},
    {"iso2": "NO", "qid": "Q20", "vi": "Na Uy", "en": "Norway"},
    {"iso2": "DK", "qid": "Q35", "vi": "Đan Mạch", "en": "Denmark"},
    {"iso2": "FI", "qid": "Q33", "vi": "Phần Lan", "en": "Finland"},
    {"iso2": "IE", "qid": "Q27", "vi": "Ireland", "en": "Ireland"},
    {"iso2": "AU", "qid": "Q408", "vi": "Úc", "en": "Australia"},
    {"iso2": "NZ", "qid": "Q664", "vi": "New Zealand", "en": "New Zealand"},
    {"iso2": "BR", "qid": "Q155", "vi": "Brazil", "en": "Brazil"},
    {"iso2": "AR", "qid": "Q414", "vi": "Argentina", "en": "Argentina"},
    {"iso2": "MX", "qid": "Q96", "vi": "Mexico", "en": "Mexico"},
    {"iso2": "EG", "qid": "Q79", "vi": "Ai Cập", "en": "Egypt"},
    {"iso2": "ZA", "qid": "Q258", "vi": "Nam Phi", "en": "South Africa"},
    {"iso2": "TR", "qid": "Q43", "vi": "Thổ Nhĩ Kỳ", "en": "Turkey"},
    {"iso2": "AE", "qid": "Q878", "vi": "Ả Rập Xê Út", "en": "United Arab Emirates"},
    {"iso2": "SA", "qid": "Q851", "vi": "Saudi Arabia", "en": "Saudi Arabia"},
    {"iso2": "IL", "qid": "Q801", "vi": "Israel", "en": "Israel"},
    {"iso2": "MA", "qid": "Q1028", "vi": "Maroc", "en": "Morocco"},
]


def _strip(text: str) -> str:
    """Bỏ dấu tiếng Việt + lower (bản nội bộ để khớp tên nước linh hoạt)."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    s = "".join(c for c in nfkd if not unicodedata.combining(c))
    s = s.replace("đ", "d").replace("Đ", "d")
    return re.sub(r"\s+", " ", s).strip().lower()


# Lookup table đã chuẩn hoá sẵn để khớp nhanh.
_LOOKUP: Dict[str, Dict[str, Any]] = {}
for _c in WORLD_COUNTRIES:
    keys = {
        _c["iso2"].lower(),
        _c["vi"],
        _c["en"],
        _strip(_c["vi"]),
        _strip(_c["en"]),
    }
    for _k in keys:
        _LOOKUP[_k] = _c

# Từ khoá đặc biệt = chế độ "toàn thế giới".
_WORLD_ALIASES = {"", "world", "global", "all", "the gioi", "toan cau", "quoc te"}


def resolve_country(
    country: Optional[str] = None, country_code: Optional[str] = None
) -> Dict[str, Any]:
    """
    Giải mã đầu vào thành chế độ truy vấn lễ hội.

    Trả về:
      - {"mode": "vn"}                       -> Việt Nam (mặc định khi không truyền gì)
      - {"mode": "world"}                    -> toàn thế giới (bỏ filter quốc gia)
      - {"mode": "country", "iso2", "qid", "vi", "en"}  -> một nước cụ thể
      - {"mode": "unknown", "raw"}           -> không nhận diện được
    """
    code = (country_code or "").strip()
    name = (country or "").strip()

    # country_code ISO2 ưu tiên (Frontend có thể gửi thẳng mã).
    if code:
        hit = _LOOKUP.get(code.lower())
        if hit:
            return {"mode": "country", **hit}
        return {"mode": "unknown", "raw": code}

    if not name:
        return {"mode": "vn"}

    if _strip(name) in _WORLD_ALIASES or name.lower() in _WORLD_ALIASES:
        return {"mode": "world"}

    hit = _LOOKUP.get(name) or _LOOKUP.get(_strip(name))
    if hit:
        return {"mode": "country", **hit}

    # Nhận diện mã ISO2 gửi qua `country` (vd "JP", "th").
    if len(name) == 2 and name.isalpha():
        hit2 = _LOOKUP.get(name.lower())
        if hit2:
            return {"mode": "country", **hit2}

    return {"mode": "unknown", "raw": name}
