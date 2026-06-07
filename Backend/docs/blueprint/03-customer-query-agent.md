# 03 — CustomerQueryAgent

## Vai trò

NLU + slot extraction. Hiểu user muốn gì, xác định intent, kiểm tra thiếu thông tin.

## Output Schema

```json
{
  "intent": "flight_search | hotel_search | build_itinerary | book_tour | payment | news | admin | general",
  "confidence": 0.91,
  "slots": {
    "destination": "Đà Lạt",
    "origin": "Hà Nội",
    "start_date": "2026-06-15",
    "end_date": "2026-06-18",
    "adults": 2,
    "children": 0,
    "budget": 5000000
  },
  "missing_slots": [],
  "risk_level": "normal",
  "should_use_workflow": false
}
```

## Xử lý thiếu thông tin

```text
User: "Tìm khách sạn Đà Lạt"
CustomerQueryAgent:
  intent = hotel_search
  missing_slots = [checkin_date, checkout_date, guests]
Supervisor:
  hỏi lại user trước, chưa gọi HotelAgent
```

## Nguyên tắc

- Nếu confidence thấp → hỏi lại user
- Nếu thiếu required slots → không route sang specialist
- Admin intent không bao giờ route sang user chat agents
- Tool nào thiếu required slots thì không gọi
