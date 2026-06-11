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

DESTINATION_SUGGESTIONS = [
    "Đà Lạt 3 ngày",
    "Hội An 2 ngày",
    "Nha Trang 4 ngày",
    "Đà Nẵng 3 ngày",
    "Phú Quốc 3 ngày",
    "Sapa 3 ngày",
]

DURATION_SUGGESTIONS = ["2 ngày", "3 ngày", "4 ngày", "5 ngày"]

GROUP_SIZE_SUGGESTIONS = [
    "Đi một mình",
    "2 người",
    "4 người gia đình",
    "6 người bạn bè",
]

BUDGET_SUGGESTIONS = ["Tiết kiệm", "Trung bình", "Cao cấp"]

PREFERENCE_SUGGESTIONS = [
    "Thiên nhiên",
    "Ẩm thực",
    "Văn hóa",
    "Phiêu lưu",
    "Thư giãn",
    "Bỏ qua",
]

BUDGET_VI = {"economy": "tiết kiệm", "moderate": "trung bình", "luxury": "cao cấp"}
GROUP_TYPE_VI = {
    "solo": "đi một mình",
    "couple": "cặp đôi",
    "family": "gia đình",
    "friends": "bạn bè",
}


def get_step_suggestions(step: int, state: Optional[Dict[str, Any]] = None) -> list:
    """Return quick-reply suggestions for a workflow step."""
    state = state or {}
    if step == 1:
        if state.get("destination") and not state.get("duration_days"):
            return DURATION_SUGGESTIONS
        return DESTINATION_SUGGESTIONS
    if step == 2:
        if state.get("group_size") and not state.get("budget_level"):
            return BUDGET_SUGGESTIONS
        return GROUP_SIZE_SUGGESTIONS
    if step == 3:
        return PREFERENCE_SUGGESTIONS
    return []


def _parse_budget_from_text(text: str) -> Optional[str]:
    """Parse Vietnamese budget phrases into economy/moderate/luxury."""
    if not text:
        return None
    lowered = text.lower()
    if any(k in lowered for k in ["tiết kiệm", "tiet kiem", "rẻ", "giá rẻ", "bình dân", "tầm thấp"]):
        return "economy"
    if any(k in lowered for k in ["cao cấp", "cao cap", "luxury", "sang trọng", "5 sao", "đắt cũng được"]):
        return "luxury"
    if any(k in lowered for k in ["trung bình", "trung binh", "vừa phải", "moderate"]):
        return "moderate"
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*(triệu|tr\b|k\b|nghìn|ngàn|mil)", lowered)
    if match:
        amount = float(match.group(1).replace(",", "."))
        unit = match.group(2)
        if unit in {"k", "nghìn", "ngàn"}:
            amount /= 1000
        if amount <= 3:
            return "economy"
        if amount <= 8:
            return "moderate"
        return "luxury"
    return None


def _infer_preferences_from_text(text: str) -> list:
    """Map free-text Vietnamese travel style to preference categories."""
    if not text:
        return []
    lowered = text.lower()
    keyword_map = [
        (["núi", "rừng", "trek", "leo núi", "sinh thái", "camping", "thác", "đồi"], "nature"),
        (["biển", "đảo", "bãi biển", "lặn", "resort"], "relax"),
        (["ẩm thực", "món", "ăn uống", "quán", "food"], "food"),
        (["văn hóa", "lịch sử", "phố cổ", "bảo tàng", "chùa", "tâm linh"], "culture"),
        (["phiêu lưu", "mạo hiểm", "adventure", "zipline"], "adventure"),
        (["thư giãn", "spa", "nghỉ dưỡng", "chill"], "relax"),
        (["mua sắm", "shopping", "chợ"], "shopping"),
        (["chụp ảnh", "check-in", "sống ảo"], "photography"),
    ]
    prefs = []
    for keywords, category in keyword_map:
        if any(kw in lowered for kw in keywords):
            prefs.append(category)
    return list(dict.fromkeys(prefs))


