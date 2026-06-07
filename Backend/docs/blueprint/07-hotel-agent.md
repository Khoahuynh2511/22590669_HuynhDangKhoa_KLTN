# 07 — HotelAgent

## Vai trò

Tìm, so sánh, đặt khách sạn.

## Tools

| Tool | Mô tả |
|---|---|
| `search_hotels` | Tìm khách sạn theo destination/date/guests |
| `get_hotel_details` | Chi tiết khách sạn (phòng, tiện ích, ảnh) |
| `get_hotel_reviews` | Đánh giá từ khách trước |
| `compare_hotels` | So sánh nhiều khách sạn |
| `book_hotel` | Đặt phòng |

## Khi nào dùng

- "Tìm khách sạn Đà Lạt 2 đêm"
- "So sánh 3 khách sạn này"
- "Có khách sạn gần chợ đêm không?"
- "Book phòng deluxe"

## Trạng thái hiện tại

Frontend đang mock data. Chưa có provider thực. Cần chọn provider (Booking.com API, Agoda, hoặc internal catalog).

## Nguyên tắc

- HotelAgent trả về options + hotel selection payload
- Booking/payment đẩy qua `BookingPaymentFlow`
- Không tự confirm booking
