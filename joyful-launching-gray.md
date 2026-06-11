# Kế Hoạch: Tích Hợp Trip Planning Vào AI Agent Chat

## Context

Hiện tại project có 2 trang riêng biệt:
- **AI Agent** (`/chat-room`) — Chat tự do, sidebar lịch sử, lưu DB qua `chat_rooms` + `chat_history`
- **Trip Planner** (`/trip-planner`) — Lập kế hoạch 6 bước, state in-memory, **không lưu lịch sử**

**Vấn đề**: User phải chuyển trang, trip planning không lưu lịch sử, UI không đồng nhất, chưa cho khách hàng tùy chỉnh lịch trình.

**Mục tiêu**: Gộp Trip Planner vào AI Agent thành 1 giao diện duy nhất. Lưu lịch sử. Cho khách hàng kéo-thả sắp xếp + thay thế activity hoàn toàn. Cải thiện flow cho mượt hơn.

---

## Tổng quan kiến trúc

```
┌─────────────────────────────────────────────────┐
│  AI Agent Page (/chat-room)                     │
│ ┌──────────┬────────────────────────────────┐   │
│ │ Sidebar  │  Main Chat Area                │   │
│ │          │                                │   │
│ │ 💬Chat   │  [Messages with rich cards]    │   │
│ │ 🗺️Plan   │                                │   │
│ │          │  Itinerary Builder (drag-drop)  │   │
│ │ History  │  Transport Selection           │   │
│ │ list     │  Checkout Summary              │   │
│ │          │                                │   │
│ │          │  [Input Bar]                   │   │
│ └──────────┴────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

---

## Bước 1: Frontend — Shared Models

### MỚI: `Frontend/src/app/shared/models/trip-planning.model.ts`

Tạo shared interfaces:
- `ActivitySlot` — activity data (id, name, price, time_slot, location, category...)
- `ItineraryDay` — morning/afternoon/evening slots
- `TripPlanState` — full state cho trip planning workflow

---

## Bước 2: Frontend — Mở rộng AI Chatbot Component

### Sửa: `Frontend/src/app/components/ai-chatbot/ai-chatbot.component.ts`

#### 2.1 Mở rộng Message interface
```typescript
interface Message {
  // Existing fields...
  content: string;
  isUser: boolean;
  tourPackages?: Tour[];
  mcpUiHtml?: string;
  isError?: boolean;
  
