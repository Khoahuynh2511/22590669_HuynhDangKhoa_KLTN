# 05 — ItineraryAgent

## Vai trò

Xây lịch trình, modular tour builder, tối ưu theo ngày/buổi.

## Tools

| Tool | Mô tả |
|---|---|
| `search_tour_sessions` | Tìm session tour theo destination/date |
| `ai_build_itinerary` | AI tự xây lịch trình từ constraints |
| `suggest_fill_gaps` | Gợi ý điền buổi trống |
| `save_custom_tour` | Lưu custom tour của user |
| `share_custom_tour` | Chia sẻ tour với người khác |
| `get_weather_forecast_by_city` | Dự báo thời tiết để tối ưu outdoor/indoor |

## Khi nào dùng

- "Lên lịch trình Đà Lạt 3 ngày 2 đêm"
- "Sắp xếp tour theo buổi"
- "Điền mấy buổi trống giúp tôi"
- "Tối ưu lịch trình theo ngân sách"

## Output mẫu

```json
{
  "destination": "Đà Lạt",
  "days": [
    {
      "date": "2026-06-15",
      "morning": {
        "title": "Đồi Cỏ Hồng",
        "price": 150000,
        "reason": "Đẹp nhất vào sáng sớm"
      },
      "afternoon": {},
      "evening": {}
    }
  ],
  "total_price": 1850000,
  "warnings": ["Chiều có khả năng mưa, nên ưu tiên indoor"]
}
```

## Frontend tương ứng

- Component: `tour-builder/` (drag & drop)
- Page: `custom-tour-builder/`
- Service: `tour-builder.service.ts`
