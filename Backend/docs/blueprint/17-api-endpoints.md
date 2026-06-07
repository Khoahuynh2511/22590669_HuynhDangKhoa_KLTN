# 17 — API Blueprint

## Chat

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/api/v1/chat/stream` | SSE chat stream |
| POST | `/api/v1/chat/message` | Single message |
| GET | `/api/v1/chat/rooms` | List chat rooms |
| GET | `/api/v1/chat/rooms/{room_id}/history` | Room history |

## Flights (new)

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/api/v1/flights/offers` | Search flight offers |
| GET | `/api/v1/flights/airports` | Airport suggestions |
| POST | `/api/v1/flights/book` | Book flight |

## Hotels (new)

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/api/v1/hotels/search` | Search hotels |
| GET | `/api/v1/hotels/{hotel_id}` | Hotel details |
| POST | `/api/v1/hotels/book` | Book hotel |

## Transport (new)

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/api/v1/transport/search` | Search transport |
| POST | `/api/v1/transport/book` | Book transport |

## Custom Tours (new)

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/api/v1/tour-sessions` | List tour sessions |
| POST | `/api/v1/custom-tours` | Create custom tour |
| GET | `/api/v1/custom-tours/{id}` | Get custom tour |
| POST | `/api/v1/custom-tours/{id}/share` | Share custom tour |

## Transactions (existing, chuẩn hóa)

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/api/v1/bookings` | Create booking |
| PATCH | `/api/v1/bookings/{id}` | Update booking |
| POST | `/api/v1/bookings/{id}/otp/verify` | Verify OTP |
| POST | `/api/v1/bookings/{id}/otp/resend` | Resend OTP |
| POST | `/api/v1/payments/create` | Create payment |
| GET | `/api/v1/payments/vnpay-return` | VNPay callback |

## Admin (new)

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/api/v1/admin/agents` | List agent configs |
| PATCH | `/api/v1/admin/agents/{agent_id}` | Update agent config |
| GET | `/api/v1/admin/agent-runs` | Agent run logs |
| GET | `/api/v1/admin/intent-stats` | Intent statistics |
| GET | `/api/v1/admin/mcp-tools` | MCP tool registry |
