"""
Trip Planning Schema
Pydantic models for trip planning API requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class TripPlanRequest(BaseModel):
    """Request to send a message in the trip planning workflow."""
    message: str = Field(..., description="User message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context")
    room_id: Optional[str] = Field(None, description="Chat room ID for persistence")
    updated_itinerary: Optional[Dict[str, Any]] = Field(None, description="User-modified itinerary from drag-and-drop")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Tôi muốn đi Đà Lạt 3 ngày",
                "conversation_id": "plan_abc123",
                "room_id": "room_xyz789"
            }
        }


class TripPlanStartRequest(BaseModel):
    """Request to start a new trip planning session."""
    destination: Optional[str] = Field(None, description="Pre-fill destination")
    duration_days: Optional[int] = Field(None, description="Pre-fill duration")

    class Config:
        json_schema_extra = {
            "example": {
                "destination": "Đà Lạt",
                "duration_days": 3
            }
        }


class ActivityPackageSchema(BaseModel):
    """Activity package data for API responses."""
    activity_id: str
    name: str
    description: Optional[str] = None
    destination: str
    time_slot: str
    category: Optional[str] = None
    duration_hours: Optional[float] = None
    price: float = 0
    difficulty: str = "easy"
    location: Optional[str] = None
    image_url: Optional[str] = None
    gallery_urls: Optional[List[str]] = None
    included_services: Optional[List[str]] = None
    max_participants: int = 20
    min_participants: int = 1
    is_ai_generated: bool = False


class ItinerarySlotSchema(BaseModel):
    """Single slot in an itinerary day."""
    activity_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    price: float = 0
    duration_hours: Optional[float] = None
    category: Optional[str] = None
    time_slot: Optional[str] = None
    location: Optional[str] = None
    image_url: Optional[str] = None


class ItineraryDaySchema(BaseModel):
    """One day of an itinerary with 3 slots."""
    morning: Optional[ItinerarySlotSchema] = None
    afternoon: Optional[ItinerarySlotSchema] = None
    evening: Optional[ItinerarySlotSchema] = None


class CustomizeItineraryRequest(BaseModel):
    """Request to customize specific itinerary slots."""
    conversation_id: str
    itinerary: Dict[str, Dict[str, Optional[str]]] = Field(
        ...,
        description="Updated itinerary: {day_1: {morning: activity_id, afternoon: activity_id, ...}}"
    )


class TripPlanStateResponse(BaseModel):
    """Response containing the current state of the trip plan."""
    conversation_id: str
    current_step: int
    step_message: str
    waiting_for_input: bool
    is_complete: bool

    # Collected data
    destination: Optional[str] = None
    travel_date: Optional[str] = None
    duration_days: Optional[int] = None
    group_size: Optional[int] = None
    group_type: Optional[str] = None
    budget_level: Optional[str] = None
    preferences: Optional[List[str]] = None

    # Step 4 data
    available_activities: List[Dict[str, Any]] = []
    suggested_itinerary: Dict[str, Any] = {}
    confirmed_itinerary: Dict[str, Any] = {}
    itinerary_total_price: Optional[float] = None

    # Step 5 data
    flight_search_results: List[Dict[str, Any]] = []
    train_search_results: List[Dict[str, Any]] = []
    selected_flight: Optional[Dict[str, Any]] = None
    selected_train: Optional[Dict[str, Any]] = None

    # Step 6 data
    custom_plan_id: Optional[str] = None
    booking_completed: bool = False
