# 15 — State Management

## TravelAgentState (Main Graph)

```python
class TravelAgentState(TypedDict):
    user_id: str
    chat_room_id: str
    messages: list[dict]

    # NLU output
    intent: str | None
    confidence: float
    slots: dict
    missing_slots: list[str]

    # Routing
    selected_agent: str | None
    agent_result: dict | None

    # Domain contexts
    booking_context: dict | None
    itinerary_context: dict | None
    payment_context: dict | None

    # Memory
    memory_context: list[dict]

    # Error tracking
    errors: list[dict]

    # Final output
    final_response: str | None
    ui_payload: dict | None
```

## BookingState (Transaction Workflow)

```python
class BookingState(TypedDict):
    booking_type: Literal["tour", "flight", "hotel", "transport"]
    user_id: str
    selected_item: dict
    passengers: list[dict]
    contact: dict
    booking_id: str | None
    otp_status: Literal["not_sent", "sent", "verified"]
    payment_id: str | None
    payment_url: str | None
    status: Literal["draft", "pending_otp", "pending_payment", "confirmed", "cancelled"]
```

## LangGraph Folder Structure

```text
Backend/app/v1/services/agent_services/
├── graphs/
│   ├── supervisor_graph.py
│   ├── booking_payment_workflow.py
│   └── event_orchestrator.py
├── agents/
│   ├── customer_query_agent.py
│   ├── recommendation_agent.py
│   ├── itinerary_agent.py
│   ├── flight_agent.py
│   ├── hotel_agent.py
│   ├── transport_agent.py
│   ├── concierge_agent.py
│   └── reply_synthesizer.py
├── routing/
│   ├── intent_schema.py
│   ├── route_policy.py
│   └── slot_policy.py
└── state/
    ├── conversation_state.py
    ├── booking_state.py
    └── itinerary_state.py
```
