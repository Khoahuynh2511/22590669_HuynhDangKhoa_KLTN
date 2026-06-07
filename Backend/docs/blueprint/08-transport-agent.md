# 08 — TransportAgent

## Vai trò

Vé xe khách, limousine, tàu, ferry.

## Tools

| Tool | Mô tả |
|---|---|
| `search_transport` | Tìm chuyến xe/tàu theo route/date |
| `get_route_details` | Chi tiết tuyến (giờ, hãng, loại xe) |
| `book_transport_ticket` | Đặt vé |

## Khi nào dùng

- "Tìm xe Sài Gòn đi Đà Lạt"
- "Có limousine không?"
- "Book 2 vé chuyến 22h"
- "Tàu đi Nha Trang giờ nào?"

## Provider candidates

| Provider | Ưu điểm |
|---|---|
| 12Go Asia | API sẵn, nhiều route ĐNA |
| Baolau | Focus Vietnam, có booking API |
| Internal catalog | Tự quản lý, không phụ thuộc |

## Trạng thái hiện tại

Chưa có trong codebase. Cần implement từ đầu.

## Nguyên tắc

- Booking/payment đẩy qua `BookingPaymentFlow`
- Không tự xử lý thanh toán
