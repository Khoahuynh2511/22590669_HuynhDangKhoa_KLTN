# 12 — ConciergeAgent & Event Jobs

## Vai trò

Proactive assistant sau khi user đã có trip. Chạy qua event jobs, không block chat request path.

## Event-driven Architecture

```text
Redis Queue / APScheduler
  │
  ├── price_alert_job
  ├── flight_delay_job
  ├── weather_disruption_job
  ├── trip_reminder_job
  ├── concierge_suggestion_job
  └── post_trip_story_job
```

## Event example

```json
{
  "event_type": "weather_disruption",
  "user_id": "uuid",
  "trip_id": "uuid",
  "severity": "medium",
  "payload": {
    "destination": "Đà Lạt",
    "date": "2026-06-15",
    "rain_chance": 0.82
  }
}
```

## Flow

```text
event detected
  -> ConciergeAgent
  -> generate suggestion
  -> save notification
  -> push/email/in-app message
```

## Use cases

- Nhắc check-in
- Cảnh báo mưa → gợi ý đổi activity
- Flight delay handling
- Packing list generation
- Travel journal
- Price alert trigger
- Post-trip review prompt
