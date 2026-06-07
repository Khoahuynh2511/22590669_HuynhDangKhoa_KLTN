# Kế Hoạch Thiết Kế "Plan Mode" (Trip Planning) - Static Workflow

## 1. Mục Tiêu (Objective)
Tạo ra một chế độ **"Plan Mode"** đặc biệt chuyên dùng cho việc lên kế hoạch du lịch (Trip Planning). Thay vì để AI tự do suy luận và dùng quá nhiều tool/subagent gây phình to context và tốn thời gian, luồng mới sẽ tách biệt hoàn toàn AI lên kế hoạch ra riêng và chạy trên một **Static Workflow** cố định.

## 2. Lợi Ích Của Cách Tiếp Cận Mới
*   **Decoupling (Tách biệt logic):** Isolate AI lên plan với AI Chat thông thường. Tránh trường hợp general AI nhồi nhét quá nhiều instruction, subagents, tools khiến prompt bị over-context.
*   **Predictable (Chuẩn xác, dễ đoán):** Hoạt động theo mô hình State Machine (Finite State Machine). AI không tự quyết định bước đi tiếp theo. Mỗi bước trong quy trình sẽ chịu trách nhiệm hỏi user các thông tin còn thiếu.
*   **Performance:** Giảm bớt token dư thừa, chạy nhanh hơn, và không bị loop (lặp vô tận) do agent tự xử lý sai.
*   **Trải nghiệm người dùng:** Giao tiếp thân thiện, rõ ràng (Step-by-step wizard).

## 3. Kiến Trúc Static Workflow
Dưới đây là sơ đồ các bước (Steps) của workflow tĩnh, được thiết kế là một quy trình end-to-end từ lên lịch trình đến thanh toán:

### Bước 1: Thu thập Thông tin Cơ bản (Basic Info)
*   **Nhiệm vụ:** Hỏi user về Điểm đến (Destination) và Thời gian (Duration / Dates).
*   **Action:** Trình bày câu hỏi. Nắm bắt thực thể (Extract Entities) từ câu trả lời của user.
*   **Chuyển bước:** Nếu đã có đủ Địa điểm + Thời gian -> Sang Bước 2. Nếu thiếu -> Tiếp tục hỏi vòng lặp trong Bước 1.

### Bước 2: Đối tượng & Ngân sách (Participants & Budget)
*   **Nhiệm vụ:** Đi bao nhiêu người? (Gia đình, bạn bè, cặp đôi, hay đi một mình), và Ngân sách ước tính (Cao cấp, Tiết kiệm, Trung bình).
*   **Action:** Hỏi và trích xuất dữ liệu. 
*   **Chuyển bước:** Có đủ Budget và Demographic -> Sang Bước 3.

### Bước 3: Sở thích & Yêu cầu Đặc biệt (Preferences & Constraints)
*   **Nhiệm vụ:** Nhu cầu đặc biệt là gì? (Ví dụ: Thích đi bảo tàng, phiêu lưu kỳ thú, thư giãn ở bãi biển, cần phòng cho trẻ em,...).
*   **Action:** Hỏi các constraint (nếu user không có, có thể skip).
*   **Chuyển bước:** Lấy đủ sở thích -> Sang Bước 4.

### Bước 4: Khởi tạo Plan & Đề xuất Tour (Plan Generation)
*   **Nhiệm vụ:** Tổng hợp Dữ liệu từ Bước 1 -> 3. Gọi LLM và kết hợp tool `TourPackageSearchService` từ MCP để tìm các Tour sát nhất.
*   **Action:** Vạch ra lộ trình đi chi tiết và list các Tour gợi ý (kèm `package_id`).
*   **Chuyển bước:** Sau khi user chọn lịch trình/Tour -> Sang Bước 5.

### Bước 5: Đặt Phương Tiện Di Chuyển (Transportation)
*   **Nhiệm vụ:** Hỏi user: "Để phục vụ lịch trình trên, bạn có muốn tìm luôn chuyến bay/tàu hỏa không?"
*   **Action:** Nếu user đồng ý -> Tự động dùng điểm đến/thời gian ở Bước 1 để gọi tool `FlightService` hoặc `TrainService` từ MCP, gợi ý chuyến bay.
*   **Chuyển bước:** Sau khi user chọn chuyến bay (hoặc skip) -> Sang Bước 6.

### Bước 6: Chốt Booking & Thanh Toán (Checkout)
*   **Nhiệm vụ:** Gom toàn bộ Tour + Phương tiện di chuyển đã chọn.
*   **Action:** Gọi API thanh toán/đặt chỗ từ hệ thống.
*   **Output:** Chốt đơn thành công và lưu vào Database.

## 4. Gợi Ý Implementation (Ví dụ với LangGraph)
Vì hệ thống đang được vận hành bởi AI/Agents, luồng Static có thể thiết kế rất dễ với LangGraph dưới dạng StateGraph tuyến tính:

```python
from langgraph.graph import StateGraph, END

# Định nghĩa các node tĩnh (không sử dụng Agent/Tools tự do)
workflow = StateGraph(TripPlanState)

workflow.add_node("ask_destination_date", ask_destination_date_node)
workflow.add_node("ask_budget_people", ask_budget_people_node)
workflow.add_node("ask_preferences", ask_preferences_node)
workflow.add_node("generate_plan_tours", generate_plan_tours_node)
workflow.add_node("ask_transportation", ask_transportation_node)
workflow.add_node("checkout_payment", checkout_payment_node)

# Định nghĩa các cạnh nối luồng tuyến tính
workflow.add_conditional_edges("ask_destination_date", condition_has_dest_date)
workflow.add_conditional_edges("ask_budget_people", condition_has_budget)
workflow.add_conditional_edges("ask_preferences", condition_has_prefs)
workflow.add_conditional_edges("generate_plan_tours", condition_plan_accepted)
workflow.add_conditional_edges("ask_transportation", condition_transport_selected)
workflow.add_edge("checkout_payment", END)

workflow.set_entry_point("ask_destination_date")
app = workflow.compile()
```

## 5. Next Steps
1. Khởi tạo schema cho `TripPlanState` (pydantic model) để lưu metadata từ mỗi bước.
2. Tạo các Prompts độc lập để hỏi/trích xuất thông tin cho mỗi bước mà không cần cấp Tool tự do.
3. Tạo endpoint API để phục vụ riêng cho Frontend "Plan Mode".
4. Tách biệt `plan_agent.py` khỏi `agent.py` hoặc `admin_agent.yaml`.