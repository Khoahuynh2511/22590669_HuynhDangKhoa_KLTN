# 06 — FlightAgent

## Vai trò

Xử lý tìm kiếm, so sánh giá, và đặt vé máy bay.

## Tools

| Tool | Mô tả |
|---|---|
| `get_airport_suggestions` | Gợi ý sân bay theo keyword |
| `search_flights` | Tra cứu chuyến bay (AviationStack) — read-only |
| `search_flight_offers` | Tìm offer + giá (Amadeus) |
| `book_flight` | Đặt vé (Amadeus) |
| `predict_flight_price` | Dự đoán giá tương lai |
| `set_price_alert` | Đặt cảnh báo giá |

## Khi nào dùng

- "Tìm vé máy bay Hà Nội đi Đà Lạt"
- "Có chuyến nào rẻ không?"
- "Book chuyến thứ 2"
- "Giá này nên mua chưa?"

## Provider strategy

| Provider | Vai trò |
|---|---|
| AviationStack (hiện tại) | Search/schedule/status realtime |
| Amadeus Self-Service | Offer + booking + multi-city + price |

Giữ AviationStack cho search/schedule, dùng Amadeus cho offer + book.

## Trạng thái hiện tại

Codebase đã có `search_flights` read-only qua AviationStack trong `Backend/app/v1/mcp/src/tools/flight_tools.py`. Còn thiếu: gợi ý sân bay, multi-city, đặt vé, bảng `flight_bookings`.

## Nguyên tắc

- FlightAgent không tự xử lý thanh toán
- Khi user chọn vé → trả payload sang `BookingPaymentFlow`
- Không fabricate giá hoặc tình trạng chỗ