def _format_group_budget_summary(size: int, gtype: str, budget: str) -> str:
    """Build a short confirmation message for step 2 completion."""
    return (
        f"**{size} người** ({GROUP_TYPE_VI.get(gtype, gtype)}), "
        f"ngân sách **{BUDGET_VI.get(budget, budget)}**."
    )


def _preferences_prompt_message(prefix: str = "") -> str:
    """Single preferences question used when entering step 3."""
    body = (
        "Bạn thích trải nghiệm gì khi đi du lịch?\n"
        "Chọn nhanh bên dưới hoặc gõ sở thích của bạn:"
    )
    if prefix:
        return f"{prefix}\n\n{body}"
    return body


PREFERENCE_CHIP_MAP = {
    "thiên nhiên": "nature",
    "ẩm thực": "food",
    "văn hóa": "culture",
    "phiêu lưu": "adventure",
    "thư giãn": "relax",
}


def _parse_preference_selection(text: str) -> Optional[list]:
    """Map quick-reply chip labels to preference categories. None if not a chip."""
    if not text:
        return None
    normalized = text.strip().lower()
    if normalized == "bỏ qua":
        return []
    category = PREFERENCE_CHIP_MAP.get(normalized)
    if category:
        return [category]
    return None


def _looks_like_preference_answer(text: str) -> bool:
    """Detect whether the user is answering the preferences question."""
    if not text or not text.strip():
        return False
    if _parse_preference_selection(text) is not None:
        return True
    if _infer_preferences_from_text(text):
        return True
    lowered = text.lower()
    pref_keywords = [
        "thích", "muốn", "thiên nhiên", "biển", "núi", "rừng", "ẩm thực", "văn hóa", "phiêu lưu",
        "thư giãn", "mua sắm", "tâm linh", "chụp ảnh", "trekking", "cafe", "spa", "du lịch",
    ]
    skip_keywords = ["bỏ qua", "skip", "đi luôn", "không có sở thích", "không cần"]
    if any(kw in lowered for kw in pref_keywords):
        return True
    return any(kw in lowered for kw in skip_keywords)


def _finalize_preferences(state: TripPlanState, messages: list, prefs: list) -> TripPlanState:
    """Save preferences and advance to step 4."""
    prefs_vi_map = {
        "nature": "Thiên nhiên",
        "food": "Ẩm thực",
        "culture": "Văn hóa",
        "adventure": "Phiêu lưu",
        "relax": "Thư giãn",
        "shopping": "Mua sắm",
        "spiritual": "Tâm linh",
        "photography": "Chụp ảnh",
    }
    state["preferences"] = prefs
    state["constraints"] = None
    state["preferences_asked"] = True
    if prefs:
        prefs_display = ", ".join([prefs_vi_map.get(p, p) for p in prefs])
        msg = f"Tuyệt! Sở thích của bạn: **{prefs_display}**. Mình sẽ tìm các hoạt động phù hợp nhất!"
    else:
        msg = "Không sao! Mình sẽ chọn những trải nghiệm phổ biến nhất cho bạn. Đang lên lịch trình..."
    state["step_message"] = msg
    state["waiting_for_input"] = False
    state["quick_suggestions"] = []
    state["current_step"] = 4
    state["messages"] = messages + [AIMessage(content=msg)]
    return state


def _advance_to_preferences(state: TripPlanState, messages: list, prefix: str = "") -> TripPlanState:
    """Move to step 3 with the preferences question and quick replies."""
    msg = _preferences_prompt_message(prefix)
    state["current_step"] = 3
    state["preferences_asked"] = True
    return _reply_waiting(state, messages, msg, PREFERENCE_SUGGESTIONS)


def _reply_waiting(state: TripPlanState, messages: list, msg: str, suggestions: list) -> TripPlanState:
    """Set assistant reply and quick suggestions while waiting for user input."""
    state["step_message"] = msg
    state["waiting_for_input"] = True
    state["quick_suggestions"] = suggestions
    state["messages"] = messages + [AIMessage(content=msg)]
    return state


