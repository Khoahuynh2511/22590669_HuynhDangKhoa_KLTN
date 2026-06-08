"""
Flight Agent Node
Handles flight search and booking via MCP tools
"""
from langchain_core.messages import AIMessage
import logging
from app.v1.services.agent_services.state import AgentState
from app.v1.services.agent_services.tools.mcp_tools import MCPClient

logger = logging.getLogger(__name__)


class FlightAgentNodes:
    """Node functions for Flight Agent"""

    def __init__(self):
        self.mcp_client = MCPClient()

    async def flight_node(self, state: AgentState) -> AgentState:
        """
        Flight Agent node: searches flights and/or books based on params from Chat Agent.
        """
        logger.info("✈️ [Flight Agent] Processing...")
        try:
            params = state.get("flight_params", {})
            action = params.get("action", "search")
            _user_query = params.get("user_query", "")  # noqa: F841

            if action == "search":
                result = await self._search_flights(params)
            elif action == "book":
                result = await self._book_flight(params)
            else:
                result = await self._search_flights(params)

            flight_msg = AIMessage(content=result)
            current_messages = state.get("messages", [])
            state["messages"] = current_messages + [flight_msg]
            state["needs_flight"] = False
            state["flight_params"] = {}

            return state

        except Exception as e:
            logger.error(f"✈️ [Flight Agent] Error: {str(e)}")
            error_msg = AIMessage(content=f"Xin lỗi, không thể xử lý yêu cầu vé máy bay: {str(e)}")
            state["messages"] = state.get("messages", []) + [error_msg]
            state["needs_flight"] = False
            return state

    async def _search_flights(self, params: dict) -> str:
        """Search flights via MCP"""
        departure = params.get("departure_city", "")
        arrival = params.get("arrival_city", "")
        date = params.get("date", "")

        if not departure or not arrival:
            airports = await self.mcp_client.call_tool("get_airports", {})
            return f"Vui lòng cung cấp sân bay đi và đến.\n\n{airports}"

        search_params = {
            "departure_iata": departure.upper(),
            "arrival_iata": arrival.upper(),
            "limit": 5
        }
        if date:
            search_params["date"] = date

        result = await self.mcp_client.call_tool("search_flights", search_params)
        return str(result) if result else "Không tìm thấy chuyến bay phù hợp."

    async def _book_flight(self, params: dict) -> str:
        """Book a flight via MCP"""
        book_params = {
            "flight_id": params.get("flight_id", ""),
            "passenger_name": params.get("passenger_name", ""),
            "passenger_phone": params.get("passenger_phone", ""),
            "passenger_email": params.get("passenger_email", ""),
            "seat_class": params.get("seat_class", "economy"),
            "num_passengers": params.get("num_passengers", 1)
        }

        if not book_params["flight_id"] or not book_params["passenger_name"]:
            return "Thiếu thông tin đặt vé. Cần: flight_id, tên hành khách, SĐT, email."

        result = await self.mcp_client.call_tool("book_flight", book_params)
        return str(result) if result else "Đặt vé thất bại."
