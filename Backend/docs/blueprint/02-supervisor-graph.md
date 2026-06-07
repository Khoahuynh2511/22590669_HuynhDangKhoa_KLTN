# 02 — SupervisorGraph (Orchestrator)

## Vai trò

Orchestrator chính, không ôm business logic. Chỉ điều phối luồng giữa các specialist agent và workflow.

## Input / Output

```text
Input:
  user_message
  user_id
  chat_room_id
  conversation_context

Output:
  final_response
  tool_cards
  follow_up_questions
  suggested_actions
```

## Luồng chính

```text
START
  -> customer_query_agent
  -> route_to_specialist
  -> specialist_agent OR workflow
  -> reply_synthesizer
END
```

## Pseudo-code LangGraph

```python
graph = StateGraph(TravelAgentState)

graph.add_node("customer_query_agent", customer_query_agent)
graph.add_node("route_to_specialist", route_to_specialist)
graph.add_node("recommendation_agent", recommendation_agent)
graph.add_node("itinerary_agent", itinerary_agent)
graph.add_node("flight_agent", flight_agent)
graph.add_node("hotel_agent", hotel_agent)
graph.add_node("transport_agent", transport_agent)
graph.add_node("booking_payment_flow", booking_payment_flow)
graph.add_node("news_search_agent", news_search_agent)
graph.add_node("reply_synthesizer", reply_synthesizer)

graph.set_entry_point("customer_query_agent")

graph.add_edge("customer_query_agent", "route_to_specialist")

graph.add_conditional_edges(
    "route_to_specialist",
    route_decision,
    {
        "recommendation": "recommendation_agent",
        "itinerary": "itinerary_agent",
        "flight": "flight_agent",
        "hotel": "hotel_agent",
        "transport": "transport_agent",
        "booking_payment": "booking_payment_flow",
        "news": "news_search_agent",
        "reply_direct": "reply_synthesizer",
    },
)

for node in [
    "recommendation_agent",
    "itinerary_agent",
    "flight_agent",
    "hotel_agent",
    "transport_agent",
    "booking_payment_flow",
    "news_search_agent",
]:
    graph.add_edge(node, "reply_synthesizer")

graph.add_edge("reply_synthesizer", END)
```

## Nguyên tắc

- Supervisor không trực tiếp gọi quá nhiều tool
- Chỉ gọi tool routing/meta nếu cần
- Không fabricate giá/tình trạng chỗ
- Nếu provider fail thì trả fallback rõ ràng
