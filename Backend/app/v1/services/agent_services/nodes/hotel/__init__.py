"""
Hotel Agent Node
Handles hotel search and booking via MCP tools
"""
from langchain_core.messages import AIMessage
import logging
from app.v1.services.agent_services.state import AgentState
from app.v1.services.agent_services.tools.mcp_tools import MCPClient

logger = logging.getLogger(__name__)


class HotelAgentNodes:
    """Node functions for Hotel Agent"""

    def __init__(self):
        self.mcp_client = MCPClient()

    async def hotel_node(self, state: AgentState) -> AgentState:
        """
        Hotel Agent node: searches hotels and/or books based on params from Chat Agent.
        """
        logger.info("🏨 [Hotel Agent] Processing...")
        try:
            params = state.get("hotel_params", {})
            action = params.get("action", "search")

            if action == "search":
                result = await self._search_hotels(params)
            elif action == "book":
                result = await self._book_hotel(params)
            else:
                result = await self._search_hotels(params)

            hotel_msg = AIMessage(content=result)
            current_messages = state.get("messages", [])
            state["messages"] = current_messages + [hotel_msg]
            state["needs_hotel"] = False
            state["hotel_params"] = {}

            return state

        except Exception as e:
            logger.error(f"🏨 [Hotel Agent] Error: {str(e)}")
            error_msg = AIMessage(content=f"Xin lỗi, không thể xử lý yêu cầu đặt phòng: {str(e)}")
            state["messages"] = state.get("messages", []) + [error_msg]
            state["needs_hotel"] = False
            return state

    async def _search_hotels(self, params: dict) -> str:
        """Search hotels via MCP"""
        location = params.get("location", "")
        min_price = params.get("min_price", 0) or 0
        max_price = params.get("max_price", 0) or 0

        if not location:
            locations = await self.mcp_client.call_tool("get_hotel_locations", {})
            return f"Vui lòng cung cấp địa điểm tìm khách sạn.\n\n{locations}"

        search_params = {
            "location": location,
            "min_price": float(min_price),
            "max_price": float(max_price),
            "limit": 5
        }

        result = await self.mcp_client.call_tool("search_hotels", search_params)
        return str(result) if result else "Không tìm thấy khách sạn phù hợp."

    async def _book_hotel(self, params: dict) -> str:
        """Book a hotel via MCP"""
        book_params = {
            "hotel_id": params.get("hotel_id", ""),
            "guest_name": params.get("guest_name", ""),
            "guest_phone": params.get("guest_phone", ""),
            "guest_email": params.get("guest_email", ""),
            "check_in": params.get("check_in", ""),
            "check_out": params.get("check_out", ""),
            "num_rooms": params.get("num_rooms", 1),
            "num_guests": params.get("num_guests", 1)
        }

        if not book_params["hotel_id"] or not book_params["guest_name"]:
            return "Thiếu thông tin đặt phòng. Cần: hotel_id, tên khách, SĐT, email, ngày nhận/trả phòng."

        result = await self.mcp_client.call_tool("book_hotel", book_params)
        return str(result) if result else "Đặt phòng thất bại."
