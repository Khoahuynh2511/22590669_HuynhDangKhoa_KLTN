"""
MCP Tools - Festival Tools
Lễ hội / sự kiện địa phương từ Wikidata SPARQL (open-source, key-free).
Cho phép AI agent gợi ý tour / lịch trình theo mùa lễ hội ("đi đúng dịp").
"""
from typing import Optional

from fastmcp import FastMCP

from app.v1.services.place_suggestion_service import PlaceSuggestionService


def register_festival_tools(mcp: FastMCP):
    """
    Register festival tools with FastMCP server.

    Args:
        mcp (FastMCP): FastMCP instance to register tools with.
    """
    festival_service = PlaceSuggestionService()

    @mcp.tool()
    async def get_local_festivals_by_province(
        province: str = "", month: Optional[int] = None, country: str = ""
    ) -> str:
        """
        Get festivals / events (worldwide), optionally filtered by country, province and/or month.

        Args:
            province: Tên tỉnh/thành (vd: Huế, Hà Nội, Kyoto). Bỏ trống để lấy cả nước.
            month: Tháng (1-12) để lọc lễ hội diễn ra trong tháng đó.
            country: Quốc gia — tên tiếng Việt/Anh (vd: "Nhật Bản", "Thailand") hoặc mã ISO2
                     (vd: "JP"). Bỏ trống = Việt Nam; "world" = toàn cầu.

        Returns:
            str: Danh sách lễ hội (tên, ngày, địa điểm) dạng văn bản.
        """
        try:
            result = await festival_service.get_local_festivals(
                province_name=province or None, month=month, country=country or None
            )
            if result.get("EC") != 0:
                return result.get("EM", "Không lấy được dữ liệu lễ hội.")
            fests = result.get("festivals") or []
            place = country.strip() or "Việt Nam"
            scope = place + (f", {province}" if province else "") + (f" tháng {month}" if month else "")
            if not fests:
                return f"Không tìm thấy lễ hội nào tại {scope}."
            lines = []
            for f in fests[:20]:
                date_str = f.get("start_date") or "?"
                loc = f.get("location") or ""
                tail = f" — {loc}" if loc else ""
                lines.append(f"- {f['name']} ({date_str}){tail}")
            return f"Tìm thấy {len(fests)} lễ hội tại {scope}:\n" + "\n".join(lines)
        except Exception as e:
            return f"Lỗi khi lấy dữ liệu lễ hội: {e}"
