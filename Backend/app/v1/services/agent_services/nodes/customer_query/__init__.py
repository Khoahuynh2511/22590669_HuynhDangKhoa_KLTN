"""
Customer Query Agent (NLU front-door)
Phân loại ý định + rút slot từ tin nhắn; set các flag needs_* để supervisor route
đến specialist agent. Nếu ý định chung/thiếu slot/thấp confidence -> KHÔNG set flag
-> rơi về chat_llm (giữ nguyên behavior ReAct cũ).

Dùng LLM non-streaming + structured output để không leak token JSON ra frontend stream.
"""
import logging
from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.v1.schema.customer_query_schema import IntentClassification
from app.v1.services.agent_services.state import AgentState

logger = logging.getLogger(__name__)

NLU_SYSTEM_PROMPT = """Bạn là bộ phân loại ý định (NLU) cho trợ lý đặt tour/đặt phòng du lịch UITravel.
Phân tích tin nhắn người dùng và trả về JSON đúng schema (intent, confidence, slots, missing_slots).

Ánh xạ ý định:
- "vé máy bay / chuyến bay / flight" -> flight_search (slot bắt buộc: origin, destination)
- "vé tàu / tàu hỏa / train" -> train_search (slot bắt buộc: origin, destination)
- "vé xe / xe khách / bus / coach" -> bus_search (slot bắt buộc: origin, destination)
- "khách sạn / phòng / homestay / đặt phòng / hotel" -> hotel_search (slot bắt buộc: location)
- "gợi ý tour / đề xuất tour / tour nào hay" -> tour_recommendation
- "lập lịch / kế hoạch chuyến đi / itinerary" -> build_itinerary
- hỏi về booking/payment đang có -> booking | payment
- chào hỏi, hỏi thời tiết, hỏi thông tin chung, mơ hồ -> general

Quy tắc:
- Chỉ gán intent chuyên biệt khi rõ ràng. Nếu mơ hồ/nhiều ý -> general, confidence thấp.
- Rút slot chính xác từ văn bản (ngày dạng YYYY-MM-DD nếu có, số người, ngân sách VND).
- Nếu thiếu slot bắt buộc -> liệt kê trong missing_slots và GIẢM confidence (<0.5).
- Trả ĐÚNG JSON theo schema, không thêm chữ nào khác."""

MIN_CONFIDENCE = 0.5


class CustomerQueryAgentNodes:
    """Node NLU front-door — set flag needs_* để route, hoặc fallback chat_llm."""

    def __init__(self, llm):
        self.llm = llm
        self.nlu_llm = None
        try:
            if llm is not None and hasattr(llm, "with_structured_output"):
                self.nlu_llm = llm.with_structured_output(IntentClassification)
        except Exception as e:
            logger.warning(f"🧭 [CustomerQueryAgent] structured output unavailable, NLU disabled: {e}")
            self.nlu_llm = None

    async def customer_query_node(self, state: AgentState) -> AgentState:
        """Phân loại ý định -> set flag route; lỗi/mơ hồ -> fallback chat_llm."""
        # NLU không khả dụng -> fallback an toàn
        if self.nlu_llm is None:
            return state
        try:
            messages = state.get("messages", [])
            user_text = ""
            for m in reversed(messages):
                if isinstance(m, HumanMessage):
                    user_text = getattr(m, "content", "") or ""
                    break
            if not user_text:
                return state

            logger.info("🧭 [CustomerQueryAgent] Classifying intent...")
            result: IntentClassification = await self.nlu_llm.ainvoke(
                [SystemMessage(content=NLU_SYSTEM_PROMPT), HumanMessage(content=user_text)]
            )

            intent = (result.intent or "general").strip().lower()
            confidence = float(result.confidence or 0.0)

            # Quan sát: gom các slot đã rút trích (field tường minh) vào nlu_slots.
            slots = {
                k: getattr(result, k)
                for k in ("origin", "destination", "location", "departure_city", "arrival_city",
                          "start_date", "end_date", "adults", "budget", "min_price", "max_price",
                          "num_rooms", "num_guests")
                if getattr(result, k, None) is not None
            }
            state["intent"] = intent
            state["nlu_slots"] = slots
            state["nlu_missing_slots"] = result.missing_slots or []
            logger.info(
                f"🧭 [CustomerQueryAgent] intent={intent} conf={confidence:.2f} "
                f"slots={list(slots.keys())} missing={result.missing_slots}"
            )

            if confidence < MIN_CONFIDENCE:
                logger.info("🧭 [CustomerQueryAgent] Low confidence -> fallback chat_llm")
                return state

            def first(*keys) -> Optional[Any]:
                for k in keys:
                    v = getattr(result, k, None)
                    if v not in (None, "", []):
                        return v
                return None

            origin = first("origin", "departure_city")
            dest = first("destination", "arrival_city")
            date = first("start_date")

            if intent == "flight_search" and origin and dest:
                state["needs_flight"] = True
                state["flight_params"] = {"action": "search", "user_query": user_text,
                                          "departure_city": str(origin), "arrival_city": str(dest),
                                          "date": str(date) if date else ""}
            elif intent == "train_search" and origin and dest:
                state["needs_train"] = True
                state["train_params"] = {"action": "search", "user_query": user_text,
                                         "departure_city": str(origin), "arrival_city": str(dest),
                                         "date": str(date) if date else ""}
            elif intent == "bus_search" and origin and dest:
                state["needs_bus"] = True
                state["bus_params"] = {"action": "search", "user_query": user_text,
                                       "departure_city": str(origin), "arrival_city": str(dest),
                                       "date": str(date) if date else ""}
            elif intent == "hotel_search" and first("location", "destination"):
                loc = first("location", "destination")
                state["needs_hotel"] = True
                state["hotel_params"] = {
                    "action": "search", "user_query": user_text, "location": str(loc),
                    "min_price": first("min_price") or 0, "max_price": first("max_price") or 0,
                    "check_in": str(first("start_date", "check_in") or ""),
                    "check_out": str(first("end_date", "check_out") or ""),
                }
            elif intent == "tour_recommendation":
                state["needs_recommendation"] = True
                state["recommendation_params"] = {
                    "user_query": user_text,
                    "destination": first("destination", "location"),
                    "budget": first("budget"),
                }
            # build_itinerary / booking / payment / general -> fallback chat_llm
            return state

        except Exception as e:
            logger.warning(f"🧭 [CustomerQueryAgent] NLU error, fallback chat_llm: {e}")
            return state
