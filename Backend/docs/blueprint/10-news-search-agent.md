# 10 — NewsSearchAgent

## Vai trò

Tin tức du lịch, search qua Perplexity.

## Khi nào dùng

- "Tin mới du lịch Đà Lạt"
- "Có lễ hội gì tuần này không?"
- "Tình hình thời tiết / du lịch ở Nhật sao?"

## Tools

| Tool | Mô tả |
|---|---|
| `search_latest_tour_info` | Search tin tức qua Perplexity |
| `perplexity_search` | Raw Perplexity query |

## Trạng thái hiện tại

Agent này đang tách khỏi LangGraph chính trong codebase (`services/search_new_agent/search_news_agent.py`). Hoạt động độc lập, gọi từ frontend qua `ai-chat-panel`.

## Cải tiến

- Chuẩn hóa output theo `ui_payload` type `news_list`
- Tích hợp vào SupervisorGraph qua routing thay vì endpoint riêng
