# 18 — Frontend Blueprint

## Component Structure

```text
Frontend/src/app/
├── components/
│   ├── ai-chatbot/              (existing)
│   ├── ai-chat-panel/           (existing)
│   ├── admin-chatbot/           (existing)
│   ├── flight-search/           (new)
│   ├── flight-card/             (new)
│   ├── hotel-search/            (new)
│   ├── hotel-card/              (new)
│   ├── transport-search/        (new)
│   ├── tour-builder/            (new — drag & drop)
│   ├── itinerary-card/          (new)
│   └── payment-button/          (new)
├── pages/
│   ├── home/                    (existing)
│   ├── tours/                   (existing)
│   ├── flights/                 (new)
│   ├── hotels/                  (new)
│   ├── transport/               (new)
│   ├── custom-tour-builder/     (new)
│   ├── booking-detail/          (new)
│   └── admin/                   (existing)
└── services/
    ├── chat.service.ts          (existing)
    ├── flight.service.ts        (new)
    ├── hotel.service.ts         (new)
    ├── transport.service.ts     (new)
    ├── tour-builder.service.ts  (new)
    ├── booking.service.ts       (existing)
    └── payment.service.ts       (existing)
```

## UI Payload Standard

Mỗi agent trả thêm `ui_payload` để frontend render card:

```json
{
  "final_response": "Mình tìm được 3 chuyến bay phù hợp...",
  "ui_payload": {
    "type": "flight_options",
    "items": [...],
    "actions": [
      {
        "label": "Chọn chuyến này",
        "action": "select_flight",
        "payload": { "offer_id": "offer_1" }
      }
    ]
  }
}
```

## UI Payload Types

| Type | Agent source |
|---|---|
| `tour_cards` | RecommendationAgent |
| `flight_options` | FlightAgent |
| `hotel_options` | HotelAgent |
| `transport_options` | TransportAgent |
| `itinerary_plan` | ItineraryAgent |
| `booking_summary` | BookingPaymentFlow |
| `payment_button` | BookingPaymentFlow |
| `otp_form` | BookingPaymentFlow |
| `admin_table` | AdminGraph |
| `news_list` | NewsSearchAgent |
