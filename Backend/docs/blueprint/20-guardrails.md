# 20 — Guardrails

## Routing Guardrails

- Admin intent không bao giờ route sang user chat agents
- Payment/booking không dùng LLM quyết định trạng thái cuối
- Tool nào thiếu required slots thì không gọi
- Nếu confidence thấp thì hỏi lại user

## Data Guardrails

- `user_id` auto-inject từ auth, không tin user nhập
- `query_database` SELECT-only
- Payment callback verify signature
- OTP có expiry + retry limit
- Không expose raw provider error ra user

## Agent Guardrails

- Mỗi specialist chỉ thấy tool của nó
- Output phải theo schema
- Supervisor không tự fabricate giá/tình trạng chỗ
- Nếu provider fail thì trả fallback rõ ràng
- max_iterations: 10, timeout: 300s

## Security

- JWT auth trên mọi endpoint (trừ health, public tour list)
- Rate limiting trên chat/stream
- Input validation (Pydantic) trên mọi request
- SQL injection prevention qua Supabase RPC (parameterized)
- XSS prevention qua Angular sanitization
