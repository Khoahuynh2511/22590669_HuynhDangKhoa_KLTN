# 21 — Build Roadmap

## Phase 1 — Refactor nền

| # | Task | Mô tả |
|---|---|---|
| 1 | Tạo CustomerQueryAgent | NLU + slot extraction |
| 2 | Tạo route_to_specialist | Conditional routing logic |
| 3 | Tạo ReplySynthesizer | Gom output, trả lời tự nhiên |
| 4 | Sửa SupervisorGraph | Chuyển thành orchestrator thuần |
| 5 | Giữ nguyên | RecommendationAgent, AdminGraph, NewsSearchAgent |

## Phase 2 — Tách specialist agents

| # | Task | Mô tả |
|---|---|---|
| 1 | ItineraryAgent | Xây lịch trình, tour builder |
| 2 | FlightAgent | Mở rộng từ search → offer + book |
| 3 | HotelAgent | Implement mới |
| 4 | TransportAgent | Implement mới |

## Phase 3 — MCP mở rộng

| # | Task | Mô tả |
|---|---|---|
| 1 | `itinerary_tools.py` | Tools cho ItineraryAgent |
| 2 | `hotel_tools.py` | Tools cho HotelAgent |
| 3 | `transport_tools.py` | Tools cho TransportAgent |
| 4 | Mở rộng `flight_tools.py` | Thêm Amadeus offer + book |
| 5 | Update `register_all_tools` | Register new tools |
| 6 | Update `agent.yaml` | Declare available tools |

## Phase 4 — BookingPaymentFlow

| # | Task | Mô tả |
|---|---|---|
| 1 | Tách workflow | Booking/payment khỏi chat LLM tự do |
| 2 | Chuẩn hóa BookingState | Unified state cho tour/flight/hotel/transport |
| 3 | Idempotency | create_booking / create_payment |
| 4 | OTP state transition | Expiry + retry limit |
| 5 | Payment callback | VNPay confirmation flow |

## Phase 5 — Frontend cards

| # | Task | Mô tả |
|---|---|---|
| 1 | Chuẩn hóa `ui_payload` | Standard response format |
| 2 | Render cards | flight/hotel/tour/itinerary/payment |
| 3 | Tour Builder | Drag & drop (`@angular/cdk`) |
| 4 | Admin dashboard | Agent metrics, intent stats |

## Phase 6 — Event jobs

| # | Task | Mô tả |
|---|---|---|
| 1 | Price alert | Monitor + notify |
| 2 | Weather disruption | Detect + suggest alternatives |
| 3 | Trip reminders | Check-in, packing |
| 4 | Concierge suggestions | Proactive recommendations |
| 5 | Travel journal | Post-trip content generation |