def _reply_done(state: TripPlanState, messages: list, msg: str, next_step: int) -> TripPlanState:
    """Set assistant reply and advance without waiting."""
    state["step_message"] = msg
    state["waiting_for_input"] = False
    state["quick_suggestions"] = []
    state["current_step"] = next_step
    state["messages"] = messages + [AIMessage(content=msg)]
    return state


def _parse_destination_duration_chip(text: str) -> tuple:
    """Parse quick-reply like 'Đà Lạt 3 ngày' into destination and duration."""
    if not text:
        return None, None
    from app.v1.services.trip_planning.activity_service import normalize_destination

    duration = None
    match = re.search(r"(\d+)\s*ngày", text, re.IGNORECASE)
    if match:
        duration = int(match.group(1))
    destination = normalize_destination(text)
    return destination or None, duration


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
    # Smarter extraction: tries to extract ALL info from one message.
    # ====================================================================
    async def step1_basic_info_node(self, state: TripPlanState) -> TripPlanState:
        """
        Extract destination, duration, and optionally group/budget from user's message.
        Tries to extract as much as possible in one go to minimize back-and-forth.
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

        chip_dest, chip_duration = _parse_destination_duration_chip(last_user_msg)
        if chip_dest and not state.get("destination"):
            state["destination"] = chip_dest
        if chip_duration and not state.get("duration_days"):
            state["duration_days"] = chip_duration

        if state.get("destination"):
            from app.v1.services.trip_planning.activity_service import normalize_destination
            state["destination"] = normalize_destination(state["destination"])

        # Check if data already exists from previous interaction
        existing_dest = state.get("destination")
        existing_duration = state.get("duration_days")

        if existing_dest and existing_duration:
            if state.get("group_size") and state.get("budget_level"):
                prefix = _format_group_budget_summary(
                    state["group_size"],
                    state.get("group_type") or "friends",
                    state["budget_level"],
                )
                return _advance_to_preferences(state, messages, prefix)
            if state.get("group_size") and not state.get("budget_level"):
                parsed_budget = _parse_budget_from_text(last_user_msg)
                if parsed_budget:
                    state["budget_level"] = parsed_budget
                    prefix = _format_group_budget_summary(
                        state["group_size"],
                        state.get("group_type") or "friends",
                        parsed_budget,
                    )
                    return _advance_to_preferences(state, messages, prefix)
            if state.get("group_size"):
                msg = "Ngân sách bạn muốn khoảng bao nhiêu?"
                state["current_step"] = 2
                return _reply_waiting(state, messages, msg, BUDGET_SUGGESTIONS)
            msg = f"Kế hoạch **{existing_dest}** **{existing_duration} ngày**. Bạn đi mấy người?"
            state["current_step"] = 2
            return _reply_waiting(state, messages, msg, GROUP_SIZE_SUGGESTIONS)

        # Use LLM to extract — comprehensive extraction
        prompt = """Bạn là trợ lý du lịch thông minh. Phân tích tin nhắn người dùng và trích xuất TẤT CẢ thông tin có thể.

Trả về CHỈ JSON, không giải thích thêm:
{
  "destination": "tên địa điểm hoặc null",
  "duration_days": số_ngày_hoặc_null,
  "travel_date": "YYYY-MM-DD hoặc null",
  "group_size": số_người_hoặc_null,
  "group_type": "solo|couple|family|friends|null",
  "budget_level": "economy|moderate|luxury|null",
  "preferences": ["nature", "food", ...] hoặc null
}

