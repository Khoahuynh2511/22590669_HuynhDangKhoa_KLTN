"""
Trip Planning Nodes
Node functions for the 6-step trip planning static workflow.

Each node:
1. Reads user message from state
2. Uses LLM to extract/understand information
3. Checks if required data is complete
4. If missing: asks user, sets waiting_for_input=True, loops back
5. If complete: advances to next step
"""
import json
import logging
import random
import re
from typing import Dict, Any, Optional

from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.v1.services.trip_planning.state.trip_plan_state import TripPlanState
from app.v1.services.agent_services.config import agent_config
from app.v1.services.agent_services.llm_providers import create_llm_provider
from app.v1.core.prompts import prompt_manager

logger = logging.getLogger(__name__)

# === Destination → Airport/Station mapping ===
DESTINATION_AIRPORTS = {
    "đà lạt": "DLI", "da lat": "DLI",
    "nha trang": "CXR", "nha trang": "CXR",
    "đà nẵng": "DAD", "da nang": "DAD",
    "phú quốc": "PQC", "phu quoc": "PQC",
    "sapa": "HAN", "sa pa": "HAN",  # Sapa → fly to Hanoi
    "hội an": "DAD", "hoi an": "DAD",  # Hoi An → fly to Da Nang
    "huế": "HUI", "hue": "HUI",
    "vũng tàu": "VCS", "vung tau": "VCS",
}

DESTINATION_STATIONS = {
    "đà lạt": "DLI", "da lat": "DLI",
    "nha trang": "NTR", "sapa": "SPC", "sa pa": "SPC",
    "đà nẵng": "DNA", "da nang": "DNA",
    "hội an": "DNA", "hoi an": "DNA",
    "huế": "HUE", "hue": "HUE",
    "sài gòn": "SGO", "sai gon": "SGO", "hcm": "SGO",
    "hà nội": "HNO", "ha noi": "HNO",
}

BUDGET_PRICE_MAP = {
    "economy": 150000,
    "moderate": 300000,
    "luxury": 600000,
}


def _get_step_prompt(step_name: str) -> str:
    """Get prompt for a specific step from agent.yaml."""
    try:
        return prompt_manager.get_prompt("trip_planning_agent", step_name)
    except (ValueError, KeyError):
        logger.warning(f"Prompt not found for step: {step_name}")
        return ""


def _extract_json_from_llm(text: str) -> Optional[Dict]:
    """Try to extract JSON from LLM response."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try to find JSON block
    patterns = [
        r'```json\s*(.*?)\s*```',
        r'```\s*(.*?)\s*```',
        r'(\{[^{}]*\})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
    return None


class TripPlanningNodes:
    """
    Node functions for the 6-step trip planning workflow.

    Each node method takes TripPlanState and returns updated TripPlanState.
    """

    def __init__(self):
        """Initialize with LLM."""
        try:
            provider = create_llm_provider()
            self.llm = provider.get_llm(
                model=agent_config.model,
                api_key=agent_config.api_key,
                temperature=0.3,
                streaming=True,
            )
            logger.info("✅ TripPlanningNodes LLM initialized")
        except Exception as e:
            logger.error(f"❌ Failed to init LLM for TripPlanningNodes: {e}")
            self.llm = None

    async def _ask_llm(self, system_prompt: str, user_message: str) -> str:
        """Call LLM with system + user message and return response text."""
        if not self.llm:
            return "Xin lỗi, hệ thống đang gặp sự cố. Vui lòng thử lại."

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message),
        ]
        response = await self.llm.ainvoke(messages)
        return response.content if hasattr(response, "content") else str(response)

    # ====================================================================
    # STEP 1: Basic Info (Destination + Duration)
    # ====================================================================
    async def step1_basic_info_node(self, state: TripPlanState) -> TripPlanState:
        """
        Extract destination and duration from user's message.
        Loop until both are provided.
        """
        logger.info("📍 [Step 1] Basic Info Node")
        current_step = state.get("current_step", 1)
        if current_step < 1:
            state["current_step"] = 1

        messages = state.get("messages", [])
        last_user_msg = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_user_msg = msg.content
                break

        # Check if data already exists from previous interaction
        existing_dest = state.get("destination")
        existing_duration = state.get("duration_days")

        if existing_dest and existing_duration:
            state["current_step"] = 2
            state["step_message"] = ""
            state["waiting_for_input"] = False
            logger.info(f"✅ [Step 1] Already complete: {existing_dest}, {existing_duration} days")
            return state

        # Use LLM to extract
        prompt = _get_step_prompt("step1_extract")
        if not prompt:
            prompt = """Bạn là trợ lý du lịch. Trích xuất thông tin từ tin nhắn người dùng.