  // NEW: Trip planning fields
  tripStep?: number;
  itineraryData?: Record<string, ItineraryDay>;  // Lịch trình đề xuất
  availableActivities?: ActivitySlot[];           // Pool activities để thay thế
  showItineraryBuilder?: boolean;                 // Hiển thị builder card
  transportData?: { flights?: any[]; trains?: any[] };
  showTransport?: boolean;
  checkoutData?: any;
  showCheckout?: boolean;
}
```

#### 2.2 Mở rộng Conversation interface
```typescript
interface Conversation {
  // Existing fields...
  conversationType: 'general_chat' | 'trip_planning';
}
```

#### 2.3 Thêm state cho trip planning
```typescript
// Trip planning state (tách biệt với chat thường)
currentTripStep = signal(1);
isTripComplete = signal(false);
```

#### 2.4 Thêm `startNewTripPlanning()` method
- Tạo conversation mới với `conversationType: 'trip_planning'`
- Push welcome message vào `this.messages`
- Select conversation đó

#### 2.5 Sửa `sendMessage()` — Routing theo mode
```typescript
async sendMessage() {
  const conversation = this.ensureActiveConversation();
  if (conversation.conversationType === 'trip_planning') {
    await this.sendTripPlanningMessage(message, conversation);
  } else {
    // existing chat logic
  }
}
```

#### 2.6 Thêm `sendTripPlanningMessage()` method
- Tạo room qua ChatRoomService (như existing pattern)
- Gọi `TripPlannerService.sendMessage()` 
- Parse SSE events, cập nhật `Message` object:
  - `start` → set conversationId, navigate URL
  - `token` → append content
  - `step` → update `currentTripStep`
  - `activities` → set `message.itineraryData`, `message.availableActivities`, `message.showItineraryBuilder = true`
  - `flights`/`trains` → set `message.transportData`, `message.showTransport = true`
  - `checkout` → set `message.checkoutData`, `message.showCheckout = true`
  - `done` → mark complete

#### 2.7 Thêm action handlers cho trip planning
- `confirmItinerary(msgIndex)` — gửi "xác nhận"
- `requestItineraryChange(msgIndex, changeDescription)` — yêu cầu thay đổi qua chat
- `selectFlight(msgIndex, flightIndex)` — chọn chuyến bay
- `selectTrain(msgIndex, trainIndex)` — chọn tàu
- `skipTransport(msgIndex)` — bỏ qua
- `proceedToCheckout(msgIndex)` — thanh toán

#### 2.8 Drag-and-Drop & Replace logic
- `onActivityDrop(event, msgIndex, dayKey, fromSlot, toSlot)` — swap 2 activity
- `onActivityReplace(msgIndex, dayKey, slot, newActivity)` — thay thế activity bằng cái khác từ pool
- Sau mỗi thao tác → cập nhật `message.itineraryData` local → gửi message mô tả thay đổi đến backend để sync state
- `recalculatePrice(msgIndex)` — tính lại tổng giá sau khi thay đổi

---

## Bước 3: Frontend — Template Updates

### Sửa: `Frontend/src/app/components/ai-chatbot/ai-chatbot.component.html`

#### 3.1 Sidebar — Thêm nút "Lập kế hoạch"
```html
<div class="sidebar-controls">
  <button class="primary-button" (click)="startNewConversation()">
    <i class="fas fa-plus"></i> Chat mới
  </button>
  <button class="outline-button" (click)="startNewTripPlanning()">
    <i class="fas fa-map-marked-alt"></i> Lập kế hoạch
  </button>
</div>
```

#### 3.2 Sidebar — Icon theo loại conversation
```html
<!-- Mỗi conversation item thêm icon -->
<i class="fas" [class.fa-comment]="conv.conversationType === 'general_chat'"
   [class.fa-map-marked-alt]="conv.conversationType === 'trip_planning'"></i>