Lưu ý:
- Nếu user nói "đi Đà Lạt 3 ngày" → destination="Đà Lạt", duration_days=3
- Nếu user nói "đi biển với gia đình" → gợi ý destination gần biển, group_type="family"
- Nếu user nói "4 bạn đi Nha Trang" → group_size=4, group_type="friends", destination="Nha Trang"
- Nếu user nói "đi Đà Lạt tiết kiệm" → budget_level="economy"
- Trích xuất tối đa thông tin, để null cho những gì KHÔNG có trong tin nhắn."""

        try:
            llm_response = await self._ask_llm(prompt, last_user_msg)
            extracted = _extract_json_from_llm(llm_response)
            logger.info(f"🔍 [Step 1] Extracted: {extracted}")
        except Exception as e:
            logger.error(f"❌ [Step 1] LLM error: {e}")
            extracted = None

        if extracted:
            if extracted.get("destination") and not state.get("destination"):
                from app.v1.services.trip_planning.activity_service import normalize_destination
                state["destination"] = normalize_destination(extracted["destination"])
            if extracted.get("duration_days") and not state.get("duration_days"):
                try:
                    state["duration_days"] = int(extracted["duration_days"])
                except (ValueError, TypeError):
                    pass
            if extracted.get("travel_date") and not state.get("travel_date"):
                state["travel_date"] = extracted["travel_date"]
            # Bonus: extract extra info if provided upfront
            if extracted.get("group_size") and not state.get("group_size"):
                try:
                    state["group_size"] = int(extracted["group_size"])
                except (ValueError, TypeError):
                    pass
            if extracted.get("group_type") and not state.get("group_type"):
                state["group_type"] = extracted["group_type"]
            if extracted.get("budget_level") and not state.get("budget_level"):
                state["budget_level"] = extracted["budget_level"]
            if extracted.get("preferences") and not state.get("preferences"):
                state["preferences"] = extracted["preferences"]

        # Check completeness
        dest = state.get("destination")
        dur = state.get("duration_days")

        if dest and dur:
            extra_info = []
            if state.get("group_size"):
                extra_info.append(f"**{state['group_size']} người**")
            if state.get("budget_level"):
                budget_vi = {"economy": "tiết kiệm", "moderate": "trung bình", "luxury": "cao cấp"}
                extra_info.append(f"ngân sách **{budget_vi.get(state['budget_level'], state['budget_level'])}**")

            extra_str = f" ({', '.join(extra_info)})" if extra_info else ""
            msg = (
                f"Tuyệt vời! Kế hoạch đi **{dest}** trong **{dur} ngày**{extra_str}.\n\n"
            )

            if state.get("group_size") and state.get("budget_level"):
                gtype = state.get("group_type") or "friends"
                prefix = _format_group_budget_summary(state["group_size"], gtype, state["budget_level"])
                return _advance_to_preferences(state, messages, prefix.strip())

            if state.get("group_size") and not state.get("budget_level"):
                msg += "Ngân sách bạn muốn khoảng bao nhiêu?"
                state["current_step"] = 2
                return _reply_waiting(state, messages, msg, BUDGET_SUGGESTIONS)

            msg += "Bạn đi **mấy người**? Chọn gợi ý bên dưới:"
            state["current_step"] = 2
            return _reply_waiting(state, messages, msg, GROUP_SIZE_SUGGESTIONS)
        elif dest and not dur:
            msg = (
                f"**{dest}** là lựa chọn tuyệt vời! Bạn muốn đi **mấy ngày**?\n"
                "Chọn nhanh hoặc nhập số ngày:"
            )
            state["current_step"] = 1
            return _reply_waiting(state, messages, msg, DURATION_SUGGESTIONS)
        else:
            ask_msg = (
                "Chào bạn! Mình sẽ giúp bạn lên kế hoạch du lịch.\n"
                "Bạn muốn đi **đâu** và **bao lâu**? Chọn gợi ý hoặc gõ tự do:"
            )
            state["current_step"] = 1
            return _reply_waiting(state, messages, ask_msg, DESTINATION_SUGGESTIONS)

    # ====================================================================
    # STEP 2: Participants & Budget
    # Smarter: defaults to moderate budget, infers group type from size.
    # ====================================================================
    async def step2_budget_people_node(self, state: TripPlanState) -> TripPlanState:
        """
        Extract group size, type, and budget level.
        Uses sensible defaults to minimize back-and-forth.
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
            prefix = _format_group_budget_summary(existing_size, existing_type, existing_budget)
            return _advance_to_preferences(state, messages, prefix)

        if not state.get("budget_level") and last_user_msg:
            parsed_budget = _parse_budget_from_text(last_user_msg)
            if parsed_budget:
                state["budget_level"] = parsed_budget

        prompt = """Trích xuất thông tin nhóm và ngân sách từ tin nhắn người dùng.
Trả về CHỈ JSON:
{"group_size": số_người, "group_type": "solo|couple|family|friends", "budget_level": "economy|moderate|luxury"}
group_type: solo=1 người, couple=2 người yêu, family=gia đình, friends=bạn bè
budget_level: economy=tiết kiệm, moderate=trung bình, luxury=cao cấp

Lưu ý:
- "không quan trọng", "bất kỳ", "tùy" → budget_level=null
- "tiết kiệm", "rẻ", "giá rẻ" → economy
- "cao cấp", "sang trọng", "đắt cũng được" → luxury
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
                try:
                    state["group_size"] = int(extracted["group_size"])
                except (ValueError, TypeError):
                    pass
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
                elif size >= 3:
                    state["group_type"] = "friends"

        size = state.get("group_size")
        gtype = state.get("group_type")
        budget = state.get("budget_level")

        # Apply sensible defaults if user provides partial info
        if size and not gtype:
            if size == 1:
                gtype = "solo"
            elif size == 2:
                gtype = "couple"
            else:
                gtype = "friends"
            state["group_type"] = gtype

        if size and gtype:
            if not budget:
                msg = (
                    f"Đã rõ **{size} người** ({GROUP_TYPE_VI.get(gtype, gtype)}). "
                    "Ngân sách bạn muốn khoảng bao nhiêu?"
                )
                return _reply_waiting(state, messages, msg, BUDGET_SUGGESTIONS)

            msg = _format_group_budget_summary(size, gtype, budget)
            return _advance_to_preferences(state, messages, msg)
        else:
            msg = "Bạn đi **mấy người**? Chọn gợi ý bên dưới hoặc gõ tự do:"
            return _reply_waiting(state, messages, msg, GROUP_SIZE_SUGGESTIONS)

    # ====================================================================
    # STEP 3: Preferences (Optional - can skip)
    # Shows quick suggestion examples for user.
    # ====================================================================
    async def step3_preferences_node(self, state: TripPlanState) -> TripPlanState:
        """
        Extract preferences. This step is optional - user can skip.
        Always advances to step 4 after processing.
        Shows helpful suggestions to guide user.
        """
        logger.info("[Step 3] Preferences Node")
        state["current_step"] = 3

        messages = state.get("messages", [])

        last_user_msg = ""
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                last_user_msg = msg.content
                break

        chip_prefs = _parse_preference_selection(last_user_msg)
        if chip_prefs is not None:
            return _finalize_preferences(state, messages, chip_prefs)

        if not state.get("preferences_asked"):
            if _looks_like_preference_answer(last_user_msg):
                state["preferences_asked"] = True
            else:
                return _advance_to_preferences(state, messages)

        skip_keywords = ["bỏ qua", "skip", "đi luôn", "không có sở thích", "không cần"]
        pref_keywords = [
            "thích", "muốn", "thiên nhiên", "biển", "núi", "rừng", "ẩm thực", "văn hóa", "phiêu lưu",
            "thư giãn", "mua sắm", "tâm linh", "chụp ảnh", "trekking", "cafe", "spa",
            "cảnh đẹp", "chùa", "phố cổ", "chợ", "đồi", "thác", "hồ", "du lịch", "sinh thái",
        ]
        lowered_msg = last_user_msg.lower()
        has_pref = any(kw in lowered_msg for kw in pref_keywords)
        wants_skip = any(kw in lowered_msg for kw in skip_keywords)

        inferred_prefs = _infer_preferences_from_text(last_user_msg)
        if inferred_prefs:
            return _finalize_preferences(state, messages, inferred_prefs)

        if wants_skip or (not has_pref and len(last_user_msg.strip()) <= 3):
            return _finalize_preferences(state, messages, [])

        # Extract preferences from user message using LLM
        prompt = """Trích xuất sở thích du lịch từ tin nhắn người dùng.
