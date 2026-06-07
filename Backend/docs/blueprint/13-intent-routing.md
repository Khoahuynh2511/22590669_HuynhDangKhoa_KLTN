# 13 — Intent Routing

## Routing Table

| Intent | Route to |
|---|---|
| `destination_recommendation` | RecommendationAgent |
| `tour_search` | RecommendationAgent |
| `itinerary_build` | ItineraryAgent |
| `custom_tour_builder` | ItineraryAgent |
| `flight_search` | FlightAgent |
| `flight_booking` | FlightAgent → BookingPaymentFlow |
| `hotel_search` | HotelAgent |
| `hotel_booking` | HotelAgent → BookingPaymentFlow |
| `transport_search` | TransportAgent |
| `transport_booking` | TransportAgent → BookingPaymentFlow |
| `tour_booking` | RecommendationAgent → BookingPaymentFlow |
| `payment` | BookingPaymentFlow |
| `otp` | BookingPaymentFlow |
| `promotion` | BookingPaymentFlow |
| `travel_news` | NewsSearchAgent |
| `admin_query` | AdminGraph |
| `packing_list` | ConciergeAgent / ItineraryAgent |
| `price_alert` | EventJob + FlightAgent |
| `general_chat` | SupervisorGraph reply directly |

## Routing Guardrails

- Admin intent không bao giờ route sang user chat agents
- Payment/booking không dùng LLM quyết định trạng thái cuối
- Tool nào thiếu required slots thì không gọi
- Nếu confidence thấp thì hỏi lại user
- Mỗi specialist chỉ thấy tool của nó