Trả về CHỈ JSON, không giải thích:
{"destination": "tên địa điểm", "duration_days": số_ngày, "travel_date": "YYYY-MM-DD hoặc null"}
Nếu không có thông tin, để giá trị null."""

        try:
            llm_response = await self._ask_llm(prompt, last_user_msg)
            extracted = _extract_json_from_llm(llm_response)
            logger.info(f"🔍 [Step 1] Extracted: {extracted}")
        except Exception as e:
            logger.error(f"❌ [Step 1] LLM error: {e}")
            extracted = None

        if extracted:
            if extracted.get("destination") and not state.get("destination"):
                state["destination"] = extracted["destination"]
            if extracted.get("duration_days") and not state.get("duration_days"):
                state["duration_days"] = int(extracted["duration_days"])
            if extracted.get("travel_date") and not state.get("travel_date"):
                state["travel_date"] = extracted["travel_date"]

        # Check completeness
        dest = state.get("destination")
        dur = state.get("duration_days")

        if dest and dur:
            # Step complete
            state["current_step"] = 2
            state["step_message"] = f"Tuyệt! Bạn muốn đi **{dest}** trong **{dur} ngày**. 🎉"
            state["waiting_for_input"] = False
            # Add AI message
            ai_msg = AIMessage(content=state["step_message"])
            state["messages"] = messages + [ai_msg]
        else:
            # Need more info
            missing = []
            if not dest:
                missing.append("điểm đến (bạn muốn đi đâu?)")
            if not dur:
                missing.append("thời gian (đi mấy ngày?)")

            ask_msg = f"📅 Bạn cho mình thêm thông tin nhé: {' và '.join(missing)}"
            state["step_message"] = ask_msg
            state["waiting_for_input"] = True
            state["current_step"] = 1
            ai_msg = AIMessage(content=ask_msg)
            state["messages"] = messages + [ai_msg]

        return state

    # ====================================================================
    # STEP 2: Participants & Budget
    # ====================================================================
    async def step2_budget_people_node(self, state: TripPlanState) -> TripPlanState:
        """
        Extract group size, type, and budget level.
        Loop until all are provided.
        """
        logger.info("👥 [Step 2] Participants & Budget Node")
        state["current_step"] = 2

        messages = state.get("messages", [])
        last_user_msg = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_user_msg = msg.content
                break

        existing_size = state.get("group_size")
        existing_type = state.get("group_type")
        existing_budget = state.get("budget_level")

        if existing_size and existing_type and existing_budget:
            state["current_step"] = 3
            state["step_message"] = ""
            state["waiting_for_input"] = False
            return state

        prompt = _get_step_prompt("step2_extract")
        if not prompt:
            prompt = """Trích xuất thông tin từ tin nhắn người dùng.