Trả về CHỈ JSON:
{"preferences": ["nature", "food", ...], "constraints": "yêu cầu đặc biệt hoặc null"}
Categories: nature, food, culture, adventure, relax, shopping, spiritual, photography
Nếu người dùng không nêu, trả về danh sách rỗng."""

        try:
            llm_response = await self._ask_llm(prompt, last_user_msg)
            extracted = _extract_json_from_llm(llm_response)
        except Exception:
            extracted = None

        if extracted and extracted.get("preferences"):
            state["constraints"] = extracted.get("constraints")
            return _finalize_preferences(state, messages, extracted["preferences"])

        return _finalize_preferences(state, messages, [])

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
        from app.v1.services.trip_planning.activity_service import normalize_destination
        destination = normalize_destination(destination)
        state["destination"] = destination
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
    # Smarter: auto-skips if no travel_date, better messaging.
    # ====================================================================
    async def step5_transportation_node(self, state: TripPlanState) -> TripPlanState:
        """
        Search for flights and trains based on destination + date.
        User can select or skip. Auto-skips if no travel_date provided.
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
           (state.get("needs_flight") is False and state.get("needs_train") is False):
            state["current_step"] = 6
            state["waiting_for_input"] = False
            return state

        # --- Check if user wants to skip ---
        skip_kw = ["không", "bỏ qua", "skip", "đi luôn", "tiếp", "tự lo", "tự sắp xếp", "không cần"]
        if any(kw in last_user_msg.lower() for kw in skip_kw):
            state["needs_flight"] = False
            state["needs_train"] = False
            state["flight_search_results"] = []
            state["train_search_results"] = []
            msg = "👌 Bạn sẽ tự sắp xếp di chuyển. Tiến hành tóm tắt đơn hàng nhé!"
            state["step_message"] = msg
            state["current_step"] = 6
            state["waiting_for_input"] = False
            ai_msg = AIMessage(content=msg)
            state["messages"] = messages + [ai_msg]
            return state

        # --- Auto-skip if no travel_date (can't search flights/trains without date) ---
        if not travel_date:
            dest_lower = destination.lower().strip()
            has_airport = DESTINATION_AIRPORTS.get(dest_lower, "")
            has_station = DESTINATION_STATIONS.get(dest_lower, "")

            if has_airport or has_station:
                msg = (f"🚌 Để tìm chuyến bay/tàu đến **{destination}**, bạn cho mình biết **ngày đi** được không? "
                       "_(Định dạng: 2025-01-15 hoặc 15/01/2025)_\n\n"
                       "Hoặc gõ **'bỏ qua'** nếu bạn tự sắp xếp di chuyển.")
                state["step_message"] = msg
                state["waiting_for_input"] = True
                ai_msg = AIMessage(content=msg)
                state["messages"] = messages + [ai_msg]
                return state
            else:
                # No transport options available for this destination
                state["needs_flight"] = False
                state["needs_train"] = False
                msg = "Tuyệt! Chuyển sang bước thanh toán. 💳"
                state["step_message"] = msg
                state["current_step"] = 6
                state["waiting_for_input"] = False
                ai_msg = AIMessage(content=msg)
                state["messages"] = messages + [ai_msg]
                return state

        # --- First time: search for transport ---
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
                lines = [f"✈️ **Phương tiện di chuyển đến {destination}:**\n"]
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
                msg = ("Không tìm thấy chuyến bay/tàu phù hợp cho ngày này. "
                       "_(Gõ **'bỏ qua'** để tiếp tục)_")
                state["needs_flight"] = False
                state["needs_train"] = False

            state["step_message"] = msg
            state["waiting_for_input"] = True
            ai_msg = AIMessage(content=msg)
            state["messages"] = messages + [ai_msg]
            return state

        # --- User responded with selection ---
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

        # If already paid / completed
        if state.get("booking_completed"):
            state["is_complete"] = True
            return state

        from app.v1.services.trip_planning.trip_checkout_service import (
            calculate_grand_total,
            trip_checkout_service,
        )

        grand_total = calculate_grand_total(state)

        # Check if user confirms checkout
        confirm_kw = ["thanh toán", "pay", "xác nhận", "ok", "oke", "đồng ý", "chốt"]
        if not any(kw in last_user_msg.lower() for kw in confirm_kw):
            itinerary = state.get("confirmed_itinerary", state.get("suggested_itinerary", {}))
            dest = state.get("destination", "")
            days = state.get("duration_days", 0)
            size = state.get("group_size", 1)
            activity_total = float(state.get("itinerary_total_price") or 0)
            transport_extra = grand_total - activity_total

            lines = [
                "**Tóm tắt đơn hàng:**",
                f"- Điểm đến: **{dest}** ({days} ngày)",
                f"- Số người: **{size}**",
            ]
            if state.get("selected_flight"):
                lines.append(f"- Chuyến bay: {state['selected_flight'].get('airline', '')}")
            if state.get("selected_train"):
                lines.append(f"- Tàu: {state['selected_train'].get('train_name', '')}")
            lines.append(f"\n**Tổng thanh toán: {grand_total:,.0f}đ**")
            lines.append(f"  (Hoạt động: {activity_total:,.0f}đ + Di chuyển: {transport_extra:,.0f}đ)\n")
            lines.append("Nhấn **Thanh toán ngay** bên dưới để tạo đơn và chuyển đến VNPay.")

            msg = "\n".join(lines)
            state["step_message"] = msg
            state["waiting_for_input"] = True
            state["quick_suggestions"] = []
            ai_msg = AIMessage(content=msg)
            state["messages"] = messages + [ai_msg]
            return state

        # --- Process checkout: booking + VNPay (same as tour flow) ---
        if state.get("payment_url") and state.get("booking_id"):
            msg = (
                "Đơn hàng đã được tạo. Nhấn **Thanh toán VNPay** bên dưới để hoàn tất.\n\n"
                f"Mã booking: `{state['booking_id']}`"
            )
            state["step_message"] = msg
            state["waiting_for_input"] = False
            ai_msg = AIMessage(content=msg)
            state["messages"] = messages + [ai_msg]
            return state

        checkout = await trip_checkout_service.create_checkout(
            state,
            ip_addr=state.get("_client_ip") or "127.0.0.1",
        )

        if not checkout.get("success"):
            msg = f"Có lỗi khi tạo đơn hàng: {checkout.get('error', 'Không xác định')}. Vui lòng thử lại."
            state["step_message"] = msg
            state["waiting_for_input"] = True
            ai_msg = AIMessage(content=msg)
            state["messages"] = messages + [ai_msg]
            return state

        state["custom_plan_id"] = checkout.get("plan_id")
        state["booking_id"] = checkout.get("booking_id")
        state["payment_url"] = checkout.get("payment_url")
        state["booking_completed"] = False
        state["waiting_for_input"] = False
        state["is_complete"] = False

        msg = (
            "Đơn hàng đã được tạo thành công!\n\n"
            f"- Mã kế hoạch: `{checkout.get('plan_id')}`\n"
            f"- Mã booking: `{checkout.get('booking_id')}`\n"
            f"- Tổng: **{checkout.get('total_price', 0):,.0f}đ**\n\n"
            "Nhấn **Thanh toán VNPay** bên dưới để chuyển đến cổng thanh toán."
        )
        state["step_message"] = msg
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
