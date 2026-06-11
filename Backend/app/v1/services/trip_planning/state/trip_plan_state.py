"""
Trip Plan State Definitions
State schema for the 6-step trip planning static workflow.
"""
from typing import Optional, List, Dict, Any
from langgraph.graph import MessagesState


class TripPlanState(MessagesState):
    """
    State for the modular itinerary building workflow.

    Extends MessagesState from LangGraph for proper message handling.
    Tracks current step, collected data, itinerary, and checkout info.
    """

    # === Context ===
    conversation_id: str
    user_id: str
    current_step: int  # 1-6

    # === Step 1: Basic Info ===
    destination: Optional[str]
    travel_date: Optional[str]
    duration_days: Optional[int]

    # === Step 2: Participants & Budget ===
    group_size: Optional[int]
    group_type: Optional[str]       # solo, couple, family, friends
    budget_level: Optional[str]     # economy, moderate, luxury

    # === Step 3: Preferences ===
    preferences: Optional[List[str]]  # ["nature", "food", "adventure"]
    constraints: Optional[str]

    # === Step 4: Modular Itinerary ===
    available_activities: List[Dict[str, Any]]  # All activities for this destination
    suggested_itinerary: Dict[str, Dict[str, Any]]
    # Format: { "day_1": {"morning": {activity_obj}, "afternoon": {...}, "evening": {...}}, ... }
    confirmed_itinerary: Dict[str, Dict[str, Any]]  # User-confirmed version
    itinerary_total_price: Optional[float]

    # === Step 5: Transportation ===
    needs_flight: Optional[bool]
    needs_train: Optional[bool]
    selected_flight: Optional[Dict[str, Any]]
    selected_train: Optional[Dict[str, Any]]
    flight_search_results: List[Dict[str, Any]]
    train_search_results: List[Dict[str, Any]]

    # === Step 6: Checkout ===
    custom_plan_id: Optional[str]
    booking_id: Optional[str]
    payment_url: Optional[str]
    booking_completed: bool

    # === Flow control ===
    step_message: str
    waiting_for_input: bool
    is_complete: bool
