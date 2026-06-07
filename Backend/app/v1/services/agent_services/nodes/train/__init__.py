"""
Train Agent Node
Handles train search and booking via MCP tools
"""
from langchain_core.messages import AIMessage
import logging
from app.v1.services.agent_services.state import AgentState
from app.v1.services.agent_services.tools.mcp_tools import MCPClient

logger = logging.getLogger(__name__)


class TrainAgentNodes:
    """Node functions for Train Agent"""

    def __init__(self):
        self.mcp_client = MCPClient()

    async def train_node(self, state: AgentState) -> AgentState:
        """
        Train Agent node: searches trains and/or books based on params from Chat Agent.
        """
        logger.info("🚂 [Train Agent] Processing...")
        try:
            params = state.get("train_params", {})
            action = params.get("action", "search")

            if action == "search":
                result = await self._search_trains(params)
            elif action == "book":
                result = await self._book_train(params)
            else:
                result = await self._search_trains(params)

            train_msg = AIMessage(content=result)
            current_messages = state.get("messages", [])
            state["messages"] = current_messages + [train_msg]
            state["needs_train"] = False
            state["train_params"] = {}

            return state

        except Exception as e:
            logger.error(f"🚂 [Train Agent] Error: {str(e)}")
            error_msg = AIMessage(content=f"Xin lỗi, không thể xử lý yêu cầu vé tàu: {str(e)}")
            state["messages"] = state.get("messages", []) + [error_msg]
            state["needs_train"] = False
            return state

    async def _search_trains(self, params: dict) -> str:
        """Search trains via MCP"""
        departure = params.get("departure_city", "")
        arrival = params.get("arrival_city", "")
        date = params.get("date", "")

        if not departure or not arrival:
            stations = await self.mcp_client.call_tool("get_train_stations", {})
            return f"Vui lòng cung cấp ga đi và ga đến.\n\n{stations}"

        search_params = {
            "departure_station": departure.upper(),
            "arrival_station": arrival.upper(),
            "limit": 5
        }
        if date:
            search_params["date"] = date

        result = await self.mcp_client.call_tool("search_trains", search_params)
        return str(result) if result else "Không tìm thấy chuyến tàu phù hợp."

    async def _book_train(self, params: dict) -> str:
        """Book a train via MCP"""
        book_params = {
            "train_id": params.get("train_id", ""),
            "passenger_name": params.get("passenger_name", ""),
            "passenger_phone": params.get("passenger_phone", ""),
            "passenger_email": params.get("passenger_email", ""),
            "seat_type": params.get("seat_type", "soft_seat"),
            "num_passengers": params.get("num_passengers", 1)
        }

        if not book_params["train_id"] or not book_params["passenger_name"]:
            return "Thiếu thông tin đặt vé. Cần: train_id, tên hành khách, SĐT, email."

        result = await self.mcp_client.call_tool("book_train", book_params)
        return str(result) if result else "Đặt vé thất bại."
