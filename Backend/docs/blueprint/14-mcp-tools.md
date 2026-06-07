# 14 — MCP Tools Blueprint

## Folder Structure

```text
Backend/app/v1/mcp/
├── server.py
└── src/
    ├── tools/
    │   ├── booking_tools.py
    │   ├── tour_search_tools.py
    │   ├── search_personalization.py
    │   ├── weather_tools.py
    │   ├── flight_tools.py
    │   ├── hotel_tools.py          (new)
    │   ├── transport_tools.py      (new)
    │   ├── itinerary_tools.py      (new)
    │   ├── concierge_tools.py      (new)
    │   └── __init__.py
    ├── schema/
    │   ├── flight_schema.py
    │   ├── hotel_schema.py
    │   ├── transport_schema.py
    │   └── itinerary_schema.py
    └── core/
        ├── supabase.py
        ├── memory.py
        └── config.py
```

## Tool Ownership per Agent

| Agent | Tools |
|---|---|
| RecommendationAgent | `search_tour_packages`, `search_episodes`, `recommend_destinations` |
| ItineraryAgent | `search_tour_sessions`, `ai_build_itinerary`, `suggest_fill_gaps`, `save_custom_tour`, `share_custom_tour` |
| FlightAgent | `get_airport_suggestions`, `search_flights`, `search_flight_offers`, `book_flight` |
| HotelAgent | `search_hotels`, `get_hotel_details`, `compare_hotels`, `book_hotel` |
| TransportAgent | `search_transport`, `get_route_details`, `book_transport_ticket` |
| BookingPaymentFlow | `create_booking`, `update_booking`, `verify_otp_and_confirm_booking`, `resend_otp`, `create_payment`, `apply_promotion_code` |
| NewsSearchAgent | `search_latest_tour_info`, `perplexity_search` |
| AdminGraph | `query_database` |

## Extension Pattern

1. Tạo file `Backend/app/v1/mcp/src/tools/<feature>_tools.py`
2. Khai báo `register_<feature>_tools(mcp: FastMCP)` chứa các `@mcp.tool()`
3. Import và gọi trong `mcp/src/tools/__init__.py::register_all_tools`
4. Optional: tách sub-server FastMCP trong `mcp/server.py` rồi `import_server`
5. Cập nhật `Backend/agent.yaml` block `tool_calling.available_tools`
