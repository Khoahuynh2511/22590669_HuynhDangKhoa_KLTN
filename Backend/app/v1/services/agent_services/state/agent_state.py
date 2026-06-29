"""
Agent State Definitions
Shared state schemas for multi-agent system
"""
from typing import Optional, List, Dict, Any
from langgraph.graph import MessagesState


class AgentState(MessagesState):
    """
    Shared state between all agents

    Extends MessagesState from LangGraph for proper message handling.
    All agents can read/write to this shared state.
    """
    # Conversation context
    conversation_id: str
    user_id: str

    # Customer Query Agent (NLU front-door) — intent/slots đã rút trích
    intent: str
    nlu_slots: Dict[str, Any]
    nlu_missing_slots: List[str]

    # Chat Agent outputs
    chat_response: str

    # Recommendation Agent outputs
    needs_recommendation: bool
    recommendation_params: Dict[str, Any]

    # Shared data
    recommended_package_ids: List[str]
    tour_packages: List[Dict[str, Any]]  # Full tour package objects for API response

    # Ephemeral UI artifacts (cards / payment UI). Reset each new turn so stale
    # recommendations from a previous turn don't re-render. NOTE: tour_packages is
    # intentionally NOT reset here — it's reused by create_booking validation/fallback.
    mcp_ui_resource: Optional[Dict[str, Any]]
    mcp_ui_html: Optional[str]

    # OTP & Booking tracking
    user_email: Optional[str]  # Email của user để gửi OTP
    pending_booking_id: Optional[str]  # Booking ID đang chờ verify OTP
    pending_otp_code: Optional[str]  # OTP code for demo popup on client

    # Flight Agent
    needs_flight: bool
    flight_params: Dict[str, Any]

    # Train Agent
    needs_train: bool
    train_params: Dict[str, Any]

    # Bus Agent
    needs_bus: bool
    bus_params: Dict[str, Any]

    # Hotel Agent
    needs_hotel: bool
    hotel_params: Dict[str, Any]

    # Final output
    final_response: str
