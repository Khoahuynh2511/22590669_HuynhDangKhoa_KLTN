# Blueprint Summary — AI Travel Multi-Agent Platform

> Hybrid Multi-Agent Architecture: sub-agent cho tư vấn, workflow cứng cho giao dịch, event jobs cho tác vụ chủ động.

---

## Component Index

| # | File | Component | Trạng thái |
|---|---|---|---|
| 01 | [01-architecture-overview.md](./01-architecture-overview.md) | Architecture tổng thể + tech stack | Nền tảng |
| 02 | [02-supervisor-graph.md](./02-supervisor-graph.md) | SupervisorGraph / Orchestrator | Refactor từ hiện tại |
| 03 | [03-customer-query-agent.md](./03-customer-query-agent.md) | CustomerQueryAgent (NLU + slots) | Mới |
| 04 | [04-recommendation-agent.md](./04-recommendation-agent.md) | RecommendationAgent | Đã có, cải tiến |
| 05 | [05-itinerary-agent.md](./05-itinerary-agent.md) | ItineraryAgent (tour builder) | Mới |
| 06 | [06-flight-agent.md](./06-flight-agent.md) | FlightAgent | Mở rộng từ search → book |
| 07 | [07-hotel-agent.md](./07-hotel-agent.md) | HotelAgent | Mới |
| 08 | [08-transport-agent.md](./08-transport-agent.md) | TransportAgent | Mới |
| 09 | [09-booking-payment-flow.md](./09-booking-payment-flow.md) | BookingPaymentFlow (state machine) | Tách từ hiện tại |
| 10 | [10-news-search-agent.md](./10-news-search-agent.md) | NewsSearchAgent | Đã có, chuẩn hóa |
| 11 | [11-admin-graph.md](./11-admin-graph.md) | AdminGraph | Đã có, mở rộng |
| 12 | [12-concierge-event-jobs.md](./12-concierge-event-jobs.md) | ConciergeAgent & Event Jobs | Mới |
| 13 | [13-intent-routing.md](./13-intent-routing.md) | Intent Routing Table | Mới |
| 14 | [14-mcp-tools.md](./14-mcp-tools.md) | MCP Tools Blueprint | Mở rộng |
| 15 | [15-state-management.md](./15-state-management.md) | State Management (LangGraph) | Mới |
| 16 | [16-database.md](./16-database.md) | Database Schema | Mở rộng |
| 17 | [17-api-endpoints.md](./17-api-endpoints.md) | API Endpoints | Mở rộng |
| 18 | [18-frontend.md](./18-frontend.md) | Frontend Components & UI Payload | Mở rộng |
| 19 | [19-observability.md](./19-observability.md) | Observability & Monitoring | Mới |
| 20 | [20-guardrails.md](./20-guardrails.md) | Guardrails & Security | Mới |
| 21 | [21-roadmap.md](./21-roadmap.md) | Build Roadmap (6 phases) | Plan |

---

## Build Phases (tóm tắt)

| Phase | Nội dung | Dependencies |
|---|---|---|
| **1 — Refactor nền** | CustomerQueryAgent, RouteToSpecialist, ReplySynthesizer, sửa SupervisorGraph | None |
| **2 — Specialist agents** | ItineraryAgent, FlightAgent, HotelAgent, TransportAgent | Phase 1 |
| **3 — MCP mở rộng** | itinerary_tools, hotel_tools, transport_tools, flight_tools upgrade | Phase 2 |
| **4 — BookingPaymentFlow** | Tách workflow, BookingState, idempotency, OTP, payment callback | Phase 1 |
| **5 — Frontend cards** | ui_payload chuẩn hóa, render cards, Tour Builder drag&drop, admin dashboard | Phase 2–4 |
| **6 — Event jobs** | Price alert, weather disruption, trip reminders, concierge, travel journal | Phase 2–4 |

---

## Kiến trúc chốt

```text
Frontend Angular 19
  → FastAPI AgentRouter
  → SupervisorGraph / Orchestrator
      → CustomerQueryAgent (NLU)
      → Specialist Sub-agents (advisory)
      → BookingPaymentWorkflow (transactional)
      → ReplySynthesizer (output)
  → FastMCP Composite Server (tool execution)
  → Supabase / Redis / Mem0 / FalkorDB / External APIs (storage)
  → APScheduler / Redis Queue (event jobs)
```

**Pattern:** Hybrid Multi-Agent + Deterministic Transaction Workflow + Event-driven Concierge.
