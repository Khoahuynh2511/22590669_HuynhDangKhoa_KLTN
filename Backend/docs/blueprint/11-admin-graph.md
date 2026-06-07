# 11 — AdminGraph

## Vai trò

Admin SQL, dashboard, thống kê, config. Tách riêng khỏi user chat.

## Luồng

```text
Admin UI -> admin-chatbot -> AdminGraph -> query_database
```

## Tools

| Tool | Mô tả |
|---|---|
| `query_database` | SELECT-only qua Supabase RPC |

## Trạng thái hiện tại

Đã có trong codebase (`services/agent_support_admin/graph.py`). Loop `admin_llm <-> admin_tools`.

## Nguyên tắc

- Admin intent không bao giờ route sang user chat agents
- query_database chỉ SELECT, không INSERT/UPDATE/DELETE
- Giữ riêng, không cho chung vào user chat
- Output nên theo `ui_payload` type `admin_table`

## Cải tiến

- Thêm dashboard metrics: intent distribution, agent success rate, tool latency
- Agent config management qua admin UI
- Audit log cho admin actions
