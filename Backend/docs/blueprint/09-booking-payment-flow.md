# 09 — BookingPaymentFlow

## Vai trò

State machine cứng cho booking/payment/OTP. **Không phải LLM agent tự do.**

## Luồng

```text
User chọn option
  → validate_selection
  → collect_passenger_info
  → create_booking (draft)
  → send_otp
  → wait_user_otp
  → verify_otp
  → create_payment
  → return payment_url / button
  → payment_callback (VNPay)
  → confirm_booking
```

## Tools

| Tool | Mô tả |
|---|---|
| `create_booking` | Tạo booking tour + gửi OTP email |
| `update_booking` | Cập nhật số người / yêu cầu đặc biệt |
| `verify_otp_and_confirm_booking` | Xác thực OTP, chuyển status |
| `resend_otp` | Gửi lại OTP qua email |
| `delete_booking` | Hủy booking (soft), restore slot |
| `create_payment` | Tạo payment + URL VNPay |
| `generate_payment_ui` | HTML nút thanh toán |
| `apply_promotion_code` | Áp mã KM cho booking pending |

## BookingState

```python
class BookingState(TypedDict):
    booking_type: Literal["tour", "flight", "hotel", "transport"]
    user_id: str
    selected_item: dict
    passengers: list[dict]
    contact: dict
    booking_id: str | None
    otp_status: Literal["not_sent", "sent", "verified"]
    payment_id: str | None
    payment_url: str | None
    status: Literal["draft", "pending_otp", "pending_payment", "confirmed", "cancelled"]
```

## Rules quan trọng

- Không charge tiền nếu booking chưa hợp lệ
- Không confirm nếu OTP chưa verified
- Không gọi payment nhiều lần nếu đã có payment_id active
- Mọi state transition phải idempotent
- Có audit log cho booking/payment/admin action
- user_id auto-inject từ auth, không tin user nhập
- Payment callback verify signature
- OTP có expiry + retry limit