Trả về CHỈ JSON:
{"group_size": số_người, "group_type": "solo|couple|family|friends", "budget_level": "economy|moderate|luxury"}
group_type: solo=1 người, couple=2 người yêu, family=gia đình, friends=bạn bè
budget_level: economy=tiết kiệm, moderate=trung bình, luxury=cao cấp
Nếu không có thông tin, để null."""

        try:
            llm_response = await self._ask_llm(prompt, last_user_msg)
            extracted = _extract_json_from_llm(llm_response)
            logger.info(f"🔍 [Step 2] Extracted: {extracted}")
        except Exception as e:
            logger.error(f"❌ [Step 2] LLM error: {e}")
            extracted = None

        if extracted:
            if extracted.get("group_size") and not state.get("group_size"):
                state["group_size"] = int(extracted["group_size"])
            if extracted.get("group_type") and not state.get("group_type"):
                state["group_type"] = extracted["group_type"]
            if extracted.get("budget_level") and not state.get("budget_level"):
                state["budget_level"] = extracted["budget_level"]
            # Infer type from size
            if state.get("group_size") and not state.get("group_type"):
                size = state["group_size"]
                if size == 1:
                    state["group_type"] = "solo"
                elif size == 2:
                    state["group_type"] = "couple"
                else:
                    state["group_type"] = "friends"

        size = state.get("group_size")
        gtype = state.get("group_type")
        budget = state.get("budget_level")

        if size and gtype and budget:
            type_vi = {"solo": "đi một mình", "couple": "cặp đôi", "family": "gia đình", "friends": "bạn bè"}
            budget_vi = {"economy": "tiết kiệm", "moderate": "trung bình", "luxury": "cao cấp"}
            msg = f"Got it! **{size} người** ({type_vi.get(gtype, gtype)}), ngân sách **{budget_vi.get(budget, budget)}**. 👍"
            state["step_message"] = msg
            state["waiting_for_input"] = False
            state["current_step"] = 3
            ai_msg = AIMessage(content=msg)
            state["messages"] = messages + [ai_msg]
        else:
            missing = []
            if not size:
                missing.append("số người đi")
            if not budget:
                missing.append("ngân sách (tiết kiệm/trung bình/cao cấp)")
            ask_msg = f"👥 Cho mình biết thêm: {' và '.join(missing)} nhé!"
            state["step_message"] = ask_msg
            state["waiting_for_input"] = True
            ai_msg = AIMessage(content=ask_msg)
            state["messages"] = messages + [ai_msg]

        return state

    # ====================================================================
    # STEP 3: Preferences (Optional - can skip)
    # ====================================================================
    async def step3_preferences_node(self, state: TripPlanState) -> TripPlanState:
        """
        Extract preferences. This step is optional - user can skip.
        Always advances to step 4 after processing.
        """
        logger.info("[Step 3] Preferences Node")
        state["current_step"] = 3

        messages = state.get("messages", [])

        # If preferences already set from a previous call, skip straight to step 4
        prefs = state.get("preferences")
        if prefs is not None and isinstance(prefs, list):
            state["current_step"] = 4
            state["waiting_for_input"] = False
            return state

        last_user_msg = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_user_msg = msg.content
                break

        # Check if user wants to skip or message doesn't contain preference keywords
        skip_keywords = ["không", "bỏ qua", "skip", "đi luôn", "tiếp", "ok", "oke", "được rồi", "không có"]
        pref_keywords = ["thích", "muốn", "thiên nhiên", "biển", "núi", "ẩm thực", "văn hóa", "phiêu lưu",
                         "thư giãn", "mua sắm", "tâm linh", "chụp ảnh", "trekking", "cafe", "spa"]
        has_pref = any(kw in last_user_msg.lower() for kw in pref_keywords)
        wants_skip = any(kw in last_user_msg.lower() for kw in skip_keywords)

        if wants_skip or not has_pref:
            # No preferences or user wants to skip
            state["preferences"] = []
            state["constraints"] = None
            msg = "Không sao! Mình sẽ gợi ý những hoạt động phổ biến nhất. Đang tìm kiếm..."
            state["step_message"] = msg
            state["waiting_for_input"] = False
            state["current_step"] = 4  # Advance immediately
            ai_msg = AIMessage(content=msg)
            state["messages"] = messages + [ai_msg]
            return state

        # Extract preferences from user message using LLM
        prompt = _get_step_prompt("step3_extract")
        if not prompt:
            prompt = """Trích xuất sở thích du lịch từ tin nhắn người dùng.
