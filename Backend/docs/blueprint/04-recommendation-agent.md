# 04 — RecommendationAgent

## Vai trò

Gợi ý tour, destination, package dựa trên semantic search + reasoning.

## Tools

| Tool | Mô tả |
|---|---|
| `search_tour_packages` | Hybrid semantic + keyword search tour |
| `search_episodes` | Tìm memory hội thoại Mem0 |
| `recommend_destinations` | Gợi ý điểm đến theo sở thích |
| `generate_tour_ui` | Render tour card UI payload |

## Khi nào dùng

- "Gợi ý tour Đà Lạt"
- "Có tour nào hợp gia đình không?"
- "Tui thích thiên nhiên, đi đâu hợp?"
- "Tìm tour gần giống cái lần trước"

## Trạng thái hiện tại

Agent này đã có trong codebase (`services/agent_services/recommendation_agent.py`), hiện gọi MCP `search_tour_packages` / `search_episodes`.

## Cải tiến cần làm

- Thêm `recommend_destinations` tool
- Tích hợp FalkorDB graph cho personalization sâu hơn
- Output chuẩn hóa theo `ui_payload` format
