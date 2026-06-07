# 16 — Database Blueprint

## Core Tables (đã có)

| Table | Mô tả |
|---|---|
| `users` | User accounts |
| `chat_rooms` | Chat room metadata |
| `chat_history` | Message history |
| `bookings` | Tour bookings |
| `payments` | Payment records |
| `promotions` | Promotion codes |
| `tour_packages` | Tour catalog |
| `tour_sessions` | Tour schedule sessions |
| `custom_tours` | User-created custom tours |
| `custom_tour_sessions` | Sessions in custom tours |
| `session_reviews` | Reviews per session |
| `session_conflicts` | Scheduling conflicts |

## New Domain Tables (cần thêm)

| Table | Mô tả |
|---|---|
| `flight_bookings` | Vé máy bay đã đặt |
| `hotel_bookings` | Phòng khách sạn đã đặt |
| `transport_bookings` | Vé xe/tàu đã đặt |
| `price_alerts` | Cảnh báo giá user đặt |
| `packing_lists` | Danh sách đồ mang theo |
| `group_trips` | Trip nhóm |
| `group_trip_members` | Thành viên trip nhóm |
| `travel_buddy_profiles` | Profile tìm bạn đồng hành |

## Observability / Admin Tables (cần thêm)

| Table | Mô tả |
|---|---|
| `agent_configs` | Config cho từng agent |
| `mcp_servers` | Registry MCP servers |
| `agent_runs` | Log mỗi agent execution |
| `intent_stats_daily` | Thống kê intent theo ngày |
| `admin_audit_log` | Audit log admin actions |