```

#### 3.3 Header — Trip planning progress bar (khi active)
Hiển thị 6-step progress bar nhỏ gọn dưới header khi đang ở mode trip planning.

#### 3.4 Message Stream — Itinerary Builder Card với Drag-Drop
Khi `message.showItineraryBuilder === true`, render card với:
- **Mỗi ngày**: 3 slot (sáng/trưa/chiều), mỗi slot là drop zone
- **Drag handle**: User kéo activity từ slot này sang slot khác (cùng ngày hoặc khác ngày)
- **Nút "Thay đổi"** trên mỗi activity → mở dropdown/panel chọn activity khác từ pool `message.availableActivities`
- **Nút "Xóa"** → remove activity khỏi slot
- **Nút "Xác nhận lịch trình"** → gửi xác nhận
- **Tổng giá** tự động cập nhật khi thay đổi

#### 3.5 Message Stream — Transport Selection Card
Khi `message.showTransport === true`, render card với flight/train options (giống existing nhưng style đồng nhất với chat bubble).

#### 3.6 Message Stream — Checkout Card
Khi `message.showCheckout === true`, render checkout summary với nút thanh toán.

---

## Bước 4: Frontend — SCSS cho Trip Planning Cards

### Sửa: `Frontend/src/app/components/ai-chatbot/ai-chatbot.component.scss`

Thêm styles cho:
- `.itinerary-builder-card` — card chứa lịch trình
- `.activity-slot` — mỗi slot trong ngày (drag target)
- `.activity-slot.drag-over` — visual feedback khi kéo qua
- `.activity-slot.dragging` — visual feedback khi đang kéo
- `.transport-card-inline` — transport selection trong chat
- `.checkout-card-inline` — checkout summary trong chat
- `.trip-progress-bar` — progress bar cho 6 bước
- Responsive styles cho mobile

---

## Bước 5: Frontend — Cập nhật TripPlannerService

### Sửa: `Frontend/src/app/services/trip-planner.service.ts`

Thêm method mới:
```typescript
async sendMessageWithRoomId(
  message: string, 
  conversationId: string | null,
  roomId: string
): Promise<ReadableStreamDefaultReader<Uint8Array>>
```
- Giữ nguyên logic gửi đến `/trip-planning/stream`
- Thêm `room_id` vào request body để backend biết room nào cần lưu

---

## Bước 6: Backend — Lưu lịch sử Trip Planning vào Chat History

### Sửa: `Backend/app/v1/api/endpoints/trip_planning.py`

Trong `trip_plan_stream()`:
1. **Nhận thêm `room_id`** từ request body
2. **Nếu chưa có room_id** → tạo room mới qua ChatRoomService với `conversation_type='trip_planning'`
3. **Lưu user message** vào `chat_history` (role='user')
4. **Sau khi process xong** → lưu assistant message vào `chat_history` (role='assistant') kèm metadata (step, itinerary data, flights, etc.)
5. **Cập nhật room title** nếu là message đầu tiên
6. **Return room_id** trong start event

### Sửa: `Backend/app/v1/services/trip_planning/graphs/trip_planning_graph.py`

**Thay in-memory state bằng DB persistence:**
- Thêm method `_load_state_from_db(room_id)` → query `chat_rooms.metadata` hoặc bảng riêng
- Thêm method `_save_state_to_db(room_id, state)` → update vào DB
- Giữ in-memory cache để performance, fallback DB khi cache miss
- Sử dụng existing database connection (psycopg2) để tạo bảng `trip_plan_states` nếu cần

**Cải thiện node logic cho mượt hơn:**

### Sửa: `Backend/app/v1/services/trip_planning/nodes/__init__.py`

**Cải thiện Step 1 (Basic Info):**
- Thay vì hỏi cứng nhắc "cho mình điểm đến và thời gian", cho phép user nói tự do: "mình muốn đi Đà Lạt 3 ngày" hoặc "kế hoạch đi biển"
- Nếu user chỉ nói "đi Đà Lạt" → tự động gợi ý thời gian phổ biến (2-3 ngày) thay vì bắt nhập
- Nếu user nói "đi Đà Lạt với bạn 4 người" → tự extract cả destination, group_size trong 1 bước, skip step 2

**Cải thiện Step 2 (Budget & People):**
- Cho phép user đưa thông tin chung chung: "tiết kiệm thôi", "không quan trọng giá"
- Default: moderate budget nếu user không nói
- Nếu đã có đủ info từ step 1 (user nói nhiều) → tự advance

**Cải thiện Step 3 (Preferences):**
- Hiện tại đã skip được, giữ nguyên nhưng thêm gợi ý: "Bạn thích gì? Ví dụ: biển, núi, ẩm thực..."
- Cho phép chọn nhanh qua quick reply buttons (từ frontend)

**Cải thiện Step 4 (Plan Generation):**
- Thêm support nhận itinerary đã được user sắp xếp lại từ frontend (drag-and-drop result)
- Khi user thay đổi activity → backend nhận itinerary mới, tính lại giá, xác nhận
- Thêm event `itinerary_updated` cho việc update realtime

**Cải thiện Step 5 (Transportation):**
- Nếu không có travel_date → bỏ qua transportation tự động thay vì hỏi
- Default departure: Sài Gòn (SGN/SGO)

---

## Bước 7: Cleanup — Xóa Trip Planner cũ

### Xóa files:
- `Frontend/src/app/pages/trip-planner/trip-planner.component.ts`
- `Frontend/src/app/pages/trip-planner/trip-planner.component.html`
- `Frontend/src/app/pages/trip-planner/trip-planner.component.scss`

### Sửa: `Frontend/src/app/app.routes.ts`
- Xóa route `/trip-planner`

### Sửa: `Frontend/src/app/layouts/header/header.component.html` + `.ts`
- Link "Lập kế hoạch" → navigate `/chat-room` rồi trigger `startNewTripPlanning()`
- Hoặc navigate `/chat-room?mode=planning` và xử lý query param trong AiChatbotComponent

### Sửa: `Frontend/src/app/components/chat-widget/chat-widget.component.ts`
- Cập nhật planner mode → dùng chung logic với AI Agent page
- Hoặc đơn giản: click planner mode → navigate đến `/chat-room?mode=planning`

### Sửa: `Frontend/src/app/app.component.ts` + `.html`
- Nếu có check `isChatPage` cho trip-planner → bỏ check đó (đã xóa route)

---

## Thứ tự triển khai

1. **Bước 1** — Tạo shared models (`trip-planning.model.ts`)
2. **Bước 6** — Backend: thêm lưu chat history cho trip planning
3. **Bước 5** — Frontend: cập nhật TripPlannerService
4. **Bước 2** — Frontend: mở rộng ai-chatbot.component.ts (state, methods)
5. **Bước 3** — Frontend: cập nhật ai-chatbot.component.html (template)
6. **Bước 4** — Frontend: thêm SCSS
7. **Bước 7** — Cleanup: xóa trip-planner cũ, cập nhật routing/header
8. **Test** end-to-end

---

## Files cần sửa đổi

| File | Hành động |
|------|-----------|
| `Frontend/src/app/shared/models/trip-planning.model.ts` | **MỚI** |
| `Frontend/src/app/components/ai-chatbot/ai-chatbot.component.ts` | Sửa — thêm trip planning logic |
| `Frontend/src/app/components/ai-chatbot/ai-chatbot.component.html` | Sửa — thêm UI components |
| `Frontend/src/app/components/ai-chatbot/ai-chatbot.component.scss` | Sửa — thêm styles |
| `Frontend/src/app/services/trip-planner.service.ts` | Sửa — thêm method mới |
| `Backend/app/v1/api/endpoints/trip_planning.py` | Sửa — lưu chat history |
| `Backend/app/v1/services/trip_planning/graphs/trip_planning_graph.py` | Sửa — DB persistence |
| `Backend/app/v1/services/trip_planning/nodes/__init__.py` | Sửa — cải thiện node logic |
| `Frontend/src/app/app.routes.ts` | Sửa — xóa route /trip-planner |
| `Frontend/src/app/layouts/header/header.component.html` | Sửa — cập nhật link |
| `Frontend/src/app/layouts/header/header.component.ts` | Sửa — cập nhật navigation |
| `Frontend/src/app/components/chat-widget/chat-widget.component.ts` | Sửa — cập nhật planner mode |
| `Frontend/src/app/pages/trip-planner/*` | **XÓA** toàn bộ folder |

---

## Cách kiểm tra (Verification)

1. Mở `/chat-room` → thấy 2 nút: "💬 Chat mới" + "🗺️ Lập kế hoạch"
2. Click "🗺️ Lập kế hoạch" → welcome message hiện, progress bar ở header
3. Chat "Đà Lạt 3 ngày" → AI phản hồi mượt, tự extract destination + duration, advance step
4. Chat "4 bạn, ngân sách tiết kiệm" → advance tiếp
5. Đến step 4 → itinerary builder card hiện:
   - Kéo activity từ sáng sang trưa → swap thành công
   - Click "Thay đổi" trên 1 activity → dropdown hiện activity khác → chọn → thay thế
   - Click "Xóa" → bỏ activity khỏi slot
   - Tổng giá tự cập nhật
6. Click "Xác nhận" → tiếp tục step vận chuyển
7. Chọn/bỏ qua vận chuyển → checkout summary hiện
8. Thanh toán → thành công
9. Refresh trang → lịch sử trip planning vẫn còn trong sidebar
10. Click vào conversation cũ → load lại messages + state
11. Sidebar hiện icon khác nhau giữa chat thường và trip planning
12. Link "Lập kế hoạch" ở header → navigate đúng đến AI Agent
