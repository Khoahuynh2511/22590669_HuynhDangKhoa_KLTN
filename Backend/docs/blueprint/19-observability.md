# 19 — Observability & Monitoring

## Agent Run Log

Mỗi agent execution được log:

```json
{
  "run_id": "uuid",
  "user_id": "uuid",
  "chat_room_id": "uuid",
  "intent": "flight_search",
  "selected_agent": "FlightAgent",
  "tools_called": ["get_airport_suggestions", "search_flight_offers"],
  "latency_ms": 4280,
  "success": true,
  "error": null,
  "created_at": "2026-05-27T10:00:00+07:00"
}
```

## Admin Dashboard Metrics

- Intent distribution (pie chart)
- Agent success rate (per agent)
- Tool latency (p50, p95, p99)
- Failed tool calls (count + reason)
- Booking conversion funnel
- Payment failure rate
- Top missing slots
- Hallucination / manual override reports

## Storage

- `agent_runs` table in Supabase
- `intent_stats_daily` aggregated table
- Redis for real-time counters
- Grafana / admin panel for visualization