Trả về CHỈ JSON:
{"preferences": ["nature", "food", ...], "constraints": "yêu cầu đặc biệt hoặc null}
Categories: nature, food, culture, adventure, relax, shopping, spiritual, photography
Nếu người dùng không nêu, trả về danh sách rỗng."""

        try:
            llm_response = await self._ask_llm(prompt, last_user_msg)
            extracted = _extract_json_from_llm(llm_response)
        except Exception:
            extracted = None

        if extracted and extracted.get("preferences"):
            state["preferences"] = extracted["preferences"]
            state["constraints"] = extracted.get("constraints")
            prefs_vi = ", ".join(extracted["preferences"])
            msg = f"Tuyệt! Sở thích: **{prefs_vi}**. Mình sẽ tìm các hoạt động phù hợp!"
        else:
            state["preferences"] = []
            state["constraints"] = None
            msg = "OK! Mình sẽ gợi ý những hoạt động phổ biến nhất."

        state["step_message"] = msg
        state["waiting_for_input"] = False
        state["current_step"] = 4  # Always advance
        ai_msg = AIMessage(content=msg)
        state["messages"] = messages + [ai_msg]

        return state

    # ====================================================================
    # STEP 4: Plan Generation (Modular Itinerary Builder)
    # ====================================================================
    async def step4_plan_generation_node(self, state: TripPlanState) -> TripPlanState:
        """
        The core node: Build a modular itinerary from activity packages.

        1. Fetch activities from DB for the destination
        2. If not enough, optionally generate via AI
        3. Rank by preferences and budget
        4. Build suggested itinerary
        5. Present to user for confirmation or customization
        """
        logger.info("🗺️ [Step 4] Plan Generation Node")
        state["current_step"] = 4

        messages = state.get("messages", [])
        destination = state.get("destination", "")
        duration_days = state.get("duration_days", 2)
        budget_level = state.get("budget_level", "moderate")
        preferences = state.get("preferences", [])

        # --- If itinerary already confirmed, advance to step 5 ---
        if state.get("confirmed_itinerary"):
            state["current_step"] = 5
            state["waiting_for_input"] = False
            return state

        # --- If we already have suggested itinerary, check user response ---
        if state.get("suggested_itinerary"):
            last_user_msg = ""
            for msg in reversed(messages):
                if isinstance(msg, HumanMessage):
                    last_user_msg = msg.content
                    break

            confirm_kw = ["xác nhận", "ok", "đồng ý", "chấp nhận", "oke", "tiếp", "thanh toán", "được"]
            customize_kw = ["thay đổi", "sửa", "đổi", "khác", "customize", "chỉnh"]

            if any(kw in last_user_msg.lower() for kw in confirm_kw):
                # User confirmed the itinerary
                state["confirmed_itinerary"] = state.get("suggested_itinerary", {})
                state["itinerary_total_price"] = state.get("itinerary_total_price", 0)
                msg = "✅ Lịch trình đã được xác nhận! Tiếp theo mình sẽ tìm phương tiện di chuyển."
                state["step_message"] = msg
                state["current_step"] = 5
                state["waiting_for_input"] = False
                ai_msg = AIMessage(content=msg)
                state["messages"] = messages + [ai_msg]
                return state
            elif any(kw in last_user_msg.lower() for kw in customize_kw):
                msg = "🔨 Bạn muốn thay đổi hoạt động nào? (Ví dụ: đổi buổi sáng ngày 1)"
                state["step_message"] = msg
                state["waiting_for_input"] = True
                ai_msg = AIMessage(content=msg)
                state["messages"] = messages + [ai_msg]
                return state
            else:
                # Try to interpret as confirmation
                state["confirmed_itinerary"] = state.get("suggested_itinerary", {})
                state["itinerary_total_price"] = state.get("itinerary_total_price", 0)
                msg = "✅ Đã ghi nhận! Tiếp tục tìm phương tiện di chuyển."
                state["step_message"] = msg
                state["current_step"] = 5
                state["waiting_for_input"] = False
                ai_msg = AIMessage(content=msg)
                state["messages"] = messages + [ai_msg]
                return state

        # --- FIRST TIME: Fetch activities and build itinerary ---
        activities = await self._fetch_activities(destination, preferences, budget_level)
        state["available_activities"] = activities

        if not activities:
            msg = (
                f"😔 Hiện chưa có hoạt động nào cho **{destination}** trong hệ thống. "
                "Mình đang bổ sung thêm. Bạn có thể thử điểm đến khác hoặc quay lại sau nhé!"
            )
            state["step_message"] = msg
            state["waiting_for_input"] = True
            ai_msg = AIMessage(content=msg)
            state["messages"] = messages + [ai_msg]
            return state

        # Build suggested itinerary
        itinerary = self._build_suggested_itinerary(activities, duration_days)
        total_price = self._calculate_itinerary_price(itinerary, state.get("group_size", 1))

        state["suggested_itinerary"] = itinerary
        state["itinerary_total_price"] = total_price

        # Generate human-readable message
        msg = self._format_itinerary_message(itinerary, destination, duration_days, total_price)
        state["step_message"] = msg
        state["waiting_for_input"] = True
        ai_msg = AIMessage(content=msg)
        state["messages"] = messages + [ai_msg]

        return state

    async def _fetch_activities(
        self, destination: str, preferences: list, budget_level: str
    ) -> list:
        """Fetch activity packages from Render PostgreSQL (psycopg2)."""
        try:
            from app.v1.services.trip_planning.activity_service import activity_service
            activities = activity_service.get_all_for_destination(
                destination=destination,
                budget_level=budget_level,
                preferences=preferences,
            )
            logger.info(f"Fetched {len(activities)} activities for '{destination}'")
            return activities
        except Exception as e:
            logger.error(f"Error fetching activities: {e}")
            return []

    def _build_suggested_itinerary(
        self, activities: list, duration_days: int
    ) -> Dict[str, Dict[str, Any]]:
        """
        Build a suggested itinerary by filling slots with available activities.
        Tries to avoid repeating the same activity across days.
        """
        itinerary = {}

        # Group activities by time_slot
        by_slot = {"morning": [], "afternoon": [], "evening": []}
        for act in activities:
            slot = act.get("time_slot", "morning")
            if slot in by_slot:
                by_slot[slot].append(act)
            elif slot == "full_day":
                # Full-day activities can go to any slot
                for s in by_slot:
                    by_slot[s].append(act)

        for day in range(1, duration_days + 1):
            day_key = f"day_{day}"
            itinerary[day_key] = {}

            for slot_name, slot_activities in by_slot.items():
                if slot_activities:
                    # Pick a different activity for each day (cycle through)
                    idx = (day - 1) % len(slot_activities)
                    activity = slot_activities[idx]
                    itinerary[day_key][slot_name] = {
                        "activity_id": activity.get("activity_id"),
                        "name": activity.get("name"),
                        "description": activity.get("description"),
                        "price": float(activity.get("price", 0) or 0),
                        "duration_hours": activity.get("duration_hours"),
                        "category": activity.get("category"),
                        "time_slot": slot_name,
                        "location": activity.get("location"),
                        "image_url": activity.get("image_url"),
                        "difficulty": activity.get("difficulty"),
                        "included_services": activity.get("included_services"),
                    }
                else:
                    itinerary[day_key][slot_name] = None

        return itinerary

    def _calculate_itinerary_price(self, itinerary: dict, group_size: int) -> float:
        """Calculate total price for the itinerary."""
        total = 0.0
        for day_key, slots in itinerary.items():
            for slot_name, activity in slots.items():
                if activity and isinstance(activity, dict):
                    price = float(activity.get("price", 0) or 0)
                    total += price * group_size
        return total

    def _format_itinerary_message(
        self, itinerary: dict, destination: str, duration_days: int, total_price: float
    ) -> str:
        """Format itinerary as a readable markdown message."""
        slot_vi = {"morning": "🌅 Sáng", "afternoon": "☀️ Trưa", "evening": "🌙 Chiều"}

        lines = [
            f"🗺️ **Lịch trình gợi ý cho {destination} ({duration_days} ngày)**\n"
        ]

        for day_key, slots in itinerary.items():
            day_num = day_key.replace("day_", "")
            lines.append(f"**📅 Ngày {day_num}:**")
            for slot in ["morning", "afternoon", "evening"]:
                activity = slots.get(slot)
                if activity and isinstance(activity, dict):
                    price_str = f"{activity.get('price', 0):,.0f}đ" if activity.get("price") else "Miễn phí"
                    lines.append(f"  {slot_vi.get(slot, slot)}: **{activity.get('name', 'Chưa chọn')}** ({price_str})")
                else:
                    lines.append(f"  {slot_vi.get(slot, slot)}: _Chưa chọn_")
            lines.append("")

        price_fmt = f"{total_price:,.0f}đ"
        lines.append(f"💰 **Tổng chi tiết ({duration_days} ngày): {price_fmt}**\n")
        lines.append("_(Gõ **'xác nhận'** để tiếp tục, hoặc **'thay đổi'** để chỉnh sửa)_")

        return "\n".join(lines)

    # ====================================================================
    # STEP 5: Transportation
    # ====================================================================
    async def step5_transportation_node(self, state: TripPlanState) -> TripPlanState:
        """
        Search for flights and trains based on destination + date.
        User can select or skip.
        """
        logger.info("✈️ [Step 5] Transportation Node")
        state["current_step"] = 5

        messages = state.get("messages", [])
        destination = state.get("destination", "")
        travel_date = state.get("travel_date")
        last_user_msg = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_user_msg = msg.content
                break

        # --- Already has selections, advance ---
        if state.get("selected_flight") or state.get("selected_train") or \
           state.get("needs_flight") is False and state.get("needs_train") is False:
            state["current_step"] = 6
            state["waiting_for_input"] = False
            return state

        # --- Check if user wants to skip ---
        skip_kw = ["không", "bỏ qua", "skip", "đi luôn", "tiếp", "tự lo"]
        if any(kw in last_user_msg.lower() for kw in skip_kw):
            state["needs_flight"] = False
            state["needs_train"] = False
            state["flight_search_results"] = []
            state["train_search_results"] = []
            msg = "👌 Bạn sẽ tự sắp xếp di chuyển. Tiến hành chốt đơn nhé!"
            state["step_message"] = msg
            state["current_step"] = 6
            state["waiting_for_input"] = False
            ai_msg = AIMessage(content=msg)
            state["messages"] = messages + [ai_msg]
            return state

        # --- First time: ask and search ---
        if not state.get("flight_search_results") and not state.get("train_search_results"):
            flights = []
            trains = []

            # Search flights
            dest_lower = destination.lower().strip()
            arrival_airport = DESTINATION_AIRPORTS.get(dest_lower, "")
            if arrival_airport:
                try:
                    from app.v1.services.flight_search_service import FlightSearchService
                    flight_svc = FlightSearchService()
                    result = flight_svc.search_flights(
                        departure="SGN",  # Default from HCMC
                        arrival=arrival_airport,
                        date=travel_date,
                        limit=3
                    )
                    if result.get("EC") == 0 and result.get("data"):
                        flights = result["data"].get("flights", [])
                        if isinstance(flights, list):
                            state["flight_search_results"] = flights[:3]
                except Exception as e:
                    logger.error(f"❌ Flight search error: {e}")

            # Search trains
            arrival_station = DESTINATION_STATIONS.get(dest_lower, "")
            if arrival_station:
                try:
                    from app.v1.services.train_search_service import TrainSearchService
                    train_svc = TrainSearchService()
                    result = train_svc.search_trains(
                        departure="SGO",  # Default from HCMC
                        arrival=arrival_station,
                        date=travel_date,
                        limit=3
                    )
                    if result.get("EC") == 0 and result.get("data"):
                        trains = result["data"].get("trains", [])
                        if isinstance(trains, list):
                            state["train_search_results"] = trains[:3]
                except Exception as e:
                    logger.error(f"❌ Train search error: {e}")

            flights = state.get("flight_search_results", [])
            trains = state.get("train_search_results", [])

            if flights or trains:
                lines = ["✈️ **Phương tiện di chuyển đến {}:**\n".format(destination)]
                if flights:
                    lines.append("**✈️ Chuyến bay:**")
                    for i, f in enumerate(flights[:3], 1):
                        lines.append(f"  {i}. {f.get('airline', '')} {f.get('flight_number', '')} - "
                                     f"{f.get('departure_time', '')} → {f.get('arrival_time', '')} - "
                                     f"{f.get('price', 0):,.0f}đ")
                    lines.append("")
                if trains:
                    lines.append("**🚂 Tàu hỏa:**")
                    for i, t in enumerate(trains[:3], 1):
                        lines.append(f"  {i}. {t.get('train_name', '')} - "
                                     f"{t.get('departure_time', '')} → {t.get('arrival_time', '')} - "
                                     f"{t.get('price', 0):,.0f}đ")
                    lines.append("")

                lines.append("_(Gõ số thứ tự để chọn, hoặc **'bỏ qua'** nếu tự sắp xếp)_")
                msg = "\n".join(lines)
            else:
                msg = ("Không tìm thấy chuyến bay/tàu phù hợp. "
                       "_(Gõ **'bỏ qua'** để tiếp tục)_")
                state["needs_flight"] = False
                state["needs_train"] = False

            state["step_message"] = msg
            state["waiting_for_input"] = True
            ai_msg = AIMessage(content=msg)
            state["messages"] = messages + [ai_msg]
            return state

        # --- User responded with selection ---
        # Parse selection
        flights = state.get("flight_search_results", [])
        trains = state.get("train_search_results", [])

        try:
            num = int(re.search(r'\d+', last_user_msg).group())
            if 1 <= num <= len(flights):
                state["selected_flight"] = flights[num - 1]
                state["needs_flight"] = True
                msg = f"✅ Đã chọn chuyến bay: {flights[num-1].get('airline', '')} {flights[num-1].get('flight_number', '')}"
            elif len(flights) < num <= len(flights) + len(trains):
                idx = num - len(flights) - 1
                state["selected_train"] = trains[idx]
                state["needs_train"] = True
                msg = f"✅ Đã chọn tàu: {trains[idx].get('train_name', '')}"
            else:
                msg = "Số thứ tự không hợp lệ. Vui lòng chọn lại hoặc gõ 'bỏ qua'."
                state["step_message"] = msg
                state["waiting_for_input"] = True
                ai_msg = AIMessage(content=msg)
                state["messages"] = messages + [ai_msg]
                return state
        except (AttributeError, ValueError):
            msg = "Không hiểu lựa chọn. Vui lòng gõ số thứ tự hoặc 'bỏ qua'."
            state["step_message"] = msg
            state["waiting_for_input"] = True
            ai_msg = AIMessage(content=msg)
            state["messages"] = messages + [ai_msg]
            return state

        state["current_step"] = 6
        state["step_message"] = msg
        state["waiting_for_input"] = False
        ai_msg = AIMessage(content=msg)
        state["messages"] = messages + [ai_msg]
        return state

    # ====================================================================
    # STEP 6: Checkout
    # ====================================================================
    async def step6_checkout_node(self, state: TripPlanState) -> TripPlanState:
        """
        Save custom itinerary, create booking, generate payment.
        """
        logger.info("💳 [Step 6] Checkout Node")
        state["current_step"] = 6

        messages = state.get("messages", [])
        last_user_msg = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_user_msg = msg.content
                break

        # If already completed
        if state.get("booking_completed"):
            state["is_complete"] = True
            return state

        # Check if user confirms checkout
        confirm_kw = ["thanh toán", "pay", "xác nhận", "ok", "oke", "đồng ý", "chốt"]
        if not any(kw in last_user_msg.lower() for kw in confirm_kw):
            # Show summary and ask for confirmation
            itinerary = state.get("confirmed_itinerary", state.get("suggested_itinerary", {}))
            total_price = state.get("itinerary_total_price", 0)
            dest = state.get("destination", "")
            days = state.get("duration_days", 0)
            size = state.get("group_size", 1)

            transport_extra = 0
            if state.get("selected_flight"):
                transport_extra += state["selected_flight"].get("price", 0) * size
            if state.get("selected_train"):
                transport_extra += state["selected_train"].get("price", 0) * size

            grand_total = total_price + transport_extra

            lines = [
                f"📋 **Tóm tắt đơn hàng:**\n",
                f"- 📍 Điểm đến: **{dest}** ({days} ngày)",
                f"- 👥 Số người: **{size}**",
            ]
            if state.get("selected_flight"):
                lines.append(f"- ✈️ Chuyến bay: {state['selected_flight'].get('airline', '')}")
            if state.get("selected_train"):
                lines.append(f"- 🚂 Tàu: {state['selected_train'].get('train_name', '')}")
            lines.append(f"\n💰 **Tổng thanh toán: {grand_total:,.0f}đ**")
            lines.append(f"  (Hoạt động: {total_price:,.0f}đ + Di chuyển: {transport_extra:,.0f}đ)\n")
            lines.append("_(Gõ **'thanh toán'** để tiếp tục)_")

            msg = "\n".join(lines)
            state["step_message"] = msg
            state["waiting_for_input"] = True
            ai_msg = AIMessage(content=msg)
            state["messages"] = messages + [ai_msg]
            return state

        # --- Process checkout ---
        try:
            import psycopg2
            import os
            from dotenv import load_dotenv
            load_dotenv()

            db_url = os.getenv("DATABASE_URL")
            conn = psycopg2.connect(db_url)
            conn.autocommit = True
            cur = conn.cursor()

            itinerary = state.get("confirmed_itinerary", state.get("suggested_itinerary", {}))
            # Convert itinerary to JSON-safe format
            itinerary_data = {}
            for day_key, slots in itinerary.items():
                itinerary_data[day_key] = {}
                for slot, activity in slots.items():
                    if activity and isinstance(activity, dict):
                        itinerary_data[day_key][slot] = activity.get("activity_id") or activity.get("name")
                    else:
                        itinerary_data[day_key][slot] = None

            import json
            cur.execute("""
                INSERT INTO custom_trip_plans
                    (user_id, destination, travel_date, duration_days, group_size,
                     group_type, budget_level, itinerary, total_price, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING plan_id
            """, (
                state.get("user_id"),
                state.get("destination"),
                state.get("travel_date"),
                state.get("duration_days"),
                state.get("group_size", 1),
                state.get("group_type"),
                state.get("budget_level"),
                json.dumps(itinerary_data, ensure_ascii=False),
                state.get("itinerary_total_price", 0),
                "confirmed",
            ))
            plan_id = cur.fetchone()[0]
            state["custom_plan_id"] = str(plan_id)

            cur.close()
            conn.close()

            msg = (
                f"🎉 **Đặt lịch thành công!**\n\n"
                f"📋 Mã kế hoạch: `{plan_id}`\n"
                f"📍 {state.get('destination')} - {state.get('duration_days')} ngày\n"
                f"💰 Tổng: {state.get('itinerary_total_price', 0):,.0f}đ\n\n"
                f"Cảm ơn bạn đã sử dụng dịch vụ! Chúc bạn có chuyến đi tuyệt vời! 🌟"
            )
            state["step_message"] = msg
            state["booking_completed"] = True
            state["is_complete"] = True
            state["waiting_for_input"] = False
            ai_msg = AIMessage(content=msg)
            state["messages"] = messages + [ai_msg]

        except Exception as e:
            logger.error(f"❌ [Step 6] Checkout error: {e}")
            msg = f"❌ Có lỗi xảy ra khi đặt lịch: {str(e)}. Vui lòng thử lại."
            state["step_message"] = msg
            state["waiting_for_input"] = True
            ai_msg = AIMessage(content=msg)
            state["messages"] = messages + [ai_msg]

        return state

    # ====================================================================
    # Conditional Edge Functions
    # ====================================================================
    def route_step1(self, state: TripPlanState) -> str:
        """Route after step 1: loop or advance."""
        if state.get("current_step", 1) >= 2:
            return "step2_budget_people"
        return "step1_basic_info"

    def route_step2(self, state: TripPlanState) -> str:
        """Route after step 2: loop or advance."""
        if state.get("current_step", 2) >= 3:
            return "step3_preferences"
        return "step2_budget_people"

    def route_step3(self, state: TripPlanState) -> str:
        """Route after step 3: always advance (optional step)."""
        return "step4_plan_generation"

    def route_step4(self, state: TripPlanState) -> str:
        """Route after step 4: loop for customization or advance."""
        if state.get("current_step", 4) >= 5:
            return "step5_transportation"
        return "step4_plan_generation"

    def route_step5(self, state: TripPlanState) -> str:
        """Route after step 5: loop or advance."""
        if state.get("current_step", 5) >= 6:
            return "step6_checkout"
        return "step5_transportation"
