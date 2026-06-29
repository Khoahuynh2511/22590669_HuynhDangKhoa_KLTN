"""
Bus Agent Node
Handles bus search and booking via MCP tools
"""
from langchain_core.messages import AIMessage
import logging
from app.v1.services.agent_services.state import AgentState
from app.v1.services.agent_services.tools.mcp_tools import MCPClient

logger = logging.getLogger(__name__)


class BusAgentNodes:
    """Node functions for Bus Agent"""

    def __init__(self):
        self.mcp_client = MCPClient()

    async def bus_node(self, state: AgentState) -> AgentState:
        """
        Bus Agent node: searches buses and/or books based on params from Chat Agent.
        """
        logger.info("🚌 [Bus Agent] Processing...")
        try:
            params = state.get("bus_params", {})
            action = params.get("action", "search")

            if action == "search":
                result = await self._search_buses(params)
            elif action == "book":
                result = await self._book_bus(params)
            else:
                result = await self._search_buses(params)

            bus_msg = AIMessage(content=result)
            current_messages = state.get("messages", [])
            state["messages"] = current_messages + [bus_msg]
            state["needs_bus"] = False
            state["bus_params"] = {}

            return state

        except Exception as e:
            logger.error(f"🚌 [Bus Agent] Error: {str(e)}")
            error_msg = AIMessage(content=f"Xin lỗi, không thể xử lý yêu cầu vé xe: {str(e)}")
            state["messages"] = state.get("messages", []) + [error_msg]
            state["needs_bus"] = False
            return state

    async def _search_buses(self, params: dict) -> str:
        """Search buses via MCP"""
        departure = params.get("departure_city", "")
        arrival = params.get("arrival_city", "")
        date = params.get("date", "")

        if not departure or not arrival:
            stations = await self.mcp_client.call_tool("get_bus_stations", {})
            return f"Vui lòng cung cấp bến xe đi và đến.\n\n{stations}"

        search_params = {
            "departure_station": departure.upper(),
            "arrival_station": arrival.upper(),
            "limit": 5
        }
        if date:
            search_params["date"] = date

        result = await self.mcp_client.call_tool("search_buses", search_params)
        return str(result) if result else "Không tìm thấy chuyến xe phù hợp."

    async def _book_bus(self, params: dict) -> str:
        """Book a bus via MCP"""
        book_params = {
            "bus_id": params.get("bus_id", ""),
            "passenger_name": params.get("passenger_name", ""),
            "passenger_phone": params.get("passenger_phone", ""),
            "passenger_email": params.get("passenger_email", ""),
            "seat_type": params.get("seat_type", "standard"),
            "num_passengers": params.get("num_passengers", 1)
        }

        if not book_params["bus_id"] or not book_params["passenger_name"]:
            return "Thiếu thông tin đặt vé. Cần: bus_id, tên hành khách, SĐT, email."

        result = await self.mcp_client.call_tool("book_bus", book_params)
        return str(result) if result else "Đặt vé thất bại."
