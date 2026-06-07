# AI Agent & Innovative Features — Development Guide

> Target: Developer onboarding guide for extending the AI Agent ecosystem
> covering flights, hotels, bus tickets, modular tour builder, and next-gen
> travel features.
>
> Revision: 2.0 — đã đối chiếu với codebase thực tế (Backend FastAPI + LangGraph + FastMCP, Frontend Angular 19) và bổ sung mẫu thiết kế multi-agent từ Azure AI Travel Agents.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Current Agent System](#2-current-agent-system)
3. [Phase A — Agent cho Vé Máy Bay (Flight Agent)](#3-phase-a--flight-agent)
4. [Phase B — Agent cho Khách Sạn (Hotel Agent)](#4-phase-b--hotel-agent)
5. [Phase C — Agent cho Vé Xe (Transport Agent)](#5-phase-c--transport-agent)
6. [Phase D — Modular Tour Builder (Drag & Drop)](#6-phase-d--modular-tour-builder)
7. [Phase E — Các tính năng AI độc đáo](#7-phase-e--innovative-ai-features)
8. [Database Schema Extensions](#8-database-schema-extensions)
9. [MCP Tools Extension Guide](#9-mcp-tools-extension-guide)
10. [Frontend Component Guide](#10-frontend-component-guide)
11. [Admin Panel — CRUD cho tất cả features mới](#11-admin-panel--crud-cho-tất-cả-features-mới)
12. [Internal Catalog System (tự quản lý data, không phụ thuộc external)](#12-internal-catalog-system)
13. [Testing Strategy](#13-testing-strategy)
14. [Azure AI Travel Agents Pattern Integration](#14-azure-ai-travel-agents-pattern-integration)

---

## 1. Architecture Overview

```
+-----------------------------------------------------------+
|                    FRONTEND (Angular 19)                  |
|  ai-chatbot  |  ai-chat-panel  |  admin-chatbot  | pages  |
|  (tour AI)      (news agent)      (admin SQL)            |
|                         |                                 |
|                         | SSE (/chat/stream) + REST       |
+-------------------------+---------------------------------+
|                  BACKEND (FastAPI, main.py)               |
|                                                           |
|  /api/v1/* -> Routers (chat, bookings, payments, ...)     |
|                                                           |
|  +-----------------------------------------------------+  |
|  |        LangGraph Multi-Agent System                 |  |
|  |                                                     |  |
|  |  SupervisorGraph (user chat)                        |  |
|  |  -> chat_llm <-> chat_tools <-> recommendation_agent|  |
|  |                                                     |  |
|  |  AdminGraph     (admin SQL agent)                   |  |
|  |  -> admin_llm <-> admin_tools (query_database)      |  |
|  |                                                     |  |
|  |  NewsSearchAgent (news / Perplexity)                |  |
|  +----------------------+------------------------------+  |
|                         | StructuredTool (LangChain)      |
|                         |  -> fastmcp.Client              |
|                         v                                 |
|  /mcp (FastMCP server, composed):                         |
|     booking_tools | tour_search_tools | flight_tools      |
|     weather_tools | search_personalization                |
|                                                           |
|  External / Storage:                                      |
|     Supabase (pgvector) | Redis | Mem0 | FalkorDB |       |
|     OpenWeatherMap | AviationStack | Perplexity |         |
|     SendGrid | Cloudinary | VNPay                         |
+-----------------------------------------------------------+
```

### Current tech stack (đã đối chiếu `pyproject.toml` + `package.json`)

| Layer | Technology | Location | Trạng thái |
|---|---|---|---|
| Frontend | Angular 19, PrimeNG 19, TailwindCSS | `Frontend/` | Đang dùng |
| Frontend (chưa dùng) | `three`, `ngx-owl-carousel-o` | `package.json` | Đã cài, chưa import |
| Frontend (cần cài thêm) | `@angular/cdk` (drag-drop), `chart.js` | — | Chưa cài, cần `npm i` |
| Backend | FastAPI, LangGraph, LangChain, FastMCP | `Backend/app/v1/` | Đang dùng |
| AI/LLM | OpenAI `gpt-5-mini` (qua LangChain), `text-embedding-3-small` | `agent.yaml`, `tour_package_service.py` | Đang dùng |
| Vector / Memory | Supabase `pgvector` + Mem0 + FalkorDB/Graphiti | `mcp/src/core/` | Đang dùng |
| Vector (chưa có) | Qdrant | — | Không có trong code, không cần |
| Tools framework | FastMCP server (`@mcp.tool()`) | `Backend/app/v1/mcp/` | Đang dùng |
| Payment | VNPay | `services/vnpay_service.py` | Đang dùng |
| Auth | JWT + Google OAuth | `services/auth_service.py`, `google_oauth_service.py` | Đang dùng |
| Flight provider hiện tại | AviationStack | `mcp/src/tools/flight_tools.py` | Tra cứu read-only, **chưa** book |
| Hotel provider | (chưa có) | — | Frontend đang mock, cần chọn provider |
| Transport provider | (chưa có) | — | Cần chọn provider |

---

## 2. Current Agent System

Codebase đang vận hành **bốn agent độc lập** phối hợp qua LangGraph + FastMCP. Đây là trạng thái thực tế đã đối chiếu trong `Backend/app/v1/services/`.

### 2.1 Bốn agent thực tế

| Agent | Vị trí code | Vai trò |
|---|---|---|
| `SupervisorGraph` (chat user) | `services/agent_services/graphs/supervisor_graph.py` | Vòng lặp `chat_llm <-> chat_tools`, có thể chuyển sang `recommendation_agent` qua tool `request_recommendation` |
| `RecommendationAgent` | `services/agent_services/recommendation_agent.py` | Semantic search tour + reasoning, gọi MCP `search_tour_packages` / `search_episodes` |
| `AdminGraph` | `services/agent_support_admin/graph.py` | Loop `admin_llm <-> admin_tools`, tool duy nhất `query_database` (SELECT-only qua Supabase RPC) |
| `NewsSearchAgent` | `services/search_new_agent/search_news_agent.py` | Search tin tức du lịch qua Perplexity, tách khỏi LangGraph chính |

### 2.2 Sơ đồ workflow user chat (SupervisorGraph)

```
START -> chat_llm
           |
           +-- tool_calls? --+--> chat_tools (FastMCP) --> chat_llm (loop tối đa 10)
           |                 |
           |                 +--> request_recommendation? --> recommendation_agent --> chat_llm
           |
           +-- no tools --> END
```

`max_iterations: 10`, `timeout: 300s`, memory dùng LangGraph `MemorySaver` + persist Supabase `chat_history` / `chat_rooms`.

### 2.3 MCP tools đang chạy (rà soát `mcp/src/tools/`)

Tất cả tool đăng ký qua hàm `register_*_tools(mcp)` trong `__init__.py`, decorator chuẩn là `@mcp.tool()`.

| Tool | File | Mô tả |
|---|---|---|
| `create_booking` | `booking_tools.py` | Tạo booking tour + gửi OTP email |
| `get_user_bookings` | `booking_tools.py` | Lấy bookings theo `user_id` (auto-inject) |
| `update_booking` | `booking_tools.py` | Cập nhật số người / yêu cầu đặc biệt |
| `verify_otp_and_confirm_booking` | `booking_tools.py` | Xác thực OTP, chuyển status `pending` |
| `resend_otp` | `booking_tools.py` | Gửi lại OTP qua email |
| `delete_booking` | `booking_tools.py` | Hủy booking (soft), restore slot |
| `create_payment` | `booking_tools.py` | Tạo payment + URL VNPay |
| `generate_payment_ui` | `booking_tools.py` | HTML nút thanh toán |
| `apply_promotion_code` | `booking_tools.py` | Áp mã KM cho booking `pending` |
| `search_tour_packages` | `tour_search_tools.py` | Hybrid semantic + keyword search tour |
| `search_episodes` | `search_personalization.py` | Tìm memory hội thoại Mem0 |
| `get_current_temperature_by_city` | `weather_tools.py` | Thời tiết hiện tại (OpenWeatherMap) |
| `get_weather_forecast_by_city` | `weather_tools.py` | Dự báo 1–5 ngày |
| `search_flights` | `flight_tools.py` | Tra cứu chuyến bay (AviationStack), read-only |

LangChain `StructuredTool` wrapper trong `mcp_tools.py` còn expose thêm:
`request_recommendation`, `search_latest_tour_info`, `generate_tour_ui`, alias `get_current_temperature` / `get_weather_forecast`.

Admin agent có tool riêng `query_database` (LangChain `@tool`) ngoài FastMCP server.

### 2.4 Cách thêm tool mới (theo pattern thực tế)

1. Tạo file mới `Backend/app/v1/mcp/src/tools/<feature>_tools.py`.
2. Khai báo hàm `register_<feature>_tools(mcp: FastMCP)` chứa các `@mcp.tool()`.
3. Import và gọi `register_<feature>_tools(mcp)` trong `mcp/src/tools/__init__.py::register_all_tools`.
4. Nếu tool thuộc domain chuyên biệt và muốn tách process, thêm sub-server FastMCP trong `mcp/server.py` rồi `import_server` vào main.
5. Cập nhật `Backend/agent.yaml` block `tool_calling.available_tools` để LLM biết.

---

## 3. Phase A — Flight Agent (Agent Vé Máy Bay)

### 3.0 Trạng thái hiện tại

Codebase **đã có** `search_flights` (read-only) chạy trên **AviationStack** trong `Backend/app/v1/mcp/src/tools/flight_tools.py`. Còn thiếu: gợi ý sân bay, multi-city, **đặt vé** (Aviationstack không có booking) và bảng `flight_bookings`.

Có hai hướng nâng cấp khi muốn book vé:

| Provider | Ưu điểm | Nhược điểm |
|---|---|---|
| **AviationStack** (hiện tại) | Free tier, schedule + status realtime | Không có booking, không có price |
| **Amadeus Self-Service** | Có offer + booking + multi-city + price | Quota free thấp, phải KYC khi production |
| **Skyscanner / Kiwi.com** | Aggregation, so giá nhiều hãng | Cần đăng ký partner |

Khuyến nghị triển khai theo lớp: giữ AviationStack cho **search/schedule**, dùng Amadeus cho **offer + book**. Khi internal catalog đã đầy đủ (Section 12) thì chuyển dần sang internal.

### 3.1 Overview

Agent cho phép user tìm kiếm, so sánh giá, và đặt vé máy bay qua hội thoại AI.

**User flow:**
```
User: "Tim ve may bay Ha Noi -> Da Lat ngay 15/06, 2 nguoi lon"
  -> AI goi search_flights tool (AviationStack)
  -> Hien thi danh sach chuyen bay dang card
  -> User chon chuyen -> AI goi book_flight tool (Amadeus / internal)
  -> Tao flight_bookings + thanh toan VNPay
```

### 3.2 External API — Amadeus cho phần booking

```python
# Backend/app/v1/services/flight_booking_service.py
# Lop nay BO SUNG cho FlightService da co (Aviationstack search).
# FlightService trong mcp/src/tools/flight_tools.py van giu nguyen vai tro
# search-by-route real-time.

from amadeus import Client, Location
from app.v1.core.config import settings


class FlightBookingService:
    """Amadeus booking flow (offer search + price + create order)."""

    def __init__(self) -> None:
        self.client = Client(
            client_id=settings.AMADEUS_CLIENT_ID,
            client_secret=settings.AMADEUS_CLIENT_SECRET,
            hostname="test",
        )

    async def search_offers(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        adults: int = 1,
        children: int = 0,
        travel_class: str | None = None,
        max_price: int | None = None,
    ) -> list[dict]:
        response = self.client.shopping.flight_offers_search.get(
            originLocationCode=origin,
            destinationLocationCode=destination,
            departureDate=departure_date,
            adults=adults,
            children=children,
            travelClass=travel_class,
            maxPrice=max_price,
            currencyCode="VND",
            nonStop="false",
        )
        return self._parse_offers(response.data)

    async def get_airport_suggestions(self, keyword: str) -> list[dict]:
        response = self.client.reference_data.locations.get(
            keyword=keyword, subType=Location.AIRPORT,
        )
        return [
            {"code": loc["iataCode"], "name": loc["name"]}
            for loc in response.data
        ]

    def _parse_offers(self, data: list[dict]) -> list[dict]:
        return [
            {
                "offer_id": offer["id"],
                "price": float(offer["price"]["total"]),
                "currency": offer["price"]["currency"],
                "itineraries": offer["itineraries"],
                "validating_airline": offer.get("validatingAirlineCodes", []),
                "seats_available": offer.get("numberOfBookableSeats", 0),
                "source": "amadeus",
            }
            for offer in data
        ]
```

### 3.3 MCP Tools — đăng ký theo pattern thực tế

`flight_tools.py` đã theo pattern `register_flight_tools(mcp)`; bổ sung các tool mới trong **cùng file** (tránh đụng tới các module khác).

```python
# Backend/app/v1/mcp/src/tools/flight_tools.py (mo rong)

from fastmcp import FastMCP

from app.v1.services.flight_booking_service import FlightBookingService


def register_flight_tools(mcp: FastMCP) -> None:
    flight_service = FlightService()
    booking_service = FlightBookingService()

    @mcp.tool()
    async def search_flights(
        departure_iata: str,
        arrival_iata: str,
        limit: int = 5,
    ) -> str:
        """Search realtime flights between two airports (Aviationstack)."""
        ...

    @mcp.tool()
    async def search_flight_offers(
        origin: str,
        destination: str,
        departure_date: str,
        adults: int = 1,
        children: int = 0,
        travel_class: str | None = None,
        max_price: int | None = None,
    ) -> str:
        """Search bookable flight offers with price (Amadeus)."""
        results = await booking_service.search_offers(
            origin, destination, departure_date,
            adults, children, travel_class, max_price,
        )
        return json.dumps(results, ensure_ascii=False)

    @mcp.tool()
    async def get_airport_suggestions(keyword: str) -> str:
        """Suggest IATA airports by city / name keyword."""
        results = await booking_service.get_airport_suggestions(keyword)
        return json.dumps(results, ensure_ascii=False)

    @mcp.tool()
    async def book_flight(
        user_id: str,
        offer_id: str,
        passengers: list[dict],
        contact_email: str,
        contact_phone: str,
    ) -> str:
        """Create a flight booking from an Amadeus offer id."""
        ...
```

### 3.4 Backend API Endpoints

Tạo `Backend/app/v1/api/endpoints/flights.py` (tên router khớp prefix `/flights`):

```python
from fastapi import APIRouter, Depends, Query

from app.v1.core.dependencies import get_current_user
from app.v1.services.flight_booking_service import FlightBookingService
from app.v1.schema.flight_schema import FlightBookingRequest

router = APIRouter(prefix="/flights", tags=["Flights"])
booking_service = FlightBookingService()


@router.get("/offers")
async def search_offers(
    origin: str = Query(..., description="IATA code di"),
    destination: str = Query(..., description="IATA code den"),
    departure_date: str = Query(..., description="YYYY-MM-DD"),
    adults: int = Query(1, ge=1, le=9),
    children: int = Query(0, ge=0, le=8),
    travel_class: str | None = None,
    max_price: int | None = None,
):
    return {
        "flights": await booking_service.search_offers(
            origin, destination, departure_date,
            adults, children, travel_class, max_price,
        )
    }


@router.get("/airports")
async def airport_suggestions(keyword: str = Query(..., min_length=2)):
    return {"airports": await booking_service.get_airport_suggestions(keyword)}


@router.post("/book")
async def book_flight(
    payload: FlightBookingRequest,
    user=Depends(get_current_user),
):
    return await booking_service.create_booking(user["user_id"], payload)
```

Register trong `Backend/app/v1/api/router.py`:

```python
from .endpoints import flights

api_router.include_router(flights.router)
```

### 3.5 Frontend Components

```
Frontend/src/app/
├── components/
│   ├── flight-search/          # Tìm kiếm chuyến bay
│   │   ├── flight-search.component.ts
│   │   ├── flight-search.component.html
│   │   └── flight-search.component.scss
│   ├── flight-card/            # Card hiển thị 1 chuyến bay
│   └── flight-booking/         # Form đặt vé
├── pages/
│   ├── flights/                # Trang danh sách chuyến bay
│   └── flight-detail/          # Chi tiết chuyến bay
└── services/
    └── flight.service.ts       # Flight API calls
```

### 3.6 Agent YAML Extension

Cập nhật `Backend/agent.yaml` — thêm flight capabilities:

```yaml
tools:
  - search_flights
  - get_airport_suggestions
  - book_flight
  - search_multi_city_flights
system_prompt_additions: |
  Bạn có khả năng tìm kiếm và đặt vé máy bay.
  Khi user hỏi về chuyến bay:
  1. Xác định điểm đi, điểm đến (convert thành IATA code)
  2. Hỏi thêm ngày đi, số hành khách nếu chưa có
  3. Gọi search_flights tool
  4. Trình bày kết quả dạng bảng so sánh
  5. Hỗ trợ đặt vé khi user chọn chuyến
```

---

## 4. Phase B — Hotel Agent (Agent Khách Sạn)

### 4.1 Overview

Agent tìm kiếm, so sánh, gợi ý và đặt phòng khách sạn.

**User flow:**
```
User: "Tìm khách sạn ở Đà Lạt 2 đêm, check-in 15/06, 2 người"
  → AI hỏi thêm: ngân sách? khu vực nào? tiện ích?
  → search_hotels tool → hiển thị danh sách
  → User chọn → book_hotel → thanh toán
```

### 4.2 External API — Booking.com (RapidAPI)

```python
# Backend/app/v1/services/hotel_service.py

import httpx
import os

class HotelService:
    BASE_URL = "https://booking-com.p.rapidapi.com/v1"

    def __init__(self):
        self.headers = {
            "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY"),
            "X-RapidAPI-Host": "booking-com.p.rapidapi.com"
        }

    async def search_hotels(
        self,
        destination: str,
        checkin_date: str,
        checkout_date: str,
        adults: int = 2,
        children: int = 0,
        rooms: int = 1,
        min_price: int | None = None,
        max_price: int | None = None,
        star_ratings: list[int] | None = None,
        amenities: list[str] | None = None,
    ) -> list[dict]:
        """Tìm kiếm khách sạn qua Booking.com API."""
        async with httpx.AsyncClient() as client:
            # Step 1: Get destination ID
            loc_resp = await client.get(
                f"{self.BASE_URL}/hotels/locations",
                headers=self.headers,
                params={"name": destination, "locale": "vi"}
            )
            dest_id = loc_resp.json()[0]["dest_id"]

            # Step 2: Search hotels
            params = {
                "dest_id": dest_id,
                "search_type": "city",
                "arrival_date": checkin_date,
                "departure_date": checkout_date,
                "adults": adults,
                "children_age": "",
                "room_qty": rooms,
                "units": "metric",
                "order_by": "popularity",
                "filter_by_currency": "VND",
                "locale": "vi",
            }
            if star_ratings:
                params["star_rating"] = ",".join(map(str, star_ratings))

            resp = await client.get(
                f"{self.BASE_URL}/hotels/search",
                headers=self.headers,
                params=params
            )
            return self._parse_hotel_results(resp.json())

    async def get_hotel_details(self, hotel_id: str) -> dict:
        """Lấy chi tiết khách sạn."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/hotels/data",
                headers=self.headers,
                params={"hotel_id": hotel_id, "locale": "vi"}
            )
            return resp.json()

    async def get_hotel_reviews(self, hotel_id: str) -> list[dict]:
        """Lấy đánh giá khách sạn."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.BASE_URL}/hotels/reviews",
                headers=self.headers,
                params={"hotel_id": hotel_id, "locale": "vi"}
            )
            return resp.json().get("result", [])
```

**Alternative APIs:**
- **Agoda API** — mạnh ở Đông Nam Á
- **Hotelbeds** — B2B wholesale rates
- **Google Hotels API** — aggregation

### 4.3 MCP Tools

Tạo file `Backend/app/v1/mcp/src/tools/hotel_tools.py`:

```python
@tool
async def search_hotels(
    destination: str,
    checkin_date: str,
    checkout_date: str,
    adults: int = 2,
    rooms: int = 1,
    min_price: int | None = None,
    max_price: int | None = None,
    star_ratings: list[int] | None = None,
) -> str:
    """
    Tìm kiếm khách sạn theo điểm đến và ngày.

    Args:
        destination: Tên thành phố hoặc địa điểm (vd: "Đà Lạt", "Nha Trang")
        checkin_date: Ngày nhận phòng (YYYY-MM-DD)
        checkout_date: Ngày trả phòng (YYYY-MM-DD)
        adults: Số người lớn
        rooms: Số phòng
        min_price: Giá tối thiểu (VND/đêm)
        max_price: Giá tối đa (VND/đêm)
        star_ratings: Lọc theo số sao [3,4,5]

    Returns:
        JSON string chứa danh sách khách sạn với giá, rating, tiện ích.
    """
    ...

@tool
async def get_hotel_details(hotel_id: str) -> str:
    """
    Lấy thông tin chi tiết khách sạn.

    Args:
        hotel_id: ID khách sạn từ kết quả search

    Returns:
        JSON string chứa chi tiết: mô tả, ảnh, tiện ích, chính sách.
    """
    ...

@tool
async def book_hotel(
    user_id: str,
    hotel_id: str,
    checkin_date: str,
    checkout_date: str,
    rooms: int,
    guests: list[dict],
    special_requests: str | None = None,
) -> str:
    """
    Đặt phòng khách sạn.

    Args:
        user_id: ID user
        hotel_id: ID khách sạn
        checkin_date: Ngày nhận phòng
        checkout_date: Ngày trả phòng
        rooms: Số phòng
        guests: Danh sách khách [{name, email, phone}]
        special_requests: Yêu cầu đặc biệt

    Returns:
        JSON string chứa booking ID và thông tin đặt phòng.
    """
    ...

@tool
async def compare_hotels(hotel_ids: list[str]) -> str:
    """
    So sánh nhiều khách sạn theo giá, rating, tiện ích.

    Args:
        hotel_ids: Danh sách ID khách sạn cần so sánh

    Returns:
        JSON string chứa bảng so sánh.
    """
    ...
```

### 4.4 Backend API + Frontend

Tương tự Flight Agent — tạo:
- `Backend/app/v1/api/endpoints/hotels.py`
- `Frontend/src/app/components/hotel-search/`
- `Frontend/src/app/components/hotel-card/`
- `Frontend/src/app/services/hotel.service.ts`

---

## 5. Phase C — Transport Agent (Agent Vé Xe)

### 5.1 Overview

Agent cho vé xe khách, xe limousine, tàu hỏa — phổ biến ở Việt Nam.

### 5.2 External APIs

| Provider | API | Coverage |
|---|---|---|
| 12Go.asia | REST API | Xe khách, tàu, ferry (Đông Nam Á) |
| Baolau | REST API | Xe khách, tàu, vé máy bay |
| Bookaway | REST API | Xe khách, minivan, limousine |
| Vietnam Railways | Scraper/API | Tàu hỏa nội địa |

```python
# Backend/app/v1/services/transport_service.py

import httpx
import os

class TransportService:
    def __init__(self):
        self.api_key = os.getenv("TWELVEGO_API_KEY")
        self.base_url = "https://api.12go.asia/v1"

    async def search_routes(
        self,
        origin: str,
        destination: str,
        date: str,
        transport_type: str = "bus",  # bus, train, ferry, van
        passengers: int = 1,
    ) -> list[dict]:
        """Tìm tuyến đường xe/tàu."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/search",
                params={
                    "from": origin,
                    "to": destination,
                    "date": date,
                    "type": transport_type,
                    "passengers": passengers,
                    "currency": "VND",
                    "lang": "vi",
                },
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            return self._parse_routes(resp.json())

    async def get_route_details(self, route_id: str) -> dict:
        """Chi tiết tuyến đường."""
        ...

    async def book_ticket(
        self,
        user_id: str,
        route_id: str,
        passengers: list[dict],
        seat_selection: list[str] | None = None,
    ) -> dict:
        """Đặt vé xe/tàu."""
        ...
```

### 5.3 MCP Tools

```python
@tool
async def search_transport(
    origin: str,
    destination: str,
    date: str,
    transport_type: str = "bus",
    passengers: int = 1,
) -> str:
    """
    Tìm kiếm vé xe/tàu giữa hai điểm.

    Args:
        origin: Điểm đi (tên thành phố)
        destination: Điểm đến
        date: Ngày đi (YYYY-MM-DD)
        transport_type: bus | train | ferry | van
        passengers: Số hành khách

    Returns:
        JSON string chứa danh sách chuyến xe/tàu.
    """
    ...

@tool
async def book_transport_ticket(
    user_id: str,
    route_id: str,
    passengers: list[dict],
) -> str:
    """
    Đặt vé xe/tàu.

    Args:
        user_id: ID user
        route_id: ID tuyến đường từ kết quả search
        passengers: [{name, phone, email, seat_number?}]

    Returns:
        JSON string chứa booking ID.
    """
    ...
```

---

## 6. Phase D — Modular Tour Builder (Drag & Drop)

### 6.1 Concept

**"Tour theo buổi" — User xếp các session như xếp hình để tạo tour hoàn hảo.**

```
┌─────────────────────────────────────────────────────────┐
│              TOUR BUILDER — ĐÀ LẠT 3 NGÀY               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  📅 Ngày 1 — Thứ 6, 15/06/2026                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  ☀️ SÁNG      │  │  🌤️ TRƯA     │  │  🌙 TỐI      │  │
│  │  Đồi Cỏ Hồng │  │  Lẩu bò       │  │  Chợ đêm      │  │
│  │  7:00-11:00  │  │  11:30-13:00 │  │  18:00-22:00 │  │
│  │  150,000đ    │  │  200,000đ    │  │  Miễn phí     │  │
│  │  ⭐ 4.8      │  │  ⭐ 4.5      │  │  ⭐ 4.2       │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                         │
│  📅 Ngày 2 — Thứ 7, 16/06/2026                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  ☀️ SÁNG      │  │  🌤️ TRƯA     │  │  🌙 TỐI      │  │
│  │  Thác Datanla│  │  BBQ Garden   │  │  Bar Live     │  │
│  │  ...         │  │  ...         │  │  ...          │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │  🎒 Activity Pool (Kéo thả vào ngày)             │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐    │   │
│  │  │Cáp     │ │Máng    │ │Đồi     │ │Hồ      │    │   │
│  │  │treo    │ │trượt   │ │Mộng Mơ │ │Tuyền Lâm│    │   │
│  │  └────────┘ └────────┘ └────────┘ └────────┘    │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  💰 Tổng: 1,850,000đ  |  👥 2 người  |  📝 Lưu tour   │
└─────────────────────────────────────────────────────────┘
```

### 6.2 Data Model

```sql
-- Session types (buổi)
CREATE TABLE tour_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,           -- "Đồi Cỏ Hồng buổi sáng"
    destination VARCHAR(255) NOT NULL,     -- "Đà Lạt"
    session_type VARCHAR(20) NOT NULL,     -- 'morning', 'afternoon', 'evening', 'fullday'
    category VARCHAR(100),                 -- 'adventure', 'food', 'culture', 'nature', 'nightlife', 'shopping'
    description TEXT,
    duration_minutes INT NOT NULL,         -- 240 = 4 tiếng
    price DECIMAL(12,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'VND',
    rating DECIMAL(2,1) DEFAULT 0,
    review_count INT DEFAULT 0,
    image_urls TEXT[],
    location JSONB,                        -- {lat, lng, address}
    meeting_point VARCHAR(500),
    included_items TEXT[],                 -- ["Vé vào cổng", "Hướng dẫn viên", ...]
    requirements TEXT[],                   -- ["Giày thể thao", "Áo mưa", ...]
    min_participants INT DEFAULT 1,
    max_participants INT DEFAULT 50,
    available_times JSONB,                -- {"weekday": ["07:00","13:00"], "weekend": ["06:00","14:00"]}
    is_active BOOLEAN DEFAULT true,
    embedding VECTOR(3072),               -- pgvector cho AI search
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Custom tours được tạo bởi user
CREATE TABLE custom_tours (
    custom_tour_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    tour_name VARCHAR(255),
    destination VARCHAR(255) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    num_people INT DEFAULT 1,
    total_price DECIMAL(12,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'draft',   -- draft, confirmed, completed, cancelled
    is_public BOOLEAN DEFAULT false,       -- cho phép share
    share_code VARCHAR(20) UNIQUE,         -- code để share tour
    ai_generated BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Các session trong custom tour (drag & drop items)
CREATE TABLE custom_tour_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    custom_tour_id UUID NOT NULL REFERENCES custom_tours(custom_tour_id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES tour_sessions(session_id),
    tour_date DATE NOT NULL,
    time_slot VARCHAR(20) NOT NULL,        -- 'morning', 'afternoon', 'evening'
    sort_order INT DEFAULT 0,
    notes TEXT,
    UNIQUE(custom_tour_id, tour_date, time_slot)  -- 1 slot = 1 session duy nhất
);

-- Session reviews
CREATE TABLE session_reviews (
    review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    session_id UUID NOT NULL REFERENCES tour_sessions(session_id),
    rating INT CHECK (rating BETWEEN 1 AND 5),
    content TEXT,
    images TEXT[],
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Session compatibility rules
CREATE TABLE session_conflicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_a UUID NOT NULL REFERENCES tour_sessions(session_id),
    session_b UUID NOT NULL REFERENCES tour_sessions(session_id),
    conflict_type VARCHAR(50),  -- 'same_location', 'time_overlap', 'physically_tiring'
    note TEXT
);
```

### 6.3 Backend — Tour Builder Service

```python
# Backend/app/v1/services/tour_builder_service.py

from datetime import date, timedelta
from typing import Optional

class TourBuilderService:

    async def get_available_sessions(
        self,
        destination: str,
        target_date: date,
        session_type: str | None = None,
        category: str | None = None,
        budget_range: tuple[float, float] | None = None,
    ) -> list[dict]:
        """Lấy danh sách session khả dụng cho ngày và địa điểm."""
        query = self.supabase.table("tour_sessions").select("*").eq(
            "destination", destination
        ).eq("is_active", True)

        if session_type:
            query = query.eq("session_type", session_type)
        if category:
            query = query.eq("category", category)

        results = query.execute()
        sessions = results.data

        # Filter by availability
        return [
            s for s in sessions
            if self._is_available_on_date(s, target_date)
               and self._within_budget(s, budget_range)
        ]

    async def get_recommended_combination(
        self,
        destination: str,
        start_date: date,
        end_date: date,
        preferences: list[str],  # ["adventure", "food", "nature"]
        budget: float,
    ) -> list[dict]:
        """
        AI gợi ý combination tối ưu cho cả chuyến đi.
        Sử dụng constraint satisfaction + AI scoring.
        """
        num_days = (end_date - start_date).days + 1
        all_sessions = await self.get_available_sessions(destination, start_date)

        # Score each session based on preferences
        scored = []
        for session in all_sessions:
            score = self._calculate_preference_score(session, preferences)
            scored.append((session, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        # Build optimal itinerary using greedy + constraint checking
        itinerary = []
        for day_offset in range(num_days):
            current_date = start_date + timedelta(days=day_offset)
            day_plan = {
                "date": current_date.isoformat(),
                "morning": None,
                "afternoon": None,
                "evening": None,
            }

            for slot in ["morning", "afternoon", "evening"]:
                for session, score in scored:
                    if (day_plan[slot] is None
                        and session["session_type"] in [slot, "fullday"]
                        and self._no_conflicts(session, day_plan)
                        and self._within_budget(session, budget)):
                        day_plan[slot] = session
                        budget -= float(session["price"])
                        break

            itinerary.append(day_plan)

        return itinerary

    async def build_custom_tour(
        self,
        user_id: str,
        destination: str,
        start_date: str,
        end_date: str,
        sessions: list[dict],  # [{session_id, date, time_slot}]
        tour_name: str | None = None,
    ) -> dict:
        """Tạo custom tour từ các session user đã chọn."""
        # Calculate total price
        total = 0
        session_records = []
        for s in sessions:
            session_data = await self._get_session(s["session_id"])
            total += float(session_data["price"])
            session_records.append({
                "session_id": s["session_id"],
                "tour_date": s["date"],
                "time_slot": s["time_slot"],
            })

        # Create custom tour
        custom_tour = await self.supabase.table("custom_tours").insert({
            "user_id": user_id,
            "tour_name": tour_name or f"Tour {destination} tự chọn",
            "destination": destination,
            "start_date": start_date,
            "end_date": end_date,
            "total_price": total,
            "status": "draft",
        }).execute()

        tour_id = custom_tour.data[0]["custom_tour_id"]

        # Insert sessions
        for record in session_records:
            record["custom_tour_id"] = tour_id
        await self.supabase.table("custom_tour_sessions").insert(
            session_records
        ).execute()

        return {"custom_tour_id": tour_id, "total_price": total}

    async def ai_suggest_fill_gaps(
        self,
        custom_tour_id: str,
        empty_slots: list[dict],  # [{date, time_slot}]
    ) -> list[dict]:
        """AI gợi ý điền vào các slot trống."""
        tour = await self._get_custom_tour(custom_tour_id)
        existing_sessions = await self._get_tour_sessions(custom_tour_id)

        suggestions = []
        for slot in empty_slots:
            available = await self.get_available_sessions(
                tour["destination"], slot["date"]
            )
            # Filter compatible with existing sessions
            compatible = [
                s for s in available
                if not any(self._has_conflict(s, ex) for ex in existing_sessions)
            ]
            # Rank by compatibility score
            compatible.sort(
                key=lambda s: self._compatibility_score(s, existing_sessions),
                reverse=True
            )
            suggestions.append({
                "date": slot["date"],
                "time_slot": slot["time_slot"],
                "recommendations": compatible[:3]  # Top 3 suggestions
            })

        return suggestions

    def _calculate_preference_score(self, session: dict, prefs: list[str]) -> float:
        """Score session dựa trên user preferences."""
        score = 0
        category = session.get("category", "")
        if category in prefs:
            score += 10
        score += float(session.get("rating", 0)) * 2
        return score

    def _no_conflicts(self, session: dict, day_plan: dict) -> bool:
        """Kiểm tra conflict với sessions đã có trong ngày."""
        # Check location proximity, physical difficulty, etc.
        return True  # Simplified

    def _has_conflict(self, a: dict, b: dict) -> bool:
        return a["session_id"] == b["session_id"]
```

### 6.4 MCP Tools for Tour Builder

```python
@tool
async def search_tour_sessions(
    destination: str,
    date: str,
    time_slot: str | None = None,
    category: str | None = None,
    max_price: float | None = None,
) -> str:
    """
    Tìm các hoạt động/session tour theo buổi tại một địa điểm.

    Args:
        destination: Địa điểm (vd: "Đà Lạt", "Sapa")
        date: Ngày cụ thể (YYYY-MM-DD)
        time_slot: Buổi muốn đi — morning | afternoon | evening
        category: Loại hoạt động — adventure | food | culture | nature | nightlife
        max_price: Giá tối đa (VND/người)

    Returns:
        JSON string danh sách session phù hợp.
    """
    ...

@tool
async def ai_build_itinerary(
    destination: str,
    start_date: str,
    end_date: str,
    preferences: list[str],
    budget_per_day: float,
    num_people: int = 1,
) -> str:
    """
    AI tự động xây dựng lịch trình tour tối ưu.

    Args:
        destination: Địa điểm
        start_date: Ngày bắt đầu
        end_date: Ngày kết thúc
        preferences: Sở thích ["adventure", "food", "culture", "relax"]
        budget_per_day: Ngân sách mỗi ngày (VND)
        num_people: Số người

    Returns:
        JSON string chứa lịch trình đề xuất theo ngày và buổi.
    """
    ...

@tool
async def suggest_fill_gaps(
    custom_tour_id: str,
) -> str:
    """
    AI gợi ý điền vào các buổi trống trong custom tour.

    Args:
        custom_tour_id: ID của custom tour

    Returns:
        JSON string chứa gợi ý cho từng slot trống.
    """
    ...

@tool
async def save_custom_tour(
    user_id: str,
    destination: str,
    start_date: str,
    end_date: str,
    sessions: list[dict],
    tour_name: str | None = None,
) -> str:
    """
    Lưu custom tour do user tự sắp xếp.

    Args:
        user_id: ID user
        destination: Địa điểm
        start_date/end_date: Ngày
        sessions: [{session_id, date, time_slot}]
        tour_name: Tên tour (tùy chọn)

    Returns:
        JSON string chứa custom_tour_id và tổng giá.
    """
    ...

@tool
async def share_custom_tour(custom_tour_id: str) -> str:
    """
    Tạo link chia sẻ custom tour cho người khác.

    Returns:
        JSON string chứa share_code và share_url.
    """
    ...
```

### 6.5 Frontend — Drag & Drop Tour Builder

#### Tech: Angular CDK Drag Drop

```typescript
// Frontend/src/app/components/tour-builder/tour-builder.component.ts

import { CdkDragDrop, CdkDrag, CdkDropList, moveItemInArray, transferArrayItem }
  from '@angular/cdk/drag-drop';
import { Component, OnInit } from '@angular/core';

interface TourSession {
  session_id: string;
  name: string;
  session_type: 'morning' | 'afternoon' | 'evening';
  category: string;
  price: number;
  duration_minutes: number;
  rating: number;
  image_url: string;
}

interface DayPlan {
  date: string;
  morning: TourSession | null;
  afternoon: TourSession | null;
  evening: TourSession | null;
}

@Component({
  selector: 'app-tour-builder',
  templateUrl: './tour-builder.component.html',
  styleUrls: ['./tour-builder.component.scss'],
  standalone: true,
  imports: [CdkDropList, CdkDrag, CommonModule],
})
export class TourBuilderComponent implements OnInit {
  destination = '';
  startDate!: Date;
  endDate!: Date;
  dayPlans: DayPlan[] = [];
  activityPool: TourSession[] = [];
  totalPrice = 0;

  // Drop handler — drag từ pool vào slot, hoặc đổi slot
  drop(event: CdkDragDrop<TourSession[]>, targetDate: string, targetSlot: string) {
    if (event.previousContainer === event.container) {
      moveItemInArray(event.container.data, event.previousIndex, event.currentIndex);
    } else {
      const session = event.previousContainer.data[event.previousIndex];
      // Check conflict
      if (this.hasConflict(session, targetDate, targetSlot)) {
        this.notificationService.warn('Session này conflict với session khác!');
        return;
      }
      transferArrayItem(
        event.previousContainer.data,
        event.container.data,
        event.previousIndex,
        event.currentIndex,
      );
      this.recalculateTotal();
    }
  }

  // AI suggest fill gaps
  async aiFillGaps() {
    const emptySlots = this.findEmptySlots();
    const suggestions = await this.tourBuilderService.suggestFillGaps(
      this.customTourId, emptySlots
    ).toPromise();
    // Show suggestions as overlay cards user can accept/reject
    this.showSuggestions(suggestions);
  }

  // Save tour
  async saveTour() {
    const result = await this.tourBuilderService.saveCustomTour({
      destination: this.destination,
      start_date: this.startDate,
      end_date: this.endDate,
      sessions: this.flattenDayPlans(),
    }).toPromise();
    this.notificationService.success('Tour đã được lưu!');
  }

  private recalculateTotal() {
    this.totalPrice = this.dayPlans.reduce((total, day) => {
      return total
        + (day.morning?.price || 0)
        + (day.afternoon?.price || 0)
        + (day.evening?.price || 0);
    }, 0);
  }
}
```

#### Template Structure

```html
<!-- tour-builder.component.html -->
<div class="tour-builder">
  <!-- Header: destination + date picker -->
  <div class="builder-header">
    <h2>Tự thiết kế tour {{ destination }}</h2>
    <div class="date-range">
      <p-calendar [(ngModel)]="startDate" placeholder="Ngày đi"></p-calendar>
      <p-calendar [(ngModel)]="endDate" placeholder="Ngày về"></p-calendar>
      <button (click)="aiFillGaps()" class="ai-suggest-btn">
        AI Gợi ý lịch trình
      </button>
    </div>
  </div>

  <!-- Day Plans — each day has 3 drop zones -->
  <div class="day-plans" *ngFor="let day of dayPlans; let i = index">
    <h3>Ngày {{ i + 1 }} — {{ day.date | date:'EEE, dd/MM' }}</h3>

    <div class="slots-row">
      <!-- Morning slot -->
      <div cdkDropList
           [cdkDropListData]="[day.morning]"
           cdkDropListConnectedTo="activity-pool"
           (cdkDropListDropped)="drop($event, day.date, 'morning')"
           class="slot morning-slot">
        <div *ngIf="day.morning" cdkDrag class="session-card">
          <img [src]="day.morning.image_url" alt="">
          <h4>{{ day.morning.name }}</h4>
          <span class="price">{{ day.morning.price | currency:'VND' }}</span>
          <button class="remove-btn" (click)="removeSession(day, 'morning')">✕</button>
        </div>
        <div *ngIf="!day.morning" class="empty-slot">
          <span>+ Kéo hoạt động vào buổi sáng</span>
        </div>
      </div>

      <!-- Afternoon slot — same pattern -->
      <!-- Evening slot — same pattern -->
    </div>
  </div>

  <!-- Activity Pool — draggable items -->
  <div cdkDropList
       id="activity-pool"
       [cdkDropListData]="activityPool"
       cdkDropListConnectedTo="all-slot-ids"
       class="activity-pool">
    <h3>Hoạt động có sẵn</h3>
    <div class="pool-filters">
      <button (click)="filterCategory('adventure')">Thám hiểm</button>
      <button (click)="filterCategory('food')">Ẩm thực</button>
      <button (click)="filterCategory('culture')">Văn hóa</button>
      <button (click)="filterCategory('nature')">Thiên nhiên</button>
    </div>
    <div class="pool-items">
      <div *ngFor="let session of activityPool" cdkDrag class="pool-card">
        <img [src]="session.image_url" alt="">
        <span class="badge">{{ session.category }}</span>
        <h4>{{ session.name }}</h4>
        <div class="meta">
          <span>{{ session.duration_minutes }} phút</span>
          <span>{{ session.price | currency:'VND' }}</span>
          <span>⭐ {{ session.rating }}</span>
        </div>
      </div>
    </div>
  </div>

  <!-- Summary Bar -->
  <div class="builder-summary">
    <span>Tổng: {{ totalPrice | currency:'VND' }}</span>
    <span>{{ dayPlans.length }} ngày</span>
    <button (click)="saveTour()" class="save-btn">Lưu Tour</button>
    <button (click)="bookTour()" class="book-btn">Đặt Tour</button>
    <button (click)="shareTour()" class="share-btn">Chia sẻ</button>
  </div>
</div>
```

#### SCSS — Grid Layout with Drag Feedback

```scss
// tour-builder.component.scss
.tour-builder {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.day-plans {
  margin: 2rem 0;
  padding: 1.5rem;
  background: #f8fafc;
  border-radius: 16px;

  .slots-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
  }
}

.slot {
  min-height: 140px;
  border: 2px dashed #e2e8f0;
  border-radius: 12px;
  padding: 1rem;
  transition: all 0.2s;

  &.morning-slot { background: rgba(251, 191, 36, 0.05); }
  &.afternoon-slot { background: rgba(251, 146, 60, 0.05); }
  &.evening-slot { background: rgba(99, 102, 241, 0.05); }

  // Visual feedback khi drag over
  &.cdk-drop-list-receiving {
    border-color: #3b82f6;
    background: rgba(59, 130, 246, 0.1);
    transform: scale(1.02);
  }
}

.session-card {
  background: white;
  border-radius: 10px;
  padding: 0.75rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  cursor: grab;

  &:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.15); }

  // Drag preview
  .cdk-drag-preview {
    box-shadow: 0 8px 32px rgba(0,0,0,0.2);
    transform: rotate(2deg);
    border-radius: 12px;
  }
}

.activity-pool {
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 16px;
  padding: 1.5rem;
  margin-top: 2rem;

  .pool-items {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 1rem;
  }
}

.builder-summary {
  position: sticky;
  bottom: 0;
  background: white;
  padding: 1rem 2rem;
  border-top: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  box-shadow: 0 -4px 16px rgba(0,0,0,0.05);
}
```

### 6.6 AI-Powered Smart Suggestions

```python
# Backend/app/v1/services/tour_builder_ai_service.py

from openai import AsyncOpenAI

class TourBuilderAIService:

    async def generate_smart_itinerary(
        self,
        destination: str,
        days: int,
        preferences: list[str],
        budget: float,
        travel_style: str = "balanced",  # relaxed, adventurous, budget, luxury
        group_type: str = "couple",      # solo, couple, family, friends
        must_avoid: list[str] | None = None,
    ) -> dict:
        """
        AI tạo lịch trình thông minh, tính đến:
        - Vị trí địa lý (cluster activities gần nhau trong 1 ngày)
        - Thời tiết dự báo
        - Mức độ体力 (không xếp quá nhiều hoạt động nặng liên tiếp)
        - Giờ mở/đóng của địa điểm
        - Best time to visit (vd: đồi cỏ hồng đẹp nhất sáng sớm)
        """
        prompt = f"""
        Tạo lịch trình {days} ngày tại {destination}:
        - Sở thích: {', '.join(preferences)}
        - Ngân sách: {budget:,.0f} VND/ngày
        - Phong cách: {travel_style}
        - Nhóm: {group_type}
        {"- Tránh: " + ", ".join(must_avoid) if must_avoid else ""}

        Trả về JSON format:
        {{
            "days": [
                {{
                    "date_offset": 0,
                    "theme": "Khám phá thiên nhiên",
                    "morning": {{
                        "activity": "Tên hoạt động",
                        "description": "Mô tả ngắn",
                        "estimated_price": 150000,
                        "duration": "3h",
                        "why_recommended": "Lý do AI chọn",
                        "tips": "Mẹo nhỏ"
                    }},
                    "afternoon": {{ ... }},
                    "evening": {{ ... }}
                }}
            ],
            "total_estimated_cost": 2500000,
            "packing_tips": ["...", "..."],
            "weather_tips": "...",
            "budget_breakdown": {{ "activities": 0, "food": 0, "transport": 0 }}
        }}
        """

        response = await self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7,
        )

        return json.loads(response.choices[0].message.content)
```

---

## 7. Phase E — Các tính năng AI độc đáo

### 7.1 AI Travel Concierge (Quản gia du lịch ảo)

**Concept:** Một AI assistant cá nhân hóa theo dõi toàn bộ chuyến đi.

```python
# Backend/app/v1/services/concierge_service.py

class ConciergeService:
    """
    Quản gia AI — proactive assistant suốt chuyến đi.
    Không đợi user hỏi, AI tự đề xuất.
    """

    async def proactive_suggestions(self, user_id: str) -> list[dict]:
        """
        Push notifications thông minh:
        - "Sắp đến giờ check-in khách sạn, bạn có cần hướng dẫn không?"
        - "Thời tiết chiều nay mưa, nên đổi activity indoor"
        - "Nhà hàng bạn bookmark cách đây 500m, có muốn đặt bàn?"
        - "Ngày mai có lễ hội tại địa điểm bạn đi qua"
        """
        ...

    async def handle_disruption(self, user_id: str, event: dict) -> dict:
        """
        Xử lý sự cố tự động:
        - Chuyến bay delay → tự đề xuất thay đổi itinerary
        - Khách sạn overbook → tìm khách sạn tương đương nearby
        - Thời tiết xấu → recomment indoor activities
        """
        ...

    async def generate_travel_journal(self, user_id: str, trip_id: str) -> dict:
        """
        Tự động tạo travel journal sau chuyến đi:
        - Compile ảnh + check-ins thành story
        - AI viết caption cho từng ảnh
        - Tạo video recap ngắn
        - Gợi ý review cho từng session
        """
        ...
```

### 7.2 AI Price Predictor (Dự đoán giá vé)

```python
# Backend/app/v1/services/price_predictor_service.py

class PricePredictorService:
    """
    Dự đoán xu hướng giá vé máy bay, khách sạn.
    Giúp user quyết định: nên mua ngay hay chờ?
    """

    async def predict_flight_price(
        self,
        route: str,
        current_price: float,
        target_date: str,
    ) -> dict:
        """
        Returns:
        {
            "current_price": 2500000,
            "predicted_best_price": 2100000,
            "predicted_best_date": "2026-06-10",
            "recommendation": "WAIT",  // BUY_NOW or WAIT
            "confidence": 0.78,
            "price_history_30days": [...],
            "price_forecast_14days": [...]
        }
        """
        # Approach 1: Historical pattern analysis
        # Approach 2: LLM-based reasoning (GPT-4)
        # Approach 3: Simple rule-based (day of week, season)
        ...

    async def set_price_alert(
        self,
        user_id: str,
        route: str,
        target_price: float,
        date_range: tuple[str, str],
    ) -> str:
        """Tạo alert khi giá xuống đến mức target."""
        ...
```

### 7.3 Travel Buddy Matcher (Tìm bạn đồng hành)

```python
# SQL Schema
CREATE TABLE travel_buddy_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    travel_style VARCHAR(50),      -- 'adventure', 'relax', 'culture', 'foodie'
    budget_level VARCHAR(20),       -- 'budget', 'mid', 'luxury'
    preferred_destinations TEXT[],
    age_range VARCHAR(20),          -- '18-25', '25-35', '35-50'
    languages TEXT[],               -- ["Vietnamese", "English"]
    interests TEXT[],
    personality_tags TEXT[],        -- ["introvert", "photographer", "early_bird"]
    embedding VECTOR(3072),        -- dùng để matching
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE buddy_match_requests (
    request_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID,
    requester_id UUID NOT NULL REFERENCES users(user_id),
    target_user_id UUID NOT NULL REFERENCES users(user_id),
    message TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    compatibility_score DECIMAL(3,2),
    created_at TIMESTAMPTZ DEFAULT now()
);
```

```python
# Service
class BuddyMatcherService:
    async def find_matching_buddies(
        self,
        user_id: str,
        destination: str,
        date_range: tuple[str, str],
        travel_style: str,
    ) -> list[dict]:
        """
        Tìm bạn đồng hành phù hợp dùng AI embedding similarity.
        Score dựa trên: travel style, budget, interests, personality.
        """
        ...

    async def generate_icebreaker(self, match_id: str) -> str:
        """AI tạo câu mở đầu để 2 người bắt chuyện."""
        ...
```

### 7.4 AI Voice Travel Assistant

```python
# Backend/app/v1/services/voice_assistant_service.py

class VoiceAssistantService:
    """
    Voice-first interface cho travel booking.
    Dùng Whisper (speech-to-text) + TTS (text-to-speech).
    """

    async def process_voice_command(self, audio_file: bytes) -> dict:
        """
        Flow:
        1. Whisper → transcript
        2. Intent extraction (book flight? search hotel? ask weather?)
        3. Execute action via existing tools
        4. TTS response
        """
        ...

    async def real_time_translation(self, audio: bytes, target_lang: str) -> bytes:
        """
        Real-time translation cho traveler ở nước ngoài.
        Vietnamese → English/Thai/Japanese/etc.
        """
        ...
```

### 7.5 Smart Packing List Generator

```python
@tool
async def generate_packing_list(
    destination: str,
    start_date: str,
    end_date: str,
    activities: list[str],
    gender: str | None = None,
    is_kids: bool = False,
) -> str:
    """
    AI tạo danh sách đồ cần mang theo tự động.

    Args:
        destination: Địa điểm
        start_date/end_date: Ngày đi/về
        activities: Hoạt động dự kiến ["trekking", "swimming", "dining"]
        gender: Giới tính (để gợi ý đồ phù hợp)
        is_kids: Có trẻ em đi cùng không

    Returns:
        JSON string: categorized packing list.
    """
    prompt = f"""
    Tạo packing list cho chuyến đi {destination} từ {start_date} đến {end_date}.
    Hoạt động: {', '.join(activities)}
    Trẻ em: {"Có" if is_kids else "Không"}

    Kiểm tra thời tiết dự báo tại {destination} và điều chỉnh.

    Trả về JSON:
    {{
        "weather_forecast": {{ "avg_temp": 22, "rain_chance": 0.3 }},
        "categories": {{
            "clothing": ["áo thun x3", "quần short x2", ...],
            "toiletries": [...],
            "electronics": [...],
            "documents": [...],
            "medication": [...],
            "activity_specific": {{ "trekking": ["giày leo núi", ...] }},
            "kids" (if applicable): [...]
        }},
        "tips": ["Mua sim card tại sân bay", ...]
    }}
    """
    ...
```

### 7.6 AI-Powered Travel Story Generator

```python
class TravelStoryService:
    """
    Sau chuyến đi, AI tự động tạo travel blog/story.
    """

    async def generate_story(
        self,
        user_id: str,
        trip_id: str,
        style: str = "blog",  # blog, instagram, video_script
    ) -> dict:
        """
        Compile check-ins, photos, reviews thành story hoàn chỉnh.
        AI viết narrative, chọn best photos, thêm emoji.
        """
        ...

    async def generate_photo_captions(
        self,
        photos: list[str],  # URLs
        location_context: str,
    ) -> list[str]:
        """AI viết caption cho ảnh du lịch."""
        ...
```

### 7.7 Group Travel Planner

```python
class GroupPlannerService:
    """
    Lên kế hoạch du lịch nhóm — vote & compromise.
    """

    async def create_group_trip(
        self,
        creator_id: str,
        destination: str,
        date_range: tuple[str, str],
        member_ids: list[str],
    ) -> dict:
        """Tạo nhóm trip, mời thành viên."""
        ...

    async def ai_compromise_itinerary(
        self,
        group_preferences: list[dict],  # preferences của từng thành viên
        destination: str,
        date_range: tuple[str, str],
        budget: float,
    ) -> dict:
        """
        AI tìm itinerary thỏa mãn sở thích của tất cả thành viên.
        Dùng multi-objective optimization.
        """
        ...

    async def vote_on_session(
        self,
        group_trip_id: str,
        session_options: list[str],  # session IDs
    ) -> dict:
        """Thành viên vote chọn hoạt động, AI đếm + đề xuất."""
        ...
```

### 7.8 Sustainable Travel Score

```python
@tool
async def calculate_sustainability_score(itinerary: dict) -> str:
    """
    Đánh giá mức độ bền vững của chuyến đi.
    Score: carbon footprint, local economy support, eco-certifications.
    """
    ...
```

### 7.9 AI Travel Insurance Recommender

```python
@tool
async def recommend_travel_insurance(
    trip_details: dict,
    user_profile: dict,
) -> str:
    """
    AI gợi ý gói bảo hiểm du lịch phù hợp.
    Phân tích rủi ro dựa trên destination, activities, duration.
    """
    ...
```

### 7.10 AR Preview của điểm đến

```typescript
// Frontend — sử dụng Three.js (đã có sẵn trong project)
// Frontend/src/app/components/ar-preview/ar-preview.component.ts

@Component({
  selector: 'app-ar-preview',
  template: `
    <div class="ar-container">
      <canvas #arCanvas></canvas>
      <div class="ar-overlay">
        <h3>{{ destination.name }}</h3>
        <p>{{ destination.description }}</p>
        <div class="ar-controls">
          <button (click)="rotate()">Xoay 360°</button>
          <button (click)="toggleWeather()">Xem thời tiết</button>
        </div>
      </div>
    </div>
  `
})
export class ArPreviewComponent implements AfterViewInit {
  // Three.js scene với 3D model của destination
  // Panorama 360° viewer
  // Weather overlay
}
```

---

## 8. Database Schema Extensions

### Migration script tổng hợp

```sql
-- File: Backend/migrations/add_agent_tables.sql

-- ============================================
-- PHASE A: FLIGHTS
-- ============================================

CREATE TABLE flight_bookings (
    booking_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    flight_offer_id VARCHAR(100) NOT NULL,
    airline VARCHAR(100),
    origin VARCHAR(10) NOT NULL,
    destination VARCHAR(10) NOT NULL,
    departure_time TIMESTAMPTZ NOT NULL,
    arrival_time TIMESTAMPTZ NOT NULL,
    passengers JSONB NOT NULL,
    total_amount DECIMAL(12,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'VND',
    status VARCHAR(20) DEFAULT 'pending',
    payment_id UUID REFERENCES payments(payment_id),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE price_alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    origin VARCHAR(10) NOT NULL,
    destination VARCHAR(10) NOT NULL,
    target_price DECIMAL(12,2),
    date_range_start DATE,
    date_range_end DATE,
    is_active BOOLEAN DEFAULT true,
    last_checked TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- PHASE B: HOTELS
-- ============================================

CREATE TABLE hotel_bookings (
    booking_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    hotel_id VARCHAR(100) NOT NULL,
    hotel_name VARCHAR(255),
    checkin_date DATE NOT NULL,
    checkout_date DATE NOT NULL,
    rooms INT DEFAULT 1,
    guests JSONB,
    total_amount DECIMAL(12,2),
    currency VARCHAR(3) DEFAULT 'VND',
    status VARCHAR(20) DEFAULT 'pending',
    payment_id UUID REFERENCES payments(payment_id),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- PHASE C: TRANSPORT
-- ============================================

CREATE TABLE transport_bookings (
    booking_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    route_id VARCHAR(100) NOT NULL,
    transport_type VARCHAR(20) NOT NULL,  -- bus, train, ferry, van
    origin VARCHAR(255) NOT NULL,
    destination VARCHAR(255) NOT NULL,
    departure_time TIMESTAMPTZ NOT NULL,
    passengers JSONB NOT NULL,
    seat_numbers TEXT[],
    total_amount DECIMAL(12,2),
    currency VARCHAR(3) DEFAULT 'VND',
    status VARCHAR(20) DEFAULT 'pending',
    payment_id UUID REFERENCES payments(payment_id),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- PHASE D: TOUR BUILDER (see section 6.2)
-- ============================================
-- tour_sessions, custom_tours, custom_tour_sessions,
-- session_reviews, session_conflicts
-- (already defined above)

-- ============================================
-- PHASE E: EXTENDED FEATURES
-- ============================================

CREATE TABLE travel_buddy_profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(user_id),
    travel_style VARCHAR(50),
    budget_level VARCHAR(20),
    preferred_destinations TEXT[],
    age_range VARCHAR(20),
    languages TEXT[],
    interests TEXT[],
    personality_tags TEXT[],
    embedding VECTOR(3072),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE group_trips (
    trip_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255),
    destination VARCHAR(255) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    budget DECIMAL(12,2),
    created_by UUID NOT NULL REFERENCES users(user_id),
    status VARCHAR(20) DEFAULT 'planning',
    itinerary JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE group_trip_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES group_trips(trip_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id),
    role VARCHAR(20) DEFAULT 'member',  -- creator, admin, member
    preferences JSONB,
    joined_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(trip_id, user_id)
);

CREATE TABLE packing_lists (
    list_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id),
    trip_id UUID,
    destination VARCHAR(255),
    items JSONB NOT NULL,
    weather_forecast JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- INDEXES
-- ============================================

CREATE INDEX idx_flight_bookings_user ON flight_bookings(user_id);
CREATE INDEX idx_hotel_bookings_user ON hotel_bookings(user_id);
CREATE INDEX idx_transport_bookings_user ON transport_bookings(user_id);
CREATE INDEX idx_tour_sessions_destination ON tour_sessions(destination);
CREATE INDEX idx_tour_sessions_category ON tour_sessions(category);
CREATE INDEX idx_tour_sessions_embedding ON tour_sessions USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_custom_tours_user ON custom_tours(user_id);
CREATE INDEX idx_buddy_profiles_embedding ON travel_buddy_profiles USING ivfflat (embedding vector_cosine_ops);
```

### Migration bổ sung cho Admin extension

Phần admin mở rộng (Section 11.10 + 11.11) cần thêm 2 file migration. Nội dung đầy đủ nằm tại các mục tương ứng, ở đây chỉ liệt kê để dev biết thứ tự apply:

| Thứ tự | File | Bảng tạo | Mô tả | Section tham chiếu |
|---|---|---|---|---|
| 1 | `add_agent_tables.sql` | `flight_bookings`, `hotel_bookings`, `transport_bookings`, `travel_buddy_profiles`, `group_trips`, `group_trip_members`, `packing_lists`, `price_alerts` (+ schemas Phase D) | Phase A-E base | Section 8 (trên) |
| 2 | `add_admin_extension_tables.sql` | `agent_configs`, `mcp_servers`, `agent_runs`, `intent_stats_daily`, `itineraries`, `admin_audit_log` | Multi-agent admin | Section 11.10.1 |
| 3 | `add_phase_e_priority_tables.sql` | `price_history`, `packing_list_templates`, `travel_stories`, `insurance_plans`, `insurance_orders` (+ ALTER `price_alerts`) | Smart features admin | Section 11.11.1 |

Apply tuần tự bằng Supabase CLI: `supabase db push` (đối với project local) hoặc paste từng file vào SQL editor (đối với project remote).

---

## 9. MCP Tools Extension Guide

### Quy trình thêm tool mới (đối chiếu pattern đang chạy)

```
1. Tao file:        Backend/app/v1/mcp/src/tools/<feature>_tools.py
2. Khai bao ham:    def register_<feature>_tools(mcp: FastMCP) -> None
3. Trong ham:       Dung @mcp.tool() cho moi tool, validate input bang pydantic
4. Register:        Goi register_<feature>_tools(mcp) trong
                    Backend/app/v1/mcp/src/tools/__init__.py::register_all_tools
5. (Optional)       Neu tach sub-server: tao mcp = FastMCP("<feature>")
                    roi server.import_server(<feature>_mcp, prefix="<feature>")
                    trong Backend/app/v1/mcp/server.py
6. Config agent:    Them ten tool vao Backend/agent.yaml -> tool_calling.available_tools
7. Document:        Cap nhat guide nay
```

### Template tool file (khớp với `flight_tools.py` đã có)

```python
# Backend/app/v1/mcp/src/tools/<feature>_tools.py

import json

from fastmcp import FastMCP
from pydantic import ValidationError

from app.v1.services.<feature>_service import <Feature>Service
from app.v1.mcp.src.schema.<feature>_schema import Search<Feature>Input


def register_<feature>_tools(mcp: FastMCP) -> None:
    service = <Feature>Service()

    @mcp.tool()
    async def search_<feature>(param1: str, param2: int = 1) -> str:
        """Short description so the LLM can decide when to use this tool.

        Args:
            param1: Mo ta param1
            param2: Mo ta param2

        Returns:
            JSON string mo ta output.
        """
        try:
            payload = Search<Feature>Input(param1=param1, param2=param2)
        except ValidationError as exc:
            return f"Input validation error: {exc}"

        result = await service.search(payload.param1, payload.param2)
        return json.dumps(result, ensure_ascii=False)
```

Đăng ký trong `mcp/src/tools/__init__.py`:

```python
from .<feature>_tools import register_<feature>_tools


def register_all_tools(mcp: FastMCP) -> None:
    register_booking_tools(mcp)
    register_tour_search_tools(mcp)
    register_search_personalization_tools(mcp)
    register_weather_tools(mcp)
    register_flight_tools(mcp)
    register_<feature>_tools(mcp)
```

### Updated agent.yaml (complete):

```yaml
# Backend/agent.yaml — updated version

model: "gpt-4o-mini"
temperature: 0.7

system_prompt: |
  Bạn là AI Travel Assistant của nền tảng du lịch.
  Bạn hỗ trợ user tìm kiếm, đặt vé máy bay, khách sạn, xe/tàu,
  xây dựng tour tự chọn, và mọi nhu cầu du lịch.

  Nguyên tắc:
  - Luôn trả lời bằng tiếng Việt
  - Hỏi đủ thông tin trước khi gọi tool
  - Trình bày kết quả rõ ràng, dễ so sánh
  - Gợi ý thêm options phù hợp
  - Hỗ trợ thanh toán VNPay

tools:
  # Existing tools
  - search_tour_packages
  - create_booking
  - verify_otp_and_confirm_booking
  - get_user_bookings
  - create_payment
  - generate_payment_ui
  - apply_promotion_code
  - search_personalization

  # Phase A: Flight
  - search_flights
  - get_airport_suggestions
  - book_flight
  - search_multi_city_flights

  # Phase B: Hotel
  - search_hotels
  - get_hotel_details
  - book_hotel
  - compare_hotels

  # Phase C: Transport
  - search_transport
  - book_transport_ticket

  # Phase D: Tour Builder
  - search_tour_sessions
  - ai_build_itinerary
  - suggest_fill_gaps
  - save_custom_tour
  - share_custom_tour

  # Phase E: Smart Features
  - generate_packing_list
  - calculate_sustainability_score
  - recommend_travel_insurance
  - find_travel_buddies
```

---

## 10. Frontend Component Guide

### Cấu trúc thư mục mới:

```
Frontend/src/app/
├── components/
│   ├── ai-chatbot/                    # EXISTING — cập nhật
│   ├── flight-search/                 # NEW — Phase A
│   │   ├── flight-search.component.ts
│   │   ├── flight-search.component.html
│   │   └── flight-search.component.scss
│   ├── flight-card/                   # NEW
│   ├── flight-booking-form/           # NEW
│   ├── hotel-search/                  # NEW — Phase B
│   ├── hotel-card/                    # NEW
│   ├── hotel-compare/                 # NEW
│   ├── transport-search/              # NEW — Phase C
│   ├── transport-card/                # NEW
│   ├── tour-builder/                  # NEW — Phase D ⭐ FEATURE
│   │   ├── tour-builder.component.ts
│   │   ├── tour-builder.component.html
│   │   └── tour-builder.component.scss
│   ├── tour-session-card/             # NEW
│   ├── packing-list/                  # NEW — Phase E
│   ├── price-predictor/               # NEW
│   ├── buddy-matcher/                 # NEW
│   ├── sustainability-badge/          # NEW
│   ├── ar-preview/                    # NEW
│   └── voice-assistant/               # NEW
├── pages/
│   ├── flights/                       # NEW
│   ├── hotels/                        # NEW
│   ├── transport/                     # NEW
│   ├── tour-builder/                  # NEW ⭐
│   ├── travel-buddies/                # NEW
│   └── packing-list/                  # NEW
├── services/
│   ├── flight.service.ts              # NEW
│   ├── hotel.service.ts               # NEW
│   ├── transport.service.ts           # NEW
│   ├── tour-builder.service.ts        # NEW
│   ├── concierge.service.ts           # NEW
│   ├── price-predictor.service.ts      # NEW
│   ├── buddy-matcher.service.ts       # NEW
│   └── voice.service.ts               # NEW
└── shared/models/
    ├── flight.model.ts                # NEW
    ├── hotel.model.ts                 # NEW
    ├── transport.model.ts             # NEW
    ├── tour-session.model.ts          # NEW
    └── custom-tour.model.ts           # NEW
```

### Routes mới cần thêm:

```typescript
// app.routes.ts — thêm vào

// Phase A: Flights
{ path: 'flights', component: FlightsComponent },
{ path: 'flights/search', component: FlightSearchComponent },

// Phase B: Hotels
{ path: 'hotels/search', component: HotelSearchComponent },
{ path: 'hotels/compare', component: HotelCompareComponent },

// Phase C: Transport
{ path: 'transport', component: TransportComponent },

// Phase D: Tour Builder
{
  path: 'tour-builder',
  component: TourBuilderComponent,
  canActivate: [authGuard],
  children: [
    { path: '', component: TourBuilderHomeComponent },
    { path: ':destination', component: TourBuilderEditorComponent },
    { path: 'shared/:code', component: TourBuilderSharedComponent },
  ]
},

// Phase E: Extended
{ path: 'packing-list/:tripId', component: PackingListComponent, canActivate: [authGuard] },
{ path: 'travel-buddies', component: TravelBuddiesComponent, canActivate: [authGuard] },
```

---

## 11. Admin Panel — CRUD cho tất cả features mới

> Phần này mô tả đầy đủ các trang admin cần tạo mới để quản lý Flight, Hotel,
> Transport, Tour Sessions, Custom Tours, Buddy Profiles, Group Trips.
> Tất cả đều theo pattern hiện tại của project (table + modal CRUD + filter).

### 11.0 Admin Pattern Recap (theo codebase hiện tại)

```
Pattern chung mỗi admin module:
├── Frontend: pages/admin/<feature>-list/
│   ├── HTML:  stat cards → filter bar → data table → CRUD modals
│   ├── TS:    loadItems, applyFilters, openAddModal, saveItem, deleteItem
│   └── SCSS:  TailwindCSS (không cần file riêng)
├── Frontend: services/admin/admin-<feature>.service.ts
│   └── CRUD methods → fetch/HttpClient → API
├── Backend: app/v1/api/endpoints/admin_<feature>.py
│   └── GET list, GET detail, POST create, PUT update, DELETE
├── Backend: app/v1/services/admin_<feature>_service.py
│   └── Business logic → Supabase queries
└── Backend: app/v1/schema/<feature>_schema.py
    └── Pydantic request/response models
```

**Response format chuẩn** (từ codebase hiện tại):
```json
{ "EC": 0, "EM": "Success", "data": { ... } }
```

---

### 11.1 Admin — Quản lý Flight Bookings

#### Backend

```python
# Backend/app/v1/api/endpoints/admin_flights.py

from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Dict
from ...services.admin_flight_service import AdminFlightService
from ...core.dependencies import get_current_admin

router = APIRouter(prefix="/admin/flights", tags=["Admin — Flights"])

@router.get("")
async def list_flight_bookings(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = None,
    airline: str | None = None,
    origin: str | None = None,
    destination: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str | None = None,
    admin: Dict = Depends(get_current_admin),
):
    service = AdminFlightService()
    result = service.get_flight_bookings(
        page=page, limit=limit, status=status, airline=airline,
        origin=origin, destination=destination,
        date_from=date_from, date_to=date_to, search=search,
    )
    return result

@router.get("/stats")
async def flight_stats(admin: Dict = Depends(get_current_admin)):
    service = AdminFlightService()
    return service.get_flight_stats()

@router.get("/{booking_id}")
async def get_flight_detail(
    booking_id: str,
    admin: Dict = Depends(get_current_admin),
):
    service = AdminFlightService()
    result = service.get_flight_booking_detail(booking_id)
    if result["EC"] == 1:
        raise HTTPException(status_code=404, detail=result["EM"])
    return result

@router.put("/{booking_id}/status")
async def update_flight_status(
    booking_id: str,
    status: str,  # pending, confirmed, cancelled, completed
    admin: Dict = Depends(get_current_admin),
):
    service = AdminFlightService()
    return service.update_flight_status(booking_id, status)

@router.delete("/{booking_id}")
async def delete_flight_booking(
    booking_id: str,
    admin: Dict = Depends(get_current_admin),
):
    service = AdminFlightService()
    return service.delete_flight_booking(booking_id)

@router.post("/price-alerts")
async def manage_price_alerts(
    admin: Dict = Depends(get_current_admin),
):
    """Xem và quản lý price alerts của user."""
    service = AdminFlightService()
    return service.get_all_price_alerts()
```

```python
# Backend/app/v1/services/admin_flight_service.py

class AdminFlightService:

    def get_flight_bookings(self, **filters) -> dict:
        query = self.supabase.table("flight_bookings").select(
            "*, users(full_name, email)"
        ).order("created_at", desc=True)

        if filters.get("status"):
            query = query.eq("status", filters["status"])
        if filters.get("airline"):
            query = query.eq("airline", filters["airline"])
        if filters.get("origin"):
            query = query.eq("origin", filters["origin"])
        if filters.get("destination"):
            query = query.eq("destination", filters["destination"])
        if filters.get("date_from"):
            query = query.gte("departure_time", filters["date_from"])
        if filters.get("date_to"):
            query = query.lte("departure_time", filters["date_to"])

        page = filters.get("page", 1)
        limit = filters.get("limit", 20)
        start = (page - 1) * limit
        result = query.range(start, start + limit - 1).execute()

        total = self.supabase.table("flight_bookings").select(
            "booking_id", count="exact"
        ).execute().count

        return {
            "EC": 0,
            "EM": "Success",
            "data": {
                "bookings": result.data,
                "total": total,
                "page": page,
                "limit": limit,
            }
        }

    def get_flight_stats(self) -> dict:
        """Thống kê flight bookings cho dashboard."""
        all_bookings = self.supabase.table("flight_bookings").select(
            "status, total_amount, currency, created_at"
        ).execute().data

        return {
            "EC": 0,
            "data": {
                "total_bookings": len(all_bookings),
                "confirmed": len([b for b in all_bookings if b["status"] == "confirmed"]),
                "pending": len([b for b in all_bookings if b["status"] == "pending"]),
                "cancelled": len([b for b in all_bookings if b["status"] == "cancelled"]),
                "total_revenue": sum(
                    float(b["total_amount"]) for b in all_bookings if b["status"] == "confirmed"
                ),
            }
        }

    def update_flight_status(self, booking_id: str, status: str) -> dict:
        valid = ["pending", "confirmed", "cancelled", "completed"]
        if status not in valid:
            return {"EC": 2, "EM": f"Invalid status. Must be: {', '.join(valid)}"}

        result = self.supabase.table("flight_bookings").update(
            {"status": status}
        ).eq("booking_id", booking_id).execute()

        if not result.data:
            return {"EC": 1, "EM": "Flight booking not found"}
        return {"EC": 0, "EM": "Status updated", "data": result.data[0]}

    def delete_flight_booking(self, booking_id: str) -> dict:
        result = self.supabase.table("flight_bookings").delete().eq(
            "booking_id", booking_id
        ).execute()
        if not result.data:
            return {"EC": 1, "EM": "Flight booking not found"}
        return {"EC": 0, "EM": "Deleted successfully"}
```

#### Frontend Service

```typescript
// Frontend/src/app/services/admin/admin-flight.service.ts

import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { ConfigService } from '../config.service';

@Injectable({ providedIn: 'root' })
export class AdminFlightService {
  constructor(private http: HttpClient, private config: ConfigService) {}

  private get url() { return `${this.config.getApiUrl()}/admin/flights`; }
  private headers() {
    return new HttpHeaders({
      'Content-Type': 'application/json',
      Authorization: `Bearer ${localStorage.getItem('access_token')}`,
    });
  }

  getBookings(params?: Record<string, string | number>) {
    return this.http.get(this.url, { headers: this.headers(), params });
  }

  getStats() {
    return this.http.get(`${this.url}/stats`, { headers: this.headers() });
  }

  getDetail(bookingId: string) {
    return this.http.get(`${this.url}/${bookingId}`, { headers: this.headers() });
  }

  updateStatus(bookingId: string, status: string) {
    return this.http.put(`${this.url}/${bookingId}/status`, { status }, { headers: this.headers() });
  }

  deleteBooking(bookingId: string) {
    return this.http.delete(`${this.url}/${bookingId}`, { headers: this.headers() });
  }
}
```

#### Frontend Component

```typescript
// Frontend/src/app/pages/admin/flight-booking-list/flight-booking-list.component.ts

import { Component, OnInit } from '@angular/core';
import { AdminFlightService } from '../../../services/admin/admin-flight.service';

@Component({
  selector: 'app-admin-flight-bookings',
  templateUrl: './flight-booking-list.component.html',
  standalone: true,
})
export class AdminFlightBookingListComponent implements OnInit {
  bookings: any[] = [];
  filteredBookings: any[] = [];
  isLoading = false;

  // Filters
  searchTerm = '';
  statusFilter = '';
  airlineFilter = '';

  // Stats
  stats = { total_bookings: 0, confirmed: 0, pending: 0, cancelled: 0, total_revenue: 0 };

  // Modals
  showDetailModal = false;
  showDeleteModal = false;
  selectedBooking: any = null;

  // Pagination
  page = 1;
  total = 0;
  limit = 20;

  constructor(private flightService: AdminFlightService) {}

  ngOnInit() {
    this.loadData();
  }

  async loadData() {
    this.isLoading = true;
    try {
      const [bookingsRes, statsRes]: any[] = await Promise.all([
        this.flightService.getBookings({ page: this.page, limit: this.limit }).toPromise(),
        this.flightService.getStats().toPromise(),
      ]);
      if (bookingsRes?.EC === 0) {
        this.bookings = bookingsRes.data.bookings;
        this.total = bookingsRes.data.total;
        this.applyFilters();
      }
      if (statsRes?.EC === 0) {
        this.stats = statsRes.data;
      }
    } finally {
      this.isLoading = false;
    }
  }

  applyFilters() {
    this.filteredBookings = this.bookings.filter(b => {
      const matchSearch = !this.searchTerm
        || b.users?.full_name?.toLowerCase().includes(this.searchTerm.toLowerCase())
        || b.booking_id?.includes(this.searchTerm);
      const matchStatus = !this.statusFilter || b.status === this.statusFilter;
      const matchAirline = !this.airlineFilter || b.airline === this.airlineFilter;
      return matchSearch && matchStatus && matchAirline;
    });
  }

  async updateStatus(bookingId: string, newStatus: string) {
    const res: any = await this.flightService.updateStatus(bookingId, newStatus).toPromise();
    if (res?.EC === 0) {
      this.loadData();
    }
  }

  openDetail(booking: any) {
    this.selectedBooking = booking;
    this.showDetailModal = true;
  }

  confirmDelete(booking: any) {
    this.selectedBooking = booking;
    this.showDeleteModal = true;
  }

  async deleteBooking() {
    const res: any = await this.flightService.deleteBooking(this.selectedBooking.booking_id).toPromise();
    if (res?.EC === 0) {
      this.showDeleteModal = false;
      this.loadData();
    }
  }

  formatPrice(price: number): string {
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(price);
  }

  getStatusBadge(status: string): string {
    const map: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-800',
      confirmed: 'bg-green-100 text-green-800',
      cancelled: 'bg-red-100 text-red-800',
      completed: 'bg-blue-100 text-blue-800',
    };
    return map[status] || 'bg-gray-100 text-gray-800';
  }
}
```

#### Template

```html
<!-- flight-booking-list.component.html -->
<div class="p-6">
  <!-- Stats Cards -->
  <div class="grid grid-cols-4 gap-4 mb-6">
    <div class="bg-gradient-to-r from-blue-500 to-blue-600 rounded-xl p-4 text-white">
      <p class="text-sm opacity-80">Tổng đặt vé</p>
      <p class="text-2xl font-bold">{{ stats.total_bookings }}</p>
    </div>
    <div class="bg-gradient-to-r from-green-500 to-green-600 rounded-xl p-4 text-white">
      <p class="text-sm opacity-80">Đã xác nhận</p>
      <p class="text-2xl font-bold">{{ stats.confirmed }}</p>
    </div>
    <div class="bg-gradient-to-r from-yellow-500 to-yellow-600 rounded-xl p-4 text-white">
      <p class="text-sm opacity-80">Chờ xử lý</p>
      <p class="text-2xl font-bold">{{ stats.pending }}</p>
    </div>
    <div class="bg-gradient-to-r from-purple-500 to-purple-600 rounded-xl p-4 text-white">
      <p class="text-sm opacity-80">Doanh thu</p>
      <p class="text-2xl font-bold">{{ formatPrice(stats.total_revenue) }}</p>
    </div>
  </div>

  <!-- Filters -->
  <div class="bg-white rounded-lg shadow-lg p-6 mb-6">
    <div class="flex gap-4 items-center">
      <input [(ngModel)]="searchTerm" (ngModelChange)="applyFilters()"
             placeholder="Tìm theo tên, mã booking..."
             class="border rounded-lg px-4 py-2 flex-1">
      <select [(ngModel)]="statusFilter" (ngModelChange)="applyFilters()"
              class="border rounded-lg px-4 py-2">
        <option value="">Tất cả trạng thái</option>
        <option value="pending">Chờ xử lý</option>
        <option value="confirmed">Đã xác nhận</option>
        <option value="cancelled">Đã hủy</option>
        <option value="completed">Hoàn thành</option>
      </select>
    </div>
  </div>

  <!-- Table -->
  <div class="bg-white rounded-lg shadow overflow-hidden">
    <table class="w-full">
      <thead class="bg-gray-50">
        <tr>
          <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Mã</th>
          <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Hành khách</th>
          <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tuyến</th>
          <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Hãng</th>
          <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ngày bay</th>
          <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tổng tiền</th>
          <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Trạng thái</th>
          <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Thao tác</th>
        </tr>
      </thead>
      <tbody class="bg-white divide-y divide-gray-200">
        <tr *ngFor="let b of filteredBookings" class="hover:bg-gray-50">
          <td class="px-6 py-4 text-sm font-mono">{{ b.booking_id?.slice(0,8) }}</td>
          <td class="px-6 py-4 text-sm">{{ b.users?.full_name }}</td>
          <td class="px-6 py-4 text-sm">{{ b.origin }} → {{ b.destination }}</td>
          <td class="px-6 py-4 text-sm">{{ b.airline }}</td>
          <td class="px-6 py-4 text-sm">{{ b.departure_time | date:'dd/MM/yyyy HH:mm' }}</td>
          <td class="px-6 py-4 text-sm font-medium">{{ formatPrice(b.total_amount) }}</td>
          <td class="px-6 py-4">
            <span [class]="getStatusBadge(b.status)" class="px-2 py-1 rounded-full text-xs font-medium">
              {{ b.status }}
            </span>
          </td>
          <td class="px-6 py-4 text-sm">
            <button (click)="openDetail(b)" class="text-blue-600 hover:text-blue-800 mr-2">Chi tiết</button>
            <button (click)="confirmDelete(b)" class="text-red-600 hover:text-red-800">Xóa</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</div>

<!-- Detail Modal -->
<div *ngIf="showDetailModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
  <div class="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
    <div class="px-6 py-4 border-b flex justify-between items-center">
      <h3 class="text-lg font-semibold">Chi tiết đặt vé</h3>
      <button (click)="showDetailModal = false" class="text-gray-400 hover:text-gray-600">✕</button>
    </div>
    <div class="p-6" *ngIf="selectedBooking">
      <!-- Flight info -->
      <div class="grid grid-cols-2 gap-4">
        <div><span class="text-gray-500">Tuyến:</span> {{ selectedBooking.origin }} → {{ selectedBooking.destination }}</div>
        <div><span class="text-gray-500">Hãng:</span> {{ selectedBooking.airline }}</div>
        <div><span class="text-gray-500">Khởi hành:</span> {{ selectedBooking.departure_time | date:'dd/MM/yyyy HH:mm' }}</div>
        <div><span class="text-gray-500">Đến:</span> {{ selectedBooking.arrival_time | date:'dd/MM/yyyy HH:mm' }}</div>
        <div><span class="text-gray-500">Tổng tiền:</span> {{ formatPrice(selectedBooking.total_amount) }}</div>
        <div><span class="text-gray-500">Trạng thái:</span> {{ selectedBooking.status }}</div>
      </div>

      <!-- Passengers JSON -->
      <div class="mt-4">
        <h4 class="font-medium mb-2">Hành khách</h4>
        <pre class="bg-gray-50 p-3 rounded text-sm">{{ selectedBooking.passengers | json }}</pre>
      </div>

      <!-- Status change -->
      <div class="mt-4 flex gap-2">
        <span class="text-gray-500 self-center mr-2">Đổi trạng thái:</span>
        <button (click)="updateStatus(selectedBooking.booking_id, 'confirmed')"
                class="px-3 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200">Xác nhận</button>
        <button (click)="updateStatus(selectedBooking.booking_id, 'cancelled')"
                class="px-3 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200">Hủy</button>
        <button (click)="updateStatus(selectedBooking.booking_id, 'completed')"
                class="px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200">Hoàn thành</button>
      </div>
    </div>
  </div>
</div>

<!-- Delete Confirmation Modal (same pattern as existing) -->
<div *ngIf="showDeleteModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
  <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6 text-center">
    <div class="mx-auto w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mb-4">
      <span class="text-red-600 text-xl">!</span>
    </div>
    <h3 class="text-lg font-medium mb-2">Xác nhận xóa</h3>
    <p class="text-sm text-gray-500 mb-4">Bạn có chắc muốn xóa booking {{ selectedBooking?.booking_id?.slice(0,8) }}?</p>
    <div class="flex gap-3 justify-center">
      <button (click)="showDeleteModal = false" class="px-4 py-2 border rounded-lg hover:bg-gray-50">Hủy</button>
      <button (click)="deleteBooking()" class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700">Xóa</button>
    </div>
  </div>
</div>
```

---

### 11.2 Admin — Quản lý Hotel Bookings

Cùng pattern với Flight Bookings. Chỉ khác filters và columns.

#### Backend Endpoints

```python
# Backend/app/v1/api/endpoints/admin_hotels.py

router = APIRouter(prefix="/admin/hotels", tags=["Admin — Hotels"])

@router.get("")           # list + filter by status, hotel_name, checkin_date range, search
@router.get("/stats")     # total bookings, revenue, avg nights, occupancy
@router.get("/{booking_id}")   # detail with guest info
@router.put("/{booking_id}/status")  # update status
@router.delete("/{booking_id}")      # delete
```

#### Frontend Columns

| Column | Hiển thị |
|---|---|
| Mã booking | `booking_id.slice(0,8)` |
| Khách hàng | `users.full_name` |
| Khách sạn | `hotel_name` |
| Check-in / Check-out | `checkin_date` → `checkout_date` |
| Số phòng | `rooms` |
| Tổng tiền | `total_amount` formatted VND |
| Trạng thái | Badge (pending/confirmed/cancelled/completed) |
| Thao tác | Chi tiết | Đổi trạng thái | Xóa |

---

### 11.3 Admin — Quản lý Transport Bookings

```python
# Backend/app/v1/api/endpoints/admin_transport.py

router = APIRouter(prefix="/admin/transport", tags=["Admin — Transport"])

@router.get("")           # list + filter by status, transport_type, route, search
@router.get("/stats")     # total, by type breakdown, revenue
@router.get("/{booking_id}")
@router.put("/{booking_id}/status")
@router.delete("/{booking_id}")
```

#### Frontend Columns

| Column | Hiển thị |
|---|---|
| Mã booking | Short ID |
| Khách hàng | `users.full_name` |
| Loại | Badge màu theo `transport_type` (bus=blue, train=green, ferry=cyan, van=orange) |
| Tuyến | `origin` → `destination` |
| Khởi hành | `departure_time` formatted |
| Ghế | `seat_numbers` array |
| Tổng tiền | VND formatted |
| Trạng thái | Badge |

---

### 11.4 Admin — Quản lý Tour Sessions (Quan trọng nhất)

Đây là module admin quan trọng nhất vì đây là dữ liệu cốt lõi cho Tour Builder.

#### Backend

```python
# Backend/app/v1/api/endpoints/admin_tour_sessions.py

from fastapi import APIRouter, Depends, UploadFile, File
from typing import Dict
from ...services.admin_tour_session_service import AdminTourSessionService
from ...core.dependencies import get_current_admin

router = APIRouter(prefix="/admin/tour-sessions", tags=["Admin — Tour Sessions"])

@router.get("")
async def list_tour_sessions(
    page: int = 1,
    limit: int = 20,
    destination: str | None = None,
    category: str | None = None,
    session_type: str | None = None,  # morning, afternoon, evening, fullday
    is_active: bool | None = None,
    search: str | None = None,
    admin: Dict = Depends(get_current_admin),
):
    service = AdminTourSessionService()
    return service.get_sessions(
        page=page, limit=limit, destination=destination,
        category=category, session_type=session_type,
        is_active=is_active, search=search,
    )

@router.get("/stats")
async def session_stats(admin: Dict = Depends(get_current_admin)):
    """Thống kê sessions: total by destination, by category, avg rating."""
    service = AdminTourSessionService()
    return service.get_session_stats()

@router.get("/destinations")
async def list_destinations(admin: Dict = Depends(get_current_admin)):
    """Lấy danh sách tất cả destination có sessions (cho filter dropdown)."""
    service = AdminTourSessionService()
    return service.get_destinations()

@router.get("/{session_id}")
async def get_session_detail(
    session_id: str,
    admin: Dict = Depends(get_current_admin),
):
    service = AdminTourSessionService()
    return service.get_session_detail(session_id)

@router.post("")
async def create_tour_session(
    request: CreateTourSessionRequest,
    admin: Dict = Depends(get_current_admin),
):
    """Tạo session mới."""
    service = AdminTourSessionService()
    return service.create_session(request.dict())

@router.post("/bulk")
async def bulk_create_sessions(
    request: BulkCreateSessionsRequest,
    admin: Dict = Depends(get_current_admin),
):
    """Tạo nhiều sessions cùng lúc (vd: import cho 1 destination)."""
    service = AdminTourSessionService()
    return service.bulk_create(request.dict())

@router.put("/{session_id}")
async def update_tour_session(
    session_id: str,
    request: UpdateTourSessionRequest,
    admin: Dict = Depends(get_current_admin),
):
    service = AdminTourSessionService()
    return service.update_session(session_id, request.dict())

@router.put("/{session_id}/toggle-active")
async def toggle_session_active(
    session_id: str,
    admin: Dict = Depends(get_current_admin),
):
    """Bật/tắt session (ẩn/hiện cho user)."""
    service = AdminTourSessionService()
    return service.toggle_active(session_id)

@router.post("/{session_id}/images")
async def upload_session_images(
    session_id: str,
    files: list[UploadFile] = File(...),
    admin: Dict = Depends(get_current_admin),
):
    """Upload ảnh cho session (lên Cloudinary)."""
    service = AdminTourSessionService()
    return service.upload_images(session_id, files)

@router.delete("/{session_id}")
async def delete_tour_session(
    session_id: str,
    admin: Dict = Depends(get_current_admin),
):
    service = AdminTourSessionService()
    return service.delete_session(session_id)

@router.get("/conflicts/check")
async def check_session_conflicts(
    session_a: str,
    session_b: str,
    admin: Dict = Depends(get_current_admin),
):
    """Kiểm tra 2 sessions có conflict không."""
    service = AdminTourSessionService()
    return service.check_conflict(session_a, session_b)

@router.post("/conflicts")
async def add_conflict_rule(
    request: AddConflictRequest,
    admin: Dict = Depends(get_current_admin),
):
    """Thêm rule conflict giữa 2 sessions."""
    service = AdminTourSessionService()
    return service.add_conflict_rule(request.dict())
```

```python
# Backend/app/v1/services/admin_tour_session_service.py

import json
from openai import AsyncOpenAI

class AdminTourSessionService:

    def get_sessions(self, **filters) -> dict:
        query = self.supabase.table("tour_sessions").select("*").order("created_at", desc=True)

        if filters.get("destination"):
            query = query.eq("destination", filters["destination"])
        if filters.get("category"):
            query = query.eq("category", filters["category"])
        if filters.get("session_type"):
            query = query.eq("session_type", filters["session_type"])
        if filters.get("is_active") is not None:
            query = query.eq("is_active", filters["is_active"])

        page = filters.get("page", 1)
        limit = filters.get("limit", 20)
        result = query.range((page - 1) * limit, page * limit - 1).execute()

        return {"EC": 0, "EM": "Success", "data": result.data}

    def get_session_stats(self) -> dict:
        all_sessions = self.supabase.table("tour_sessions").select(
            "destination, category, is_active, rating"
        ).execute().data

        # Group by destination
        by_destination = {}
        for s in all_sessions:
            dest = s["destination"]
            by_destination.setdefault(dest, {"total": 0, "active": 0, "avg_rating": 0})
            by_destination[dest]["total"] += 1
            if s["is_active"]:
                by_destination[dest]["active"] += 1

        # Calculate avg ratings
        for dest in by_destination:
            dest_sessions = [s for s in all_sessions if s["destination"] == dest]
            by_destination[dest]["avg_rating"] = round(
                sum(float(s["rating"]) for s in dest_sessions) / len(dest_sessions), 1
            )

        return {
            "EC": 0,
            "data": {
                "total_sessions": len(all_sessions),
                "active_sessions": len([s for s in all_sessions if s["is_active"]]),
                "by_destination": by_destination,
                "by_category": {
                    cat: len([s for s in all_sessions if s["category"] == cat])
                    for cat in set(s["category"] for s in all_sessions)
                },
            }
        }

    def get_destinations(self) -> dict:
        result = self.supabase.table("tour_sessions").select("destination").execute()
        destinations = sorted(set(s["destination"] for s in result.data))
        return {"EC": 0, "data": destinations}

    def create_session(self, data: dict) -> dict:
        # Auto-generate embedding for AI search
        embedding_text = f"{data['name']} {data.get('destination', '')} {data.get('category', '')} {data.get('description', '')}"
        # embedding = self._generate_embedding(embedding_text)  # uncomment khi cần

        result = self.supabase.table("tour_sessions").insert(data).execute()
        return {"EC": 0, "EM": "Session created", "data": result.data[0]}

    def update_session(self, session_id: str, data: dict) -> dict:
        result = self.supabase.table("tour_sessions").update(data).eq(
            "session_id", session_id
        ).execute()
        if not result.data:
            return {"EC": 1, "EM": "Session not found"}
        return {"EC": 0, "EM": "Updated", "data": result.data[0]}

    def toggle_active(self, session_id: str) -> dict:
        current = self.supabase.table("tour_sessions").select("is_active").eq(
            "session_id", session_id
        ).execute()
        if not current.data:
            return {"EC": 1, "EM": "Session not found"}

        new_status = not current.data[0]["is_active"]
        self.supabase.table("tour_sessions").update(
            {"is_active": new_status}
        ).eq("session_id", session_id).execute()

        return {"EC": 0, "EM": f"Session {'activated' if new_status else 'deactivated'}"}

    def delete_session(self, session_id: str) -> dict:
        # Check if used in any custom tour
        usage = self.supabase.table("custom_tour_sessions").select("id").eq(
            "session_id", session_id
        ).execute()
        if usage.data:
            return {"EC": 2, "EM": f"Cannot delete: session is used in {len(usage.data)} custom tours. Deactivate instead."}

        self.supabase.table("tour_sessions").delete().eq("session_id", session_id).execute()
        return {"EC": 0, "EM": "Deleted"}

    def upload_images(self, session_id: str, files) -> dict:
        # Upload to Cloudinary (same pattern as tour package images)
        urls = []
        for file in files:
            # upload_to_cloudinary(file) → url
            pass

        self.supabase.table("tour_sessions").update(
            {"image_urls": urls}
        ).eq("session_id", session_id).execute()

        return {"EC": 0, "EM": "Images uploaded", "data": {"urls": urls}}
```

#### Frontend — Session List Component

```typescript
// Frontend/src/app/pages/admin/session-list/session-list.component.ts

import { Component, OnInit } from '@angular/core';
import { AdminTourSessionService } from '../../../services/admin/admin-tour-session.service';

@Component({
  selector: 'app-admin-sessions',
  templateUrl: './session-list.component.html',
  standalone: true,
})
export class AdminSessionListComponent implements OnInit {
  sessions: any[] = [];
  filteredSessions: any[] = [];
  isLoading = false;

  // Filters
  searchTerm = '';
  destinationFilter = '';
  categoryFilter = '';
  typeFilter = '';  // morning/afternoon/evening/fullday
  activeFilter = '';  // all/active/inactive

  destinations: string[] = [];
  categories = ['adventure', 'food', 'culture', 'nature', 'nightlife', 'shopping'];
  sessionTypes = ['morning', 'afternoon', 'evening', 'fullday'];

  // Stats
  stats: any = {};

  // Modals
  showAddModal = false;
  showEditModal = false;
  showDeleteModal = false;
  showDetailModal = false;
  selectedSession: any = null;

  // Form model
  formData = {
    name: '',
    destination: '',
    session_type: 'morning',
    category: 'adventure',
    description: '',
    duration_minutes: 180,
    price: 0,
    meeting_point: '',
    included_items: [] as string[],
    requirements: [] as string[],
    min_participants: 1,
    max_participants: 50,
  };

  constructor(private sessionService: AdminTourSessionService) {}

  ngOnInit() {
    this.loadData();
  }

  async loadData() {
    this.isLoading = true;
    try {
      const [sessionsRes, statsRes, destRes]: any[] = await Promise.all([
        this.sessionService.getSessions().toPromise(),
        this.sessionService.getStats().toPromise(),
        this.sessionService.getDestinations().toPromise(),
      ]);
      if (sessionsRes?.EC === 0) this.sessions = sessionsRes.data;
      if (statsRes?.EC === 0) this.stats = statsRes.data;
      if (destRes?.EC === 0) this.destinations = destRes.data;
      this.applyFilters();
    } finally {
      this.isLoading = false;
    }
  }

  applyFilters() {
    this.filteredSessions = this.sessions.filter(s => {
      const matchSearch = !this.searchTerm
        || s.name?.toLowerCase().includes(this.searchTerm.toLowerCase());
      const matchDest = !this.destinationFilter || s.destination === this.destinationFilter;
      const matchCat = !this.categoryFilter || s.category === this.categoryFilter;
      const matchType = !this.typeFilter || s.session_type === this.typeFilter;
      const matchActive = this.activeFilter === 'active' ? s.is_active
        : this.activeFilter === 'inactive' ? !s.is_active : true;
      return matchSearch && matchDest && matchCat && matchType && matchActive;
    });
  }

  openAddModal() {
    this.formData = {
      name: '', destination: '', session_type: 'morning', category: 'adventure',
      description: '', duration_minutes: 180, price: 0, meeting_point: '',
      included_items: [], requirements: [], min_participants: 1, max_participants: 50,
    };
    this.showAddModal = true;
  }

  openEditModal(session: any) {
    this.formData = { ...session };
    this.selectedSession = session;
    this.showEditModal = true;
  }

  async saveSession() {
    const res: any = this.showAddModal
      ? await this.sessionService.createSession(this.formData).toPromise()
      : await this.sessionService.updateSession(this.selectedSession.session_id, this.formData).toPromise();

    if (res?.EC === 0) {
      this.showAddModal = false;
      this.showEditModal = false;
      this.loadData();
    }
  }

  async toggleActive(session: any) {
    const res: any = await this.sessionService.toggleActive(session.session_id).toPromise();
    if (res?.EC === 0) this.loadData();
  }

  confirmDelete(session: any) {
    this.selectedSession = session;
    this.showDeleteModal = true;
  }

  async deleteSession() {
    const res: any = await this.sessionService.deleteSession(this.selectedSession.session_id).toPromise();
    if (res?.EC === 0) {
      this.showDeleteModal = false;
      this.loadData();
    }
  }
}
```

#### Template

```html
<!-- session-list.component.html -->
<div class="p-6">
  <!-- Stats -->
  <div class="grid grid-cols-4 gap-4 mb-6">
    <div class="bg-gradient-to-r from-indigo-500 to-indigo-600 rounded-xl p-4 text-white">
      <p class="text-sm opacity-80">Tổng sessions</p>
      <p class="text-2xl font-bold">{{ stats.total_sessions || 0 }}</p>
    </div>
    <div class="bg-gradient-to-r from-green-500 to-green-600 rounded-xl p-4 text-white">
      <p class="text-sm opacity-80">Đang hoạt động</p>
      <p class="text-2xl font-bold">{{ stats.active_sessions || 0 }}</p>
    </div>
    <div class="bg-gradient-to-r from-orange-500 to-orange-600 rounded-xl p-4 text-white">
      <p class="text-sm opacity-80">Điểm đến</p>
      <p class="text-2xl font-bold">{{ destinations.length }}</p>
    </div>
    <div class="bg-gradient-to-r from-purple-500 to-purple-600 rounded-xl p-4 text-white">
      <p class="text-sm opacity-80">Danh mục</p>
      <p class="text-2xl font-bold">{{ categories.length }}</p>
    </div>
  </div>

  <!-- Toolbar -->
  <div class="flex justify-between items-center mb-4">
    <div class="flex gap-3 flex-1">
      <input [(ngModel)]="searchTerm" (ngModelChange)="applyFilters()"
             placeholder="Tìm session..." class="border rounded-lg px-4 py-2 flex-1">
      <select [(ngModel)]="destinationFilter" (ngModelChange)="applyFilters()"
              class="border rounded-lg px-4 py-2">
        <option value="">Tất cả điểm đến</option>
        <option *ngFor="let d of destinations" [value]="d">{{ d }}</option>
      </select>
      <select [(ngModel)]="categoryFilter" (ngModelChange)="applyFilters()"
              class="border rounded-lg px-4 py-2">
        <option value="">Tất cả danh mục</option>
        <option *ngFor="let c of categories" [value]="c">{{ c }}</option>
      </select>
      <select [(ngModel)]="typeFilter" (ngModelChange)="applyFilters()"
              class="border rounded-lg px-4 py-2">
        <option value="">Tất cả buổi</option>
        <option *ngFor="let t of sessionTypes" [value]="t">{{ t }}</option>
      </select>
      <select [(ngModel)]="activeFilter" (ngModelChange)="applyFilters()"
              class="border rounded-lg px-4 py-2">
        <option value="">Tất cả trạng thái</option>
        <option value="active">Đang hoạt động</option>
        <option value="inactive">Đã ẩn</option>
      </select>
    </div>
    <button (click)="openAddModal()"
            class="ml-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
      + Thêm Session
    </button>
  </div>

  <!-- Table -->
  <div class="bg-white rounded-lg shadow overflow-hidden">
    <table class="w-full">
      <thead class="bg-gray-50">
        <tr>
          <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tên</th>
          <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Điểm đến</th>
          <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Buổi</th>
          <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Danh mục</th>
          <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Thời lượng</th>
          <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Giá</th>
          <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Rating</th>
          <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Trạng thái</th>
          <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Thao tác</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-gray-200">
        <tr *ngFor="let s of filteredSessions" class="hover:bg-gray-50">
          <td class="px-4 py-3">
            <div class="flex items-center gap-2">
              <img *ngIf="s.image_urls?.[0]" [src]="s.image_urls[0]" class="w-10 h-10 rounded object-cover">
              <span class="text-sm font-medium">{{ s.name }}</span>
            </div>
          </td>
          <td class="px-4 py-3 text-sm">{{ s.destination }}</td>
          <td class="px-4 py-3">
            <span class="px-2 py-1 rounded text-xs font-medium"
                  [class]="s.session_type === 'morning' ? 'bg-yellow-100 text-yellow-700'
                         : s.session_type === 'afternoon' ? 'bg-orange-100 text-orange-700'
                         : s.session_type === 'evening' ? 'bg-indigo-100 text-indigo-700'
                         : 'bg-blue-100 text-blue-700'">
              {{ s.session_type }}
            </span>
          </td>
          <td class="px-4 py-3 text-sm">{{ s.category }}</td>
          <td class="px-4 py-3 text-sm">{{ s.duration_minutes }} phút</td>
          <td class="px-4 py-3 text-sm font-medium">{{ formatPrice(s.price) }}</td>
          <td class="px-4 py-3 text-sm">{{ s.rating }} ({{ s.review_count }})</td>
          <td class="px-4 py-3">
            <button (click)="toggleActive(s)"
                    [class]="s.is_active ? 'text-green-600' : 'text-gray-400'"
                    class="text-sm hover:underline">
              {{ s.is_active ? 'Hoạt động' : 'Đã ẩn' }}
            </button>
          </td>
          <td class="px-4 py-3 text-sm">
            <button (click)="openEditModal(s)" class="text-blue-600 hover:text-blue-800 mr-2">Sửa</button>
            <button (click)="confirmDelete(s)" class="text-red-600 hover:text-red-800">Xóa</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</div>

<!-- Add/Edit Modal -->
<div *ngIf="showAddModal || showEditModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
  <div class="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[95vh] overflow-hidden">
    <div class="px-6 py-4 border-b">
      <h3 class="text-lg font-semibold">{{ showAddModal ? 'Thêm Session mới' : 'Chỉnh sửa Session' }}</h3>
    </div>
    <div class="overflow-y-auto p-6">
      <!-- Basic Info -->
      <div class="grid grid-cols-2 gap-6 mb-6">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Tên hoạt động *</label>
          <input [(ngModel)]="formData.name" class="w-full border rounded-lg px-3 py-2"
                 placeholder="vd: Khám phá Đồi Cỏ Hồng buổi sáng">
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Điểm đến *</label>
          <input [(ngModel)]="formData.destination" class="w-full border rounded-lg px-3 py-2"
                 placeholder="vd: Đà Lạt" list="dest-list">
          <datalist id="dest-list">
            <option *ngFor="let d of destinations" [value]="d">
          </datalist>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Buổi *</label>
          <select [(ngModel)]="formData.session_type" class="w-full border rounded-lg px-3 py-2">
            <option value="morning">Buổi sáng</option>
            <option value="afternoon">Buổi trưa</option>
            <option value="evening">Buổi tối</option>
            <option value="fullday">Cả ngày</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Danh mục *</label>
          <select [(ngModel)]="formData.category" class="w-full border rounded-lg px-3 py-2">
            <option *ngFor="let c of categories" [value]="c">{{ c }}</option>
          </select>
        </div>
      </div>

      <!-- Description -->
      <div class="mb-6">
        <label class="block text-sm font-medium text-gray-700 mb-1">Mô tả</label>
        <textarea [(ngModel)]="formData.description" rows="3"
                  class="w-full border rounded-lg px-3 py-2"></textarea>
      </div>

      <!-- Pricing & Duration -->
      <div class="grid grid-cols-3 gap-6 mb-6">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Giá (VND) *</label>
          <input [(ngModel)]="formData.price" type="number" class="w-full border rounded-lg px-3 py-2">
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Thời lượng (phút) *</label>
          <input [(ngModel)]="formData.duration_minutes" type="number" class="w-full border rounded-lg px-3 py-2">
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Điểm tập kết</label>
          <input [(ngModel)]="formData.meeting_point" class="w-full border rounded-lg px-3 py-2"
                 placeholder="vd: Khách sạn XYZ">
        </div>
      </div>

      <!-- Participants -->
      <div class="grid grid-cols-2 gap-6 mb-6">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Số người tối thiểu</label>
          <input [(ngModel)]="formData.min_participants" type="number" class="w-full border rounded-lg px-3 py-2">
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Số người tối đa</label>
          <input [(ngModel)]="formData.max_participants" type="number" class="w-full border rounded-lg px-3 py-2">
        </div>
      </div>

      <!-- Images -->
      <div class="mb-6">
        <label class="block text-sm font-medium text-gray-700 mb-1">Hình ảnh</label>
        <input type="file" multiple accept="image/*" class="w-full border rounded-lg px-3 py-2">
      </div>
    </div>
    <div class="px-6 py-4 border-t bg-gray-50 flex justify-end gap-3">
      <button (click)="showAddModal = false; showEditModal = false"
              class="px-4 py-2 border rounded-lg hover:bg-gray-50">Hủy</button>
      <button (click)="saveSession()"
              class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
        {{ showAddModal ? 'Tạo Session' : 'Cập nhật' }}
      </button>
    </div>
  </div>
</div>

<!-- Delete Modal (same pattern) -->
```

---

### 11.5 Admin — Quản lý Custom Tours

```python
# Backend/app/v1/api/endpoints/admin_custom_tours.py

router = APIRouter(prefix="/admin/custom-tours", tags=["Admin — Custom Tours"])

@router.get("")            # list all custom tours by users
@router.get("/stats")      # total created, by status, most popular destinations
@router.get("/{tour_id}")  # detail: full itinerary with all sessions
@router.put("/{tour_id}/status")  # approve/reject featured tours
@router.delete("/{tour_id}")
@router.get("/featured")   # get tours marked as featured/public
@router.put("/{tour_id}/toggle-featured")  # toggle featured status
```

#### Frontend Columns

| Column | Hiển thị |
|---|---|
| Mã tour | Short ID |
| Tên tour | `tour_name` |
| User tạo | `users.full_name` |
| Điểm đến | `destination` |
| Ngày đi / Ngày về | Date range |
| Số buổi đã chọn | Count of sessions |
| Tổng giá | VND formatted |
| Trạng thái | draft / confirmed / completed / cancelled |
| Featured | Toggle star icon |
| Thao tác | Xem chi tiết | Toggle featured | Xóa |

**Detail modal đặc biệt:** Hiển thị timeline dạng calendar với các session đã chọn cho từng ngày/buổi — tương tự preview của user-side Tour Builder.

---

### 11.6 Admin — Quản lý Buddy Profiles & Group Trips

```python
# Backend/app/v1/api/endpoints/admin_community.py

router = APIRouter(prefix="/admin/community", tags=["Admin — Community"])

# Buddy Profiles
@router.get("/buddy-profiles")          # list all profiles
@router.get("/buddy-profiles/{user_id}")  # detail
@router.delete("/buddy-profiles/{user_id}")  # remove profile (violation)

# Group Trips
@router.get("/group-trips")             # list all group trips
@router.get("/group-trips/{trip_id}")   # detail with members
@router.put("/group-trips/{trip_id}/status")  # approve/close
@router.delete("/group-trips/{trip_id}")

# Match Requests
@router.get("/match-requests")          # list all match requests
@router.put("/match-requests/{request_id}")  # approve/reject (moderation)
```

---

### 11.7 Admin Sidebar — Menu Items Mới

Cập nhật sidebar navigation trong `Frontend/src/app/layouts/admin-layout/admin-layout.component.html`:

```typescript
// Booking domain (Phase A-D)
{ label: 'Ve may bay', icon: 'fa-plane', route: '/admin/flights', badge: stats.flightPending },
{ label: 'Khach san',  icon: 'fa-hotel', route: '/admin/hotels',  badge: stats.hotelPending },
{ label: 'Ve xe/tau',  icon: 'fa-bus',   route: '/admin/transport', badge: stats.transportPending },
{ label: 'Tour Sessions', icon: 'fa-puzzle-piece', route: '/admin/tour-sessions' },
{ label: 'Custom Tours',  icon: 'fa-map',          route: '/admin/custom-tours' },

// Community (Phase E - buddy / group)
{ label: 'Cong dong', icon: 'fa-users', route: '/admin/community',
  children: [
    { label: 'Buddy Profiles',  route: '/admin/community/buddy-profiles' },
    { label: 'Group Trips',     route: '/admin/community/group-trips' },
    { label: 'Match Requests',  route: '/admin/community/match-requests' },
  ],
},

// Multi-agent system (Section 14)
{ label: 'AI System', icon: 'fa-robot', route: '/admin/ai',
  children: [
    { label: 'Agent Control',  route: '/admin/ai/agents' },
    { label: 'Agent Runs',     route: '/admin/ai/runs' },
    { label: 'MCP Servers',    route: '/admin/ai/mcp' },
    { label: 'Intent Stats',   route: '/admin/ai/intent-stats' },
    { label: 'Itineraries',    route: '/admin/ai/itineraries' },
  ],
},

// Phase E priority features (Section 7.x)
{ label: 'Smart Features', icon: 'fa-bolt', route: '/admin/smart',
  children: [
    { label: 'Price Alerts',       route: '/admin/smart/price-alerts' },
    { label: 'Packing Templates',  route: '/admin/smart/packing-templates' },
    { label: 'Travel Stories',     route: '/admin/smart/travel-stories' },
    { label: 'Insurance Plans',    route: '/admin/smart/insurance-plans' },
    { label: 'Insurance Orders',   route: '/admin/smart/insurance-orders' },
  ],
},

// Security
{ label: 'Audit Log', icon: 'fa-shield', route: '/admin/audit-log' },
```

### 11.8 Admin Routes — Tổng hợp

```typescript
// pages/admin/admin.routes.ts - admin children them vao
{
  path: 'admin',
  component: AdminLayoutComponent,
  canActivate: [authGuard, adminGuard],
  children: [
    // existing routes (dashboard / tours / bookings / payments / customers / promotions / reviews / reports / cancellations / profile)
    // ... giu nguyen ...

    // Phase A-D booking domain
    { path: 'flights',       loadComponent: () => import('./flight-booking-list/flight-booking-list.component').then(m => m.AdminFlightBookingListComponent) },
    { path: 'hotels',        loadComponent: () => import('./hotel-booking-list/hotel-booking-list.component').then(m => m.AdminHotelBookingListComponent) },
    { path: 'transport',     loadComponent: () => import('./transport-booking-list/transport-booking-list.component').then(m => m.AdminTransportBookingListComponent) },
    { path: 'tour-sessions', loadComponent: () => import('./session-list/session-list.component').then(m => m.AdminSessionListComponent) },
    { path: 'custom-tours',  loadComponent: () => import('./custom-tour-list/custom-tour-list.component').then(m => m.AdminCustomTourListComponent) },

    // Community
    { path: 'community/buddy-profiles',  loadComponent: () => import('./buddy-profile-list/buddy-profile-list.component').then(m => m.AdminBuddyProfileListComponent) },
    { path: 'community/group-trips',     loadComponent: () => import('./group-trip-list/group-trip-list.component').then(m => m.AdminGroupTripListComponent) },
    { path: 'community/match-requests',  loadComponent: () => import('./match-request-list/match-request-list.component').then(m => m.AdminMatchRequestListComponent) },

    // Multi-agent system (Section 14)
    { path: 'ai/agents',        loadComponent: () => import('./agent-control/agent-control.component').then(m => m.AgentControlComponent) },
    { path: 'ai/runs',          loadComponent: () => import('./agent-runs/agent-runs.component').then(m => m.AgentRunsComponent) },
    { path: 'ai/runs/:runId',   loadComponent: () => import('./agent-run-detail/agent-run-detail.component').then(m => m.AgentRunDetailComponent) },
    { path: 'ai/mcp',           loadComponent: () => import('./mcp-servers/mcp-servers.component').then(m => m.McpServersComponent) },
    { path: 'ai/intent-stats',  loadComponent: () => import('./intent-stats/intent-stats.component').then(m => m.IntentStatsComponent) },
    { path: 'ai/itineraries',   loadComponent: () => import('./itinerary-list/itinerary-list.component').then(m => m.ItineraryListComponent) },

    // Phase E priority (Section 7.2 / 7.5 / 7.6 / 7.9)
    { path: 'smart/price-alerts',       loadComponent: () => import('./price-alert-list/price-alert-list.component').then(m => m.PriceAlertListComponent) },
    { path: 'smart/packing-templates',  loadComponent: () => import('./packing-template-list/packing-template-list.component').then(m => m.PackingTemplateListComponent) },
    { path: 'smart/travel-stories',     loadComponent: () => import('./travel-story-moderation/travel-story-moderation.component').then(m => m.TravelStoryModerationComponent) },
    { path: 'smart/insurance-plans',    loadComponent: () => import('./insurance-plan-list/insurance-plan-list.component').then(m => m.InsurancePlanListComponent) },
    { path: 'smart/insurance-orders',   loadComponent: () => import('./insurance-order-list/insurance-order-list.component').then(m => m.InsuranceOrderListComponent) },

    // Audit
    { path: 'audit-log',  loadComponent: () => import('./audit-log/audit-log.component').then(m => m.AuditLogComponent) },
  ],
}
```

---

### 11.9 Tổng hợp files cần tạo cho Admin

```
Backend/
├── app/v1/api/endpoints/
│   ├── admin_flights.py              # Phase A bookings CRUD
│   ├── admin_hotels.py               # Phase B
│   ├── admin_transport.py            # Phase C
│   ├── admin_tour_sessions.py        # Phase D sessions
│   ├── admin_custom_tours.py         # Phase D custom tours
│   ├── admin_community.py            # Buddy + Group + Match
│   ├── admin_agents.py               # 11.10 Multi-agent control + runs + intent stats
│   ├── admin_mcp.py                  # 11.10 MCP health + ping
│   ├── admin_itineraries.py          # 11.10 Itinerary mgmt
│   ├── admin_smart_features.py       # 11.11 Price / Packing / Story / Insurance
│   └── admin_audit_log.py            # Audit
├── app/v1/services/
│   ├── admin_flight_service.py
│   ├── admin_hotel_service.py
│   ├── admin_transport_service.py
│   ├── admin_tour_session_service.py
│   ├── admin_custom_tour_service.py
│   ├── admin_community_service.py
│   ├── admin_agent_service.py        # 11.10
│   ├── mcp_health_service.py         # 11.10 (ping/echo sub-server)
│   ├── admin_itinerary_service.py    # 11.10
│   ├── admin_price_alert_service.py  # 11.11
│   ├── admin_packing_template_service.py
│   ├── admin_travel_story_service.py
│   ├── admin_insurance_service.py
│   ├── admin_audit_log_service.py
│   └── agent_run_logger.py           # 11.10 LangGraph callback handler
└── app/v1/schema/
    ├── flight_schema.py
    ├── hotel_schema.py
    ├── transport_schema.py
    ├── tour_session_schema.py
    ├── custom_tour_schema.py
    ├── agent_config_schema.py        # 11.10
    ├── agent_run_schema.py           # 11.10
    ├── mcp_server_schema.py          # 11.10
    ├── itinerary_schema.py           # 11.10
    ├── price_alert_schema.py         # 11.11
    ├── packing_template_schema.py    # 11.11
    ├── travel_story_schema.py        # 11.11
    ├── insurance_schema.py           # 11.11
    └── audit_log_schema.py

Frontend/
├── pages/admin/
│   ├── flight-booking-list/          # Phase A
│   ├── hotel-booking-list/           # Phase B
│   ├── transport-booking-list/       # Phase C
│   ├── session-list/                 # Phase D
│   ├── custom-tour-list/             # Phase D
│   ├── buddy-profile-list/
│   ├── group-trip-list/
│   ├── match-request-list/
│   ├── agent-control/                # 11.10
│   ├── agent-runs/                   # 11.10
│   ├── agent-run-detail/             # 11.10
│   ├── mcp-servers/                  # 11.10
│   ├── intent-stats/                 # 11.10
│   ├── itinerary-list/               # 11.10
│   ├── price-alert-list/             # 11.11
│   ├── packing-template-list/        # 11.11
│   ├── travel-story-moderation/     # 11.11
│   ├── insurance-plan-list/          # 11.11
│   ├── insurance-order-list/         # 11.11
│   └── audit-log/
└── services/admin/
    ├── admin-flight.service.ts
    ├── admin-hotel.service.ts
    ├── admin-transport.service.ts
    ├── admin-tour-session.service.ts
    ├── admin-custom-tour.service.ts
    ├── admin-community.service.ts
    ├── admin-agent.service.ts        # 11.10
    ├── admin-mcp.service.ts          # 11.10
    ├── admin-itinerary.service.ts    # 11.10
    ├── admin-smart.service.ts        # 11.11 (gop 4 feature)
    └── admin-audit-log.service.ts
```

---

### 11.10 Admin cho Multi-Agent System (đối ứng Section 14)

Phần này bổ sung admin UI cho các thành phần ở Section 14: kiểm soát agent runtime, theo dõi sức khoẻ MCP sub-server, phân tích intent, quản lý itinerary AI sinh.

#### 11.10.1 Schema bảng

```sql
-- File: Backend/migrations/add_admin_extension_tables.sql

CREATE TABLE IF NOT EXISTS agent_configs (
    agent_name       VARCHAR(100) PRIMARY KEY,
    enabled          BOOLEAN      NOT NULL DEFAULT true,
    model            VARCHAR(100),
    temperature      NUMERIC(3,2),
    max_tokens       INT,
    system_prompt    TEXT,
    metadata         JSONB        DEFAULT '{}'::jsonb,
    updated_by       UUID         REFERENCES users(user_id),
    updated_at       TIMESTAMPTZ  DEFAULT now()
);

CREATE TABLE IF NOT EXISTS mcp_servers (
    name             VARCHAR(50) PRIMARY KEY,
    display_name     VARCHAR(100) NOT NULL,
    prefix           VARCHAR(50)  NOT NULL,
    is_active        BOOLEAN      NOT NULL DEFAULT true,
    last_ping_ms     INT,
    last_ping_at     TIMESTAMPTZ,
    last_error       TEXT,
    error_count_24h  INT DEFAULT 0,
    updated_at       TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent_runs (
    run_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_room_id      UUID,
    user_id           UUID REFERENCES users(user_id),
    user_query        TEXT,
    intent            VARCHAR(50),
    route_taken       VARCHAR(50),
    tool_calls        JSONB DEFAULT '[]'::jsonb,
    latency_ms        INT,
    token_usage       JSONB,
    status            VARCHAR(20) DEFAULT 'success',
    langsmith_trace_id VARCHAR(100),
    error_message     TEXT,
    created_at        TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS intent_stats_daily (
    stat_date        DATE NOT NULL,
    intent           VARCHAR(50) NOT NULL,
    total_count      INT  DEFAULT 0,
    success_count    INT  DEFAULT 0,
    avg_latency_ms   INT,
    PRIMARY KEY (stat_date, intent)
);

CREATE TABLE IF NOT EXISTS itineraries (
    itinerary_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID REFERENCES users(user_id),
    destination      VARCHAR(255) NOT NULL,
    start_date       DATE NOT NULL,
    end_date         DATE NOT NULL,
    days             JSONB NOT NULL,
    total_estimated_cost_vnd  BIGINT,
    source           VARCHAR(20) DEFAULT 'ai',    -- ai | admin_template | user_saved
    is_template      BOOLEAN DEFAULT false,
    is_public        BOOLEAN DEFAULT false,
    status           VARCHAR(20) DEFAULT 'active',-- active | archived | deleted
    metadata         JSONB DEFAULT '{}'::jsonb,
    created_at       TIMESTAMPTZ DEFAULT now(),
    updated_at       TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS admin_audit_log (
    id            BIGSERIAL PRIMARY KEY,
    admin_id      UUID REFERENCES users(user_id),
    action        VARCHAR(100) NOT NULL,
    target_type   VARCHAR(50)  NOT NULL,
    target_id     VARCHAR(100),
    before_state  JSONB,
    after_state   JSONB,
    ip_address    VARCHAR(45),
    created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_created_at ON agent_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_runs_intent     ON agent_runs(intent);
CREATE INDEX IF NOT EXISTS idx_itineraries_user      ON itineraries(user_id);
CREATE INDEX IF NOT EXISTS idx_itineraries_template  ON itineraries(is_template);
CREATE INDEX IF NOT EXISTS idx_audit_log_admin       ON admin_audit_log(admin_id, created_at DESC);
```

Seed `mcp_servers` ngay khi `register_all_tools()` được gọi lúc startup (upsert 7 sub-server: `booking`, `search`, `weather`, `flight`, `destination`, `itinerary`, `echo`).

#### 11.10.2 Backend endpoints

```python
# Backend/app/v1/api/endpoints/admin_agents.py

from fastapi import APIRouter, Depends, Query

from app.v1.core.dependencies import get_current_admin
from app.v1.schema.agent_config_schema import AgentConfigUpdate
from app.v1.services.admin_agent_service import AdminAgentService

router = APIRouter(prefix="/admin/ai", tags=["Admin - AI System"])
service = AdminAgentService()


@router.get("/agents")
async def list_agents(admin=Depends(get_current_admin)):
    return service.list_agents()


@router.get("/agents/{name}")
async def get_agent(name: str, admin=Depends(get_current_admin)):
    return service.get_agent(name)


@router.put("/agents/{name}")
async def update_agent(
    name: str,
    payload: AgentConfigUpdate,
    admin=Depends(get_current_admin),
):
    return service.update_agent(name, payload, admin_id=admin["user_id"])


@router.post("/agents/{name}/reload")
async def reload_agent(name: str, admin=Depends(get_current_admin)):
    return service.reload_agent(name)


@router.get("/runs")
async def list_runs(
    page: int = 1,
    limit: int = 20,
    intent: str | None = None,
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    admin=Depends(get_current_admin),
):
    return service.list_runs(page, limit, intent, status, date_from, date_to)


@router.get("/runs/{run_id}")
async def get_run(run_id: str, admin=Depends(get_current_admin)):
    return service.get_run(run_id)


@router.get("/intent-stats")
async def intent_stats(
    date_from: str = Query(..., description="YYYY-MM-DD"),
    date_to:   str = Query(..., description="YYYY-MM-DD"),
    admin=Depends(get_current_admin),
):
    return service.intent_stats(date_from, date_to)
```

```python
# Backend/app/v1/api/endpoints/admin_mcp.py

from fastapi import APIRouter, Depends

from app.v1.core.dependencies import get_current_admin
from app.v1.services.mcp_health_service import MCPHealthService

router = APIRouter(prefix="/admin/ai/mcp", tags=["Admin - MCP Servers"])
service = MCPHealthService()


@router.get("/servers")
async def list_servers(admin=Depends(get_current_admin)):
    return await service.list_servers()


@router.post("/servers/{name}/ping")
async def ping_server(name: str, admin=Depends(get_current_admin)):
    return await service.ping(name)


@router.get("/servers/{name}/tools")
async def list_tools(name: str, admin=Depends(get_current_admin)):
    return await service.list_tools(name)
```

```python
# Backend/app/v1/api/endpoints/admin_itineraries.py

from fastapi import APIRouter, Depends

from app.v1.core.dependencies import get_current_admin
from app.v1.schema.itinerary_schema import ItineraryUpdate
from app.v1.services.admin_itinerary_service import AdminItineraryService

router = APIRouter(prefix="/admin/ai/itineraries", tags=["Admin - Itineraries"])
service = AdminItineraryService()


@router.get("")
async def list_itineraries(
    page: int = 1,
    limit: int = 20,
    user_id: str | None = None,
    is_template: bool | None = None,
    destination: str | None = None,
    admin=Depends(get_current_admin),
):
    return service.list(page, limit, user_id, is_template, destination)


@router.get("/{itinerary_id}")
async def get_itinerary(itinerary_id: str, admin=Depends(get_current_admin)):
    return service.get(itinerary_id)


@router.put("/{itinerary_id}")
async def update_itinerary(
    itinerary_id: str,
    payload: ItineraryUpdate,
    admin=Depends(get_current_admin),
):
    return service.update(itinerary_id, payload, admin_id=admin["user_id"])


@router.delete("/{itinerary_id}")
async def delete_itinerary(itinerary_id: str, admin=Depends(get_current_admin)):
    return service.soft_delete(itinerary_id, admin_id=admin["user_id"])


@router.post("/{itinerary_id}/promote-template")
async def promote_template(itinerary_id: str, admin=Depends(get_current_admin)):
    return service.promote_template(itinerary_id, admin_id=admin["user_id"])
```

#### 11.10.3 Service mẫu — `MCPHealthService`

```python
# Backend/app/v1/services/mcp_health_service.py

import asyncio
import time
from datetime import datetime, timezone

from fastmcp import Client

from app.v1.core.supabase import get_supabase
from app.v1.mcp.server import mcp as composite_mcp


class MCPHealthService:
    """Ping each sub-server through the composite FastMCP instance."""

    SUB_SERVERS = (
        "booking", "search", "weather", "flight",
        "destination", "itinerary", "echo",
    )

    def __init__(self) -> None:
        self.supabase = get_supabase()

    async def list_servers(self) -> dict:
        rows = self.supabase.table("mcp_servers").select("*").order("name").execute()
        return {"EC": 0, "data": rows.data}

    async def ping(self, name: str) -> dict:
        if name not in self.SUB_SERVERS:
            return {"EC": 1, "EM": "unknown sub-server"}

        started = time.perf_counter()
        try:
            async with Client(composite_mcp) as client:
                await client.call_tool(f"{name}/ping", {})
            latency_ms = int((time.perf_counter() - started) * 1000)
            self._record(name, latency_ms=latency_ms, error=None)
            return {"EC": 0, "latency_ms": latency_ms}
        except Exception as exc:
            self._record(name, latency_ms=None, error=str(exc))
            return {"EC": 1, "EM": str(exc)}

    async def list_tools(self, name: str) -> dict:
        async with Client(composite_mcp) as client:
            tools = await client.list_tools()
        scoped = [t for t in tools if t.name.startswith(f"{name}/")]
        return {"EC": 0, "data": scoped}

    def _record(self, name: str, latency_ms: int | None, error: str | None) -> None:
        self.supabase.table("mcp_servers").update(
            {
                "last_ping_ms": latency_ms,
                "last_ping_at": datetime.now(timezone.utc).isoformat(),
                "last_error":   error,
                "is_active":    error is None,
                "updated_at":   datetime.now(timezone.utc).isoformat(),
            }
        ).eq("name", name).execute()
```

Cron 60 giây có thể thêm vào `scheduled_tasks.py`:

```python
from app.v1.services.mcp_health_service import MCPHealthService

async def mcp_ping_job() -> None:
    service = MCPHealthService()
    for name in service.SUB_SERVERS:
        await service.ping(name)

scheduler.add_job(mcp_ping_job, "interval", seconds=60, id="mcp_ping")
```

#### 11.10.4 LangGraph callback ghi `agent_runs`

```python
# Backend/app/v1/services/agent_run_logger.py

import time
from typing import Any
from uuid import uuid4

from langchain_core.callbacks.base import AsyncCallbackHandler

from app.v1.core.supabase import get_supabase


class AgentRunLogger(AsyncCallbackHandler):
    """Persist one row per Supervisor invocation into agent_runs."""

    def __init__(self, chat_room_id: str, user_id: str, user_query: str) -> None:
        self.run_id = str(uuid4())
        self.chat_room_id = chat_room_id
        self.user_id = user_id
        self.user_query = user_query
        self.started_at = time.perf_counter()
        self.tool_calls: list[dict] = []
        self.intent: str | None = None
        self.route_taken: str | None = None
        self.error_message: str | None = None
        self.supabase = get_supabase()

    def set_intent(self, intent: str, route_taken: str) -> None:
        self.intent = intent
        self.route_taken = route_taken

    async def on_tool_start(self, serialized: dict[str, Any], input_str: str, **kw: Any) -> None:
        self.tool_calls.append({"name": serialized.get("name"), "input": input_str})

    async def on_chain_error(self, error: BaseException, **kw: Any) -> None:
        self.error_message = str(error)

    async def flush(self, langsmith_trace_id: str | None = None) -> None:
        latency_ms = int((time.perf_counter() - self.started_at) * 1000)
        self.supabase.table("agent_runs").insert(
            {
                "run_id": self.run_id,
                "chat_room_id": self.chat_room_id,
                "user_id": self.user_id,
                "user_query": self.user_query,
                "intent": self.intent,
                "route_taken": self.route_taken,
                "tool_calls": self.tool_calls,
                "latency_ms": latency_ms,
                "status": "error" if self.error_message else "success",
                "langsmith_trace_id": langsmith_trace_id,
                "error_message": self.error_message,
            }
        ).execute()
```

Sử dụng:

```python
logger = AgentRunLogger(chat_room_id, user_id, user_query)
result = await supervisor.ainvoke(state, config={"callbacks": [logger]})
await logger.flush()
```

#### 11.10.5 Frontend admin pages

`agent-control.component.ts` (chỉ list + edit prompt, sử dụng PrimeNG):

```typescript
// Frontend/src/app/pages/admin/agent-control/agent-control.component.ts

import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TableModule } from 'primeng/table';
import { InputTextareaModule } from 'primeng/inputtextarea';
import { InputNumberModule } from 'primeng/inputnumber';
import { ToggleButtonModule } from 'primeng/togglebutton';
import { ButtonModule } from 'primeng/button';
import { AdminAgentService, AgentConfig } from '../../../services/admin/admin-agent.service';

@Component({
  selector: 'app-agent-control',
  standalone: true,
  imports: [CommonModule, FormsModule, TableModule, InputTextareaModule,
            InputNumberModule, ToggleButtonModule, ButtonModule],
  templateUrl: './agent-control.component.html',
})
export class AgentControlComponent implements OnInit {
  private api = inject(AdminAgentService);

  agents: AgentConfig[] = [];
  editing: AgentConfig | null = null;

  ngOnInit(): void {
    this.api.listAgents().subscribe(res => (this.agents = res.data));
  }

  startEdit(agent: AgentConfig): void {
    this.editing = { ...agent };
  }

  save(): void {
    if (!this.editing) { return; }
    this.api.updateAgent(this.editing.agent_name, this.editing)
      .subscribe(() => {
        this.api.reload(this.editing!.agent_name).subscribe();
        this.editing = null;
        this.ngOnInit();
      });
  }
}
```

`admin-agent.service.ts`:

```typescript
// Frontend/src/app/services/admin/admin-agent.service.ts

import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from '../config.service';

export interface AgentConfig {
  agent_name: string;
  enabled: boolean;
  model: string;
  temperature: number;
  max_tokens: number;
  system_prompt: string;
  updated_at: string;
}

@Injectable({ providedIn: 'root' })
export class AdminAgentService {
  private http = inject(HttpClient);
  private cfg  = inject(ConfigService);

  private get base(): string { return `${this.cfg.apiUrl}/admin/ai`; }

  listAgents(): Observable<{ data: AgentConfig[] }> {
    return this.http.get<{ data: AgentConfig[] }>(`${this.base}/agents`);
  }

  updateAgent(name: string, payload: Partial<AgentConfig>): Observable<unknown> {
    return this.http.put(`${this.base}/agents/${name}`, payload);
  }

  reload(name: string): Observable<unknown> {
    return this.http.post(`${this.base}/agents/${name}/reload`, {});
  }

  listRuns(params: Record<string, unknown>): Observable<unknown> {
    return this.http.get(`${this.base}/runs`, { params: params as never });
  }

  getRun(runId: string): Observable<unknown> {
    return this.http.get(`${this.base}/runs/${runId}`);
  }

  intentStats(dateFrom: string, dateTo: string): Observable<unknown> {
    return this.http.get(`${this.base}/intent-stats`, {
      params: { date_from: dateFrom, date_to: dateTo },
    });
  }
}
```

Các page còn lại (`agent-runs`, `agent-run-detail`, `mcp-servers`, `intent-stats`, `itinerary-list`) đi theo cùng pattern PrimeNG TableModule + service riêng. Trang `intent-stats` thêm Chart.js (cần `npm i chart.js`).

---

### 11.11 Admin cho Phase E priority

Chỉ cover 4 feature có giá trị production cao: Price Predictor (7.2), Packing List (7.5), Travel Story (7.6), Insurance (7.9). Các feature còn lại (Concierge / Voice / Sustainable / AR / Story…) để revision sau.

#### 11.11.1 Schema bảng

```sql
-- File: Backend/migrations/add_phase_e_priority_tables.sql

-- 7.2 Price Predictor
CREATE TABLE IF NOT EXISTS price_history (
    id              BIGSERIAL PRIMARY KEY,
    asset_type      VARCHAR(20) NOT NULL,        -- flight | hotel | tour
    asset_ref       VARCHAR(100) NOT NULL,       -- route IATA / hotel_id / tour_id
    snapshot_date   DATE NOT NULL,
    price_vnd       BIGINT NOT NULL,
    source          VARCHAR(50),
    metadata        JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_price_history_lookup
    ON price_history(asset_type, asset_ref, snapshot_date DESC);

-- price_alerts: dung lai bang da khai bao o Section 8 (Phase A migration).
-- Bo sung 2 cot phuc vu predictor:
ALTER TABLE price_alerts
    ADD COLUMN IF NOT EXISTS last_predicted_price BIGINT,
    ADD COLUMN IF NOT EXISTS model_version VARCHAR(50);

-- 7.5 Packing List
CREATE TABLE IF NOT EXISTS packing_list_templates (
    template_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    destination    VARCHAR(255) NOT NULL,
    season         VARCHAR(20),                  -- spring | summer | autumn | winter | all
    duration_days  INT,
    items          JSONB NOT NULL,               -- [{category, name, qty, required}]
    is_active      BOOLEAN DEFAULT true,
    updated_by     UUID REFERENCES users(user_id),
    created_at     TIMESTAMPTZ DEFAULT now(),
    updated_at     TIMESTAMPTZ DEFAULT now()
);

-- 7.6 Travel Story
CREATE TABLE IF NOT EXISTS travel_stories (
    story_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID NOT NULL REFERENCES users(user_id),
    trip_ref       VARCHAR(100),                 -- booking_id / itinerary_id
    title          VARCHAR(255) NOT NULL,
    content        TEXT NOT NULL,
    images         TEXT[] DEFAULT '{}',
    status         VARCHAR(20) DEFAULT 'pending',-- pending | approved | rejected
    moderator_id   UUID REFERENCES users(user_id),
    moderation_note TEXT,
    created_at     TIMESTAMPTZ DEFAULT now(),
    updated_at     TIMESTAMPTZ DEFAULT now()
);

-- 7.9 Insurance
CREATE TABLE IF NOT EXISTS insurance_plans (
    plan_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider       VARCHAR(100) NOT NULL,
    name           VARCHAR(255) NOT NULL,
    coverage       JSONB NOT NULL,               -- {medical, baggage, cancellation, ...}
    price_vnd      BIGINT NOT NULL,
    currency       VARCHAR(3) DEFAULT 'VND',
    is_active      BOOLEAN DEFAULT true,
    created_at     TIMESTAMPTZ DEFAULT now(),
    updated_at     TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS insurance_orders (
    order_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID NOT NULL REFERENCES users(user_id),
    plan_id        UUID NOT NULL REFERENCES insurance_plans(plan_id),
    booking_ref    VARCHAR(100),
    price_vnd      BIGINT NOT NULL,
    status         VARCHAR(20) DEFAULT 'pending',-- pending | active | expired | cancelled
    payment_id     UUID,
    valid_from     DATE,
    valid_to       DATE,
    created_at     TIMESTAMPTZ DEFAULT now()
);
```

#### 11.11.2 Endpoint admin

```python
# Backend/app/v1/api/endpoints/admin_smart_features.py

from fastapi import APIRouter, Depends, Query

from app.v1.core.dependencies import get_current_admin
from app.v1.services.admin_price_alert_service import AdminPriceAlertService
from app.v1.services.admin_packing_template_service import AdminPackingTemplateService
from app.v1.services.admin_travel_story_service import AdminTravelStoryService
from app.v1.services.admin_insurance_service import AdminInsuranceService

router = APIRouter(prefix="/admin/smart", tags=["Admin - Smart Features"])

price_service     = AdminPriceAlertService()
packing_service   = AdminPackingTemplateService()
story_service     = AdminTravelStoryService()
insurance_service = AdminInsuranceService()


# 7.2 Price Predictor
@router.get("/price-alerts")
async def list_price_alerts(
    page: int = 1, limit: int = 20,
    user_id: str | None = None, is_active: bool | None = None,
    admin=Depends(get_current_admin),
):
    return price_service.list_alerts(page, limit, user_id, is_active)


@router.get("/price-alerts/{alert_id}/history")
async def alert_history(alert_id: str, admin=Depends(get_current_admin)):
    return price_service.history(alert_id)


@router.delete("/price-alerts/{alert_id}")
async def delete_alert(alert_id: str, admin=Depends(get_current_admin)):
    return price_service.delete(alert_id, admin_id=admin["user_id"])


# 7.5 Packing
@router.get("/packing-templates")
async def list_templates(
    destination: str | None = None, season: str | None = None,
    admin=Depends(get_current_admin),
):
    return packing_service.list(destination, season)


@router.post("/packing-templates")
async def create_template(payload: dict, admin=Depends(get_current_admin)):
    return packing_service.create(payload, admin_id=admin["user_id"])


@router.put("/packing-templates/{template_id}")
async def update_template(template_id: str, payload: dict, admin=Depends(get_current_admin)):
    return packing_service.update(template_id, payload, admin_id=admin["user_id"])


@router.delete("/packing-templates/{template_id}")
async def delete_template(template_id: str, admin=Depends(get_current_admin)):
    return packing_service.delete(template_id, admin_id=admin["user_id"])


# 7.6 Travel Story moderation
@router.get("/travel-stories")
async def list_stories(
    page: int = 1, limit: int = 20,
    status: str | None = Query(None, pattern="^(pending|approved|rejected)$"),
    admin=Depends(get_current_admin),
):
    return story_service.list(page, limit, status)


@router.get("/travel-stories/{story_id}")
async def get_story(story_id: str, admin=Depends(get_current_admin)):
    return story_service.get(story_id)


@router.put("/travel-stories/{story_id}/moderate")
async def moderate_story(
    story_id: str, payload: dict, admin=Depends(get_current_admin),
):
    # payload: { status: 'approved'|'rejected', note?: str }
    return story_service.moderate(story_id, payload, moderator_id=admin["user_id"])


# 7.9 Insurance
@router.get("/insurance-plans")
async def list_plans(is_active: bool | None = None, admin=Depends(get_current_admin)):
    return insurance_service.list_plans(is_active)


@router.post("/insurance-plans")
async def create_plan(payload: dict, admin=Depends(get_current_admin)):
    return insurance_service.create_plan(payload, admin_id=admin["user_id"])


@router.put("/insurance-plans/{plan_id}")
async def update_plan(plan_id: str, payload: dict, admin=Depends(get_current_admin)):
    return insurance_service.update_plan(plan_id, payload, admin_id=admin["user_id"])


@router.delete("/insurance-plans/{plan_id}")
async def delete_plan(plan_id: str, admin=Depends(get_current_admin)):
    return insurance_service.delete_plan(plan_id, admin_id=admin["user_id"])


@router.get("/insurance-orders")
async def list_orders(
    page: int = 1, limit: int = 20,
    user_id: str | None = None, status: str | None = None,
    admin=Depends(get_current_admin),
):
    return insurance_service.list_orders(page, limit, user_id, status)
```

#### 11.11.3 Service mẫu — Travel Story moderation

```python
# Backend/app/v1/services/admin_travel_story_service.py

from datetime import datetime, timezone

from app.v1.core.supabase import get_supabase
from app.v1.services.admin_audit_log_service import AdminAuditLogService


class AdminTravelStoryService:

    def __init__(self) -> None:
        self.supabase = get_supabase()
        self.audit = AdminAuditLogService()

    def list(self, page: int, limit: int, status: str | None) -> dict:
        offset = (page - 1) * limit
        query = self.supabase.table("travel_stories").select("*", count="exact")
        if status:
            query = query.eq("status", status)
        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        return {"EC": 0, "data": result.data, "total": result.count}

    def get(self, story_id: str) -> dict:
        result = self.supabase.table("travel_stories").select("*").eq("story_id", story_id).execute()
        if not result.data:
            return {"EC": 1, "EM": "story not found"}
        return {"EC": 0, "data": result.data[0]}

    def moderate(self, story_id: str, payload: dict, moderator_id: str) -> dict:
        new_status = payload.get("status")
        if new_status not in ("approved", "rejected"):
            return {"EC": 1, "EM": "invalid status"}

        before = self.get(story_id)
        if before.get("EC") != 0:
            return before

        update = {
            "status": new_status,
            "moderator_id": moderator_id,
            "moderation_note": payload.get("note"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        result = self.supabase.table("travel_stories").update(update).eq("story_id", story_id).execute()
        self.audit.log(
            admin_id=moderator_id,
            action=f"travel_story.{new_status}",
            target_type="travel_story",
            target_id=story_id,
            before=before["data"],
            after=result.data[0] if result.data else None,
        )
        return {"EC": 0, "EM": f"story {new_status}", "data": result.data[0]}
```

#### 11.11.4 Audit log dùng chung

```python
# Backend/app/v1/services/admin_audit_log_service.py

from app.v1.core.supabase import get_supabase


class AdminAuditLogService:

    def __init__(self) -> None:
        self.supabase = get_supabase()

    def log(
        self,
        admin_id: str,
        action: str,
        target_type: str,
        target_id: str | None = None,
        before: dict | None = None,
        after: dict | None = None,
        ip_address: str | None = None,
    ) -> None:
        self.supabase.table("admin_audit_log").insert(
            {
                "admin_id": admin_id,
                "action": action,
                "target_type": target_type,
                "target_id": target_id,
                "before_state": before,
                "after_state": after,
                "ip_address": ip_address,
            }
        ).execute()

    def list(
        self,
        page: int = 1, limit: int = 50,
        admin_id: str | None = None,
        target_type: str | None = None,
        action: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict:
        offset = (page - 1) * limit
        query = self.supabase.table("admin_audit_log").select("*", count="exact")
        if admin_id:
            query = query.eq("admin_id", admin_id)
        if target_type:
            query = query.eq("target_type", target_type)
        if action:
            query = query.ilike("action", f"%{action}%")
        if date_from:
            query = query.gte("created_at", date_from)
        if date_to:
            query = query.lte("created_at", date_to)
        result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        return {"EC": 0, "data": result.data, "total": result.count}
```

Endpoint `/admin/audit-log` chỉ là wrapper gọi `AdminAuditLogService.list()`.

#### 11.11.5 Frontend admin — gộp 1 service

```typescript
// Frontend/src/app/services/admin/admin-smart.service.ts

import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from '../config.service';

@Injectable({ providedIn: 'root' })
export class AdminSmartService {
  private http = inject(HttpClient);
  private cfg  = inject(ConfigService);

  private get base(): string { return `${this.cfg.apiUrl}/admin/smart`; }

  // Price
  listPriceAlerts(params: Record<string, unknown>): Observable<unknown> {
    return this.http.get(`${this.base}/price-alerts`, { params: params as never });
  }
  priceHistory(alertId: string): Observable<unknown> {
    return this.http.get(`${this.base}/price-alerts/${alertId}/history`);
  }
  deletePriceAlert(alertId: string): Observable<unknown> {
    return this.http.delete(`${this.base}/price-alerts/${alertId}`);
  }

  // Packing
  listPackingTemplates(destination?: string, season?: string): Observable<unknown> {
    return this.http.get(`${this.base}/packing-templates`, {
      params: { destination, season } as never,
    });
  }
  createPackingTemplate(payload: unknown): Observable<unknown> {
    return this.http.post(`${this.base}/packing-templates`, payload);
  }
  updatePackingTemplate(id: string, payload: unknown): Observable<unknown> {
    return this.http.put(`${this.base}/packing-templates/${id}`, payload);
  }
  deletePackingTemplate(id: string): Observable<unknown> {
    return this.http.delete(`${this.base}/packing-templates/${id}`);
  }

  // Travel Story moderation
  listStories(page: number, limit: number, status?: string): Observable<unknown> {
    return this.http.get(`${this.base}/travel-stories`, {
      params: { page, limit, status } as never,
    });
  }
  moderateStory(id: string, payload: { status: 'approved'|'rejected'; note?: string }): Observable<unknown> {
    return this.http.put(`${this.base}/travel-stories/${id}/moderate`, payload);
  }

  // Insurance
  listPlans(isActive?: boolean): Observable<unknown> {
    return this.http.get(`${this.base}/insurance-plans`, { params: { is_active: isActive } as never });
  }
  createPlan(payload: unknown): Observable<unknown> {
    return this.http.post(`${this.base}/insurance-plans`, payload);
  }
  updatePlan(id: string, payload: unknown): Observable<unknown> {
    return this.http.put(`${this.base}/insurance-plans/${id}`, payload);
  }
  deletePlan(id: string): Observable<unknown> {
    return this.http.delete(`${this.base}/insurance-plans/${id}`);
  }
  listOrders(params: Record<string, unknown>): Observable<unknown> {
    return this.http.get(`${this.base}/insurance-orders`, { params: params as never });
  }
}
```

---

### 11.12 Tổng hợp endpoint admin mở rộng

| Section | Prefix | Số endpoint |
|---|---|---|
| Bookings (Phase A-D) — 11.1 → 11.5 | `/admin/{flights,hotels,transport,tour-sessions,custom-tours}` | đã có ở 11.1–11.5 |
| Community — 11.6 | `/admin/community/*` | đã có |
| Internal Catalog — 12.5 | `/admin/{flight,hotel,transport}-catalog/*` | đã có |
| **Multi-Agent System — 11.10** | `/admin/ai/{agents,runs,mcp,intent-stats,itineraries}` | 16 |
| **Phase E priority — 11.11** | `/admin/smart/{price-alerts,packing-templates,travel-stories,insurance-*}` | 13 |
| **Audit log** | `/admin/audit-log` | 1 |

Tổng cộng thêm khoảng 30 endpoint vào router admin.

---

## 12. Internal Catalog System

> Thay vì phụ thuộc external API (Amadeus, Booking.com, 12Go), hệ thống
> tự quản lý toàn bộ catalog data. Admin tự thêm/sửa/xóa chuyến bay,
> khách sạn, xe/tàu qua admin panel. AI Agent tìm kiếm từ internal DB.

### 12.1 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      ADMIN PANEL                         │
│  Thêm/Sửa/Xóa catalog data trực tiếp                    │
│  ├── Flights (chuyến bay, giá, ghế)                     │
│  ├── Hotels (phòng, giá, tiện ích)                      │
│  ├── Transport (xe, tàu, tuyến đường)                   │
│  └── Tour Sessions (hoạt động theo buổi)                │
└──────────────────────────┬──────────────────────────────┘
                           │ CRUD
┌──────────────────────────┴──────────────────────────────┐
│                 INTERNAL DATABASE                        │
│  ├── flights              (chuyến bay catalog)           │
│  ├── flight_prices        (giá theo ngày)               │
│  ├── airlines             (hãng bay)                    │
│  ├── airports             (sân bay)                     │
│  ├── hotels               (khách sạn catalog)           │
│  ├── hotel_rooms          (phòng & giá)                 │
│  ├── transport_routes     (tuyến xe/tàu)                │
│  ├── transport_schedules  (lịch chạy)                   │
│  └── tour_sessions        (hoạt động theo buổi)         │
└──────────────────────────┬──────────────────────────────┘
                           │ Search (SQL + pgvector)
┌──────────────────────────┴──────────────────────────────┐
│                    AI AGENT                               │
│  search_internal_flights()  → query flights + prices    │
│  search_internal_hotels()   → query hotels + rooms      │
│  search_internal_transport()→ query routes + schedules  │
│  search_tour_sessions()     → query sessions + pgvector │
└─────────────────────────────────────────────────────────┘
```

### 12.2 Database Schema — Internal Catalog

```sql
-- ============================================
-- AIRLINES
-- ============================================

CREATE TABLE airlines (
    airline_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(10) NOT NULL UNIQUE,     -- "VN", "VJ", "QH"
    name VARCHAR(255) NOT NULL,           -- "Vietnam Airlines"
    logo_url TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- AIRPORTS
-- ============================================

CREATE TABLE airports (
    airport_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    iata_code VARCHAR(10) NOT NULL UNIQUE, -- "HAN", "SGN", "DAD", "DLI"
    name VARCHAR(255) NOT NULL,            -- "Sân bay Nội Bài"
    city VARCHAR(255) NOT NULL,            -- "Hà Nội"
    country VARCHAR(100) DEFAULT 'Vietnam',
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),
    is_active BOOLEAN DEFAULT true
);

-- Seed data airports
INSERT INTO airports (iata_code, name, city) VALUES
    ('HAN', 'Sân bay quốc tế Nội Bài', 'Hà Nội'),
    ('SGN', 'Sân bay quốc tế Tân Sơn Nhất', 'TP. Hồ Chí Minh'),
    ('DAD', 'Sân bay quốc tế Đà Nẵng', 'Đà Nẵng'),
    ('DLI', 'Sân bay Liên Khương', 'Đà Lạt'),
    ('CXR', 'Sân bay Cam Ranh', 'Nha Trang'),
    ('PQC', 'Sân bay Phú Quốc', 'Phú Quốc'),
    ('HPH', 'Sân bay Cát Bi', 'Hải Phòng'),
    ('VII', 'Sân bay Vinh', 'Nghệ An'),
    ('HUI', 'Sân bay Phú Bài', 'Huế'),
    ('TBB', 'Sân bay Phù Cát', 'Quy Nhơn'),
    ('VCA', 'Sân bay Cần Thơ', 'Cần Thơ'),
    ('BMV', 'Sân bay Buôn Ma Thuột', 'Đắk Lắk'),
    ('UIH', 'Sân bay Phù Cát', 'Bình Định'),
    ('VDO', 'Sân bay Vân Đồn', 'Quảng Ninh');

-- Seed data airlines
INSERT INTO airlines (code, name) VALUES
    ('VN', 'Vietnam Airlines'),
    ('VJ', 'VietJet Air'),
    ('QH', 'Bamboo Airways'),
    ('BL', 'Jetstar Pacific Airlines'),
    ('VU', 'Vietravel Airlines');

-- ============================================
-- FLIGHTS (Catalog — admin quản lý)
-- ============================================

CREATE TABLE flights (
    flight_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flight_code VARCHAR(20) NOT NULL,      -- "VN247"
    airline_id UUID NOT NULL REFERENCES airlines(airline_id),
    origin_id UUID NOT NULL REFERENCES airports(airport_id),
    destination_id UUID NOT NULL REFERENCES airports(airport_id),
    departure_time TIME NOT NULL,          -- "06:30"
    arrival_time TIME NOT NULL,            -- "08:45"
    duration_minutes INT NOT NULL,
    aircraft_type VARCHAR(50),             -- "Airbus A321", "Boeing 787"
    travel_classes JSONB NOT NULL,         -- xem bên dưới
    frequency TEXT[],                      -- ["mon", "tue", "wed", ...] hoặc ["daily"]
    effective_from DATE NOT NULL,
    effective_to DATE,
    is_active BOOLEAN DEFAULT true,
    embedding VECTOR(3072),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    CONSTRAINT unique_flight UNIQUE (flight_code, airline_id, origin_id, destination_id)
);

/*
travel_classes structure:
{
    "economy": {
        "base_price": 1500000,
        "baggage_included": 20,     // kg
        "meal_included": true,
        "seat_selection": true,
        "refundable": false,
        "change_fee": 300000
    },
    "premium_economy": {
        "base_price": 2800000,
        "baggage_included": 30,
        "meal_included": true,
        "seat_selection": true,
        "refundable": true,
        "change_fee": 0
    },
    "business": {
        "base_price": 5500000,
        "baggage_included": 40,
        "meal_included": true,
        "seat_selection": true,
        "refundable": true,
        "change_fee": 0,
        "lounge_access": true
    }
}
*/

-- ============================================
-- FLIGHT PRICES (giá theo ngày — linh hoạt)
-- ============================================

CREATE TABLE flight_prices (
    price_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flight_id UUID NOT NULL REFERENCES flights(flight_id) ON DELETE CASCADE,
    travel_date DATE NOT NULL,
    travel_class VARCHAR(30) NOT NULL,     -- "economy", "premium_economy", "business"
    price DECIMAL(12,2) NOT NULL,          -- override giá base
    available_seats INT NOT NULL DEFAULT 180,
    total_seats INT NOT NULL DEFAULT 180,
    is_promo BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(flight_id, travel_date, travel_class)
);

-- ============================================
-- HOTELS (Catalog — admin quản lý)
-- ============================================

CREATE TABLE hotels (
    hotel_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    city VARCHAR(255) NOT NULL,
    district VARCHAR(255),                 -- "Quận 1", "Ba Đình"
    address TEXT NOT NULL,
    star_rating INT CHECK (star_rating BETWEEN 1 AND 5),
    description TEXT,
    phone VARCHAR(20),
    email VARCHAR(255),
    website VARCHAR(500),
    checkin_time TIME DEFAULT '14:00',
    checkout_time TIME DEFAULT '12:00',
    amenities TEXT[],                      -- ["wifi", "pool", "spa", "gym", "parking"]
    image_urls TEXT[],
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),
    rating DECIMAL(2,1) DEFAULT 0,
    review_count INT DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    embedding VECTOR(3072),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================
-- HOTEL ROOMS (phòng & giá)
-- ============================================

CREATE TABLE hotel_rooms (
    room_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hotel_id UUID NOT NULL REFERENCES hotels(hotel_id) ON DELETE CASCADE,
    room_type VARCHAR(100) NOT NULL,       -- "Standard", "Deluxe", "Suite", "Family"
    name VARCHAR(255) NOT NULL,            -- "Phòng Deluxe View Biển"
    description TEXT,
    max_occupancy INT NOT NULL DEFAULT 2,
    bed_type VARCHAR(50),                  -- "King", "Twin", "Queen", "Double"
    room_size_sqm DECIMAL(6,2),
    base_price DECIMAL(12,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'VND',
    amenities TEXT[],                      -- ["minibar", "bathtub", "balcony", "city_view"]
    image_urls TEXT[],
    total_rooms INT NOT NULL DEFAULT 10,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Giá phòng theo ngày (override base_price)
CREATE TABLE hotel_room_prices (
    price_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id UUID NOT NULL REFERENCES hotel_rooms(room_id) ON DELETE CASCADE,
    date DATE NOT NULL,
    price DECIMAL(12,2) NOT NULL,
    available_rooms INT NOT NULL,
    is_promo BOOLEAN DEFAULT false,
    UNIQUE(room_id, date)
);

-- ============================================
-- TRANSPORT CATALOG
-- ============================================

CREATE TABLE transport_providers (
    provider_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,            -- "Phương Trang", "FUTA", "Vietnam Railways"
    type VARCHAR(30) NOT NULL,             -- "bus", "train", "limousine", "van", "ferry"
    logo_url TEXT,
    phone VARCHAR(20),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE transport_routes (
    route_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id UUID NOT NULL REFERENCES transport_providers(provider_id),
    origin_city VARCHAR(255) NOT NULL,     -- "TP. Hồ Chí Minh"
    destination_city VARCHAR(255) NOT NULL, -- "Đà Lạt"
    duration_minutes INT NOT NULL,
    distance_km DECIMAL(8,2),
    transport_type VARCHAR(30) NOT NULL,   -- "bus", "train", "limousine", "van", "ferry"
    amenities TEXT[],                      -- ["wifi", "ac", "usb_charging", "blanket"]
    is_active BOOLEAN DEFAULT true,
    embedding VECTOR(3072),
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE transport_schedules (
    schedule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    route_id UUID NOT NULL REFERENCES transport_routes(route_id) ON DELETE CASCADE,
    departure_time TIME NOT NULL,
    arrival_time TIME NOT NULL,
    seat_types JSONB NOT NULL,
    /*
    seat_types structure (giá theo loại ghế):
    [
        {
            "type": "standard",
            "total_seats": 40,
            "base_price": 250000,
            "features": ["reclining_seat", "ac"]
        },
        {
            "type": "vip",
            "total_seats": 20,
            "base_price": 400000,
            "features": ["wide_seat", "ac", "snack", "usb"]
        }
    ]
    */
    frequency TEXT[],                      -- ["mon", "wed", "fri"] hoặc ["daily"]
    effective_from DATE NOT NULL,
    effective_to DATE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Giá transport theo ngày
CREATE TABLE transport_prices (
    price_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id UUID NOT NULL REFERENCES transport_schedules(schedule_id) ON DELETE CASCADE,
    travel_date DATE NOT NULL,
    seat_type VARCHAR(50) NOT NULL,
    price DECIMAL(12,2) NOT NULL,
    available_seats INT NOT NULL,
    UNIQUE(schedule_id, travel_date, seat_type)
);

-- ============================================
-- INDEXES cho internal catalog
-- ============================================

CREATE INDEX idx_flights_route ON flights(origin_id, destination_id);
CREATE INDEX idx_flights_airline ON flights(airline_id);
CREATE INDEX idx_flight_prices_date ON flight_prices(travel_date);
CREATE INDEX idx_flight_prices_flight_date ON flight_prices(flight_id, travel_date);
CREATE INDEX idx_hotels_city ON hotels(city);
CREATE INDEX idx_hotels_star ON hotels(star_rating);
CREATE INDEX idx_hotels_embedding ON hotels USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_hotel_rooms_hotel ON hotel_rooms(hotel_id);
CREATE INDEX idx_hotel_room_prices_date ON hotel_room_prices(date);
CREATE INDEX idx_transport_routes_cities ON transport_routes(origin_city, destination_city);
CREATE INDEX idx_transport_schedules_route ON transport_schedules(route_id);
CREATE INDEX idx_transport_prices_date ON transport_prices(travel_date);
```

### 12.3 Internal Search Services

```python
# Backend/app/v1/services/internal_flight_service.py

class InternalFlightService:
    """Tìm kiếm chuyến bay từ internal database."""

    async def search_flights(
        self,
        origin_code: str,       # IATA: "HAN"
        destination_code: str,  # IATA: "DLI"
        departure_date: str,    # "2026-06-15"
        travel_class: str | None = None,
        adults: int = 1,
        max_price: float | None = None,
        sort_by: str = "price",  # "price", "departure", "duration"
    ) -> list[dict]:
        """
        Tìm chuyến bay từ internal flights + flight_prices tables.
        Join flights với prices để lấy giá cụ thể cho ngày.
        """
        # Get airport IDs
        origin = self.supabase.table("airports").select("airport_id").eq(
            "iata_code", origin_code
        ).execute()
        dest = self.supabase.table("airports").select("airport_id").eq(
            "iata_code", destination_code
        ).execute()

        if not origin.data or not dest.data:
            return []

        # Get active flights on this route
        day_name = self._get_day_name(departure_date)  # "mon", "tue", ...
        flights = self.supabase.table("flights").select(
            "*, airlines(code, name, logo_url), "
            "origin:airports!flights_origin_id_fkey(iata_code, name, city), "
            "destination:airports!flights_destination_id_fkey(iata_code, name, city)"
        ).eq("origin_id", origin.data[0]["airport_id"]).eq(
            "destination_id", dest.data[0]["airport_id"]
        ).eq("is_active", True).contains(
            "frequency", [day_name, "daily"]
        ).execute()

        # Get prices for this date
        flight_ids = [f["flight_id"] for f in flights.data]
        prices = self.supabase.table("flight_prices").select("*").in_(
            "flight_id", flight_ids
        ).eq("travel_date", departure_date).execute()

        price_map = {}
        for p in prices.data:
            key = p["flight_id"]
            price_map.setdefault(key, {})[p["travel_class"]] = p

        # Build results
        results = []
        for flight in flights.data:
            flight_prices = price_map.get(flight["flight_id"], {})

            # Use override price if exists, else base price
            for cls_name, cls_info in flight.get("travel_classes", {}).items():
                if travel_class and cls_name != travel_class:
                    continue

                price_entry = flight_prices.get(cls_name)
                price = float(price_entry["price"]) if price_entry else float(cls_info["base_price"])
                available = price_entry["available_seats"] if price_entry else cls_info.get("total_seats", 180)

                if max_price and price > max_price:
                    continue
                if available < adults:
                    continue

                results.append({
                    "flight_id": flight["flight_id"],
                    "flight_code": flight["flight_code"],
                    "airline": {
                        "code": flight["airlines"]["code"],
                        "name": flight["airlines"]["name"],
                        "logo": flight["airlines"]["logo_url"],
                    },
                    "origin": flight["origin"],
                    "destination": flight["destination"],
                    "departure_time": flight["departure_time"],
                    "arrival_time": flight["arrival_time"],
                    "duration_minutes": flight["duration_minutes"],
                    "aircraft": flight["aircraft_type"],
                    "travel_class": cls_name,
                    "price": price,
                    "original_price": float(cls_info["base_price"]),
                    "available_seats": available,
                    "is_promo": price_entry.get("is_promo", False) if price_entry else False,
                    "baggage_included": cls_info.get("baggage_included"),
                    "meal_included": cls_info.get("meal_included"),
                    "refundable": cls_info.get("refundable", False),
                    "source": "internal",
                })

        # Sort
        sort_key = {
            "price": lambda x: x["price"],
            "departure": lambda x: x["departure_time"],
            "duration": lambda x: x["duration_minutes"],
        }.get(sort_by, lambda x: x["price"])
        results.sort(key=sort_key)

        return results

    async def get_airports(self) -> list[dict]:
        """Lấy danh sách sân bay cho autocomplete."""
        result = self.supabase.table("airports").select("*").eq(
            "is_active", True
        ).order("city").execute()
        return result.data

    async def get_airlines(self) -> list[dict]:
        """Lấy danh sách hãng bay."""
        result = self.supabase.table("airlines").select("*").eq(
            "is_active", True
        ).order("name").execute()
        return result.data

    async def get_popular_routes(self) -> list[dict]:
        """Lấy tuyến bay phổ biến (cho homepage gợi ý)."""
        result = self.supabase.table("flights").select(
            "origin:airports!flights_origin_id_fkey(iata_code, city), "
            "destination:airports!flights_destination_id_fkey(iata_code, city)"
        ).eq("is_active", True).execute()

        routes = {}
        for f in result.data:
            key = f"{f['origin']['iata_code']}-{f['destination']['iata_code']}"
            routes[key] = {
                "origin": f["origin"],
                "destination": f["destination"],
            }
        return list(routes.values())[:10]

    def _get_day_name(self, date_str: str) -> str:
        from datetime import datetime
        days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return days[dt.weekday()]
```

```python
# Backend/app/v1/services/internal_hotel_service.py

class InternalHotelService:
    """Tìm kiếm khách sạn từ internal database."""

    async def search_hotels(
        self,
        city: str,
        checkin_date: str,
        checkout_date: str,
        adults: int = 2,
        rooms: int = 1,
        star_ratings: list[int] | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        amenities: list[str] | None = None,
    ) -> list[dict]:
        """
        Tìm khách sạn + phòng trống + giá cho ngày check-in.
        """
        query = self.supabase.table("hotels").select(
            "*, hotel_rooms(*)"
        ).eq("city", city).eq("is_active", True)

        if star_ratings:
            query = query.in_("star_rating", star_ratings)

        hotels = query.execute()

        num_nights = self._calc_nights(checkin_date, checkout_date)

        results = []
        for hotel in hotels.data:
            # Filter amenities
            if amenities and not all(a in (hotel.get("amenities") or []) for a in amenities):
                continue

            available_rooms = []
            for room in hotel.get("hotel_rooms", []):
                if not room["is_active"]:
                    continue
                if room["max_occupancy"] * rooms < adults:
                    continue

                # Check availability & price for dates
                room_price = await self._get_room_price(
                    room["room_id"], checkin_date, checkout_date
                )
                if room_price is None:
                    room_price = float(room["base_price"])

                total = room_price * num_nights * rooms

                if min_price and total < min_price:
                    continue
                if max_price and total > max_price:
                    continue

                available_rooms.append({
                    **room,
                    "price_per_night": room_price,
                    "total_price": total,
                    "num_nights": num_nights,
                })

            if available_rooms:
                results.append({
                    **hotel,
                    "available_rooms": available_rooms,
                    "min_price": min(r["price_per_night"] for r in available_rooms),
                })

        results.sort(key=lambda x: x["min_price"])
        return results

    async def get_hotel_detail(self, hotel_id: str) -> dict | None:
        """Chi tiết khách sạn + tất cả phòng."""
        result = self.supabase.table("hotels").select(
            "*, hotel_rooms(*)"
        ).eq("hotel_id", hotel_id).eq("is_active", True).execute()

        if not result.data:
            return None
        return result.data[0]

    async def _get_room_price(self, room_id: str, checkin: str, checkout: str) -> float | None:
        """Lấy giá phòng trung bình cho range ngày."""
        prices = self.supabase.table("hotel_room_prices").select("price").eq(
            "room_id", room_id
        ).gte("date", checkin).lt("date", checkout).eq(
            "available_rooms", True  # có phòng trống
        ).execute()

        if not prices.data:
            return None

        return sum(float(p["price"]) for p in prices.data) / len(prices.data)

    def _calc_nights(self, checkin: str, checkout: str) -> int:
        from datetime import datetime
        c1 = datetime.strptime(checkin, "%Y-%m-%d")
        c2 = datetime.strptime(checkout, "%Y-%m-%d")
        return max((c2 - c1).days, 1)
```

```python
# Backend/app/v1/services/internal_transport_service.py

class InternalTransportService:
    """Tìm kiếm xe/tàu từ internal database."""

    async def search_transport(
        self,
        origin_city: str,
        destination_city: str,
        travel_date: str,
        transport_type: str | None = None,
        seat_type: str | None = None,
        max_price: float | None = None,
    ) -> list[dict]:
        """Tìm tuyến xe/tàu + giá cho ngày."""
        day_name = self._get_day_name(travel_date)

        query = self.supabase.table("transport_routes").select(
            "*, transport_providers(name, type, logo_url), transport_schedules(*)"
        ).eq("origin_city", origin_city).eq(
            "destination_city", destination_city
        ).eq("is_active", True)

        if transport_type:
            query = query.eq("transport_type", transport_type)

        routes = query.execute()
        results = []

        for route in routes.data:
            for schedule in route.get("transport_schedules", []):
                if not schedule["is_active"]:
                    continue
                if day_name not in schedule.get("frequency", []) and "daily" not in schedule.get("frequency", []):
                    continue

                # Get price overrides for this date
                price_overrides = self.supabase.table("transport_prices").select(
                    "*"
                ).eq("schedule_id", schedule["schedule_id"]).eq(
                    "travel_date", travel_date
                ).execute()

                price_map = {p["seat_type"]: p for p in price_overrides.data}

                for seat_info in schedule.get("seat_types", []):
                    if seat_type and seat_info["type"] != seat_type:
                        continue

                    override = price_map.get(seat_info["type"])
                    price = float(override["price"]) if override else float(seat_info["base_price"])
                    available = override["available_seats"] if override else seat_info.get("total_seats", 40)

                    if max_price and price > max_price:
                        continue

                    results.append({
                        "route_id": route["route_id"],
                        "schedule_id": schedule["schedule_id"],
                        "provider": route["transport_providers"],
                        "transport_type": route["transport_type"],
                        "origin": route["origin_city"],
                        "destination": route["destination_city"],
                        "departure_time": schedule["departure_time"],
                        "arrival_time": schedule["arrival_time"],
                        "duration_minutes": route["duration_minutes"],
                        "distance_km": float(route["distance_km"]) if route["distance_km"] else None,
                        "amenities": route["amenities"],
                        "seat_type": seat_info["type"],
                        "price": price,
                        "available_seats": available,
                        "features": seat_info.get("features", []),
                        "source": "internal",
                    })

        results.sort(key=lambda x: x["price"])
        return results
```

### 12.4 MCP Tools — Updated (Internal)

```python
# Backend/app/v1/mcp/src/tools/flight_tools.py — REWRITE for internal

from fastmcp import tool
import json
from ....services.internal_flight_service import InternalFlightService

_flight_service = InternalFlightService()

@tool
async def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    adults: int = 1,
    travel_class: str | None = None,
    max_price: int | None = None,
    sort_by: str = "price",
) -> str:
    """
    Tìm kiếm chuyến bay từ cơ sở dữ liệu nội bộ.

    Args:
        origin: Mã sân bay đi IATA (HAN, SGN, DAD, DLI, CXR, PQC, HPH, VII, HUI)
        destination: Mã sân bay đến IATA
        departure_date: Ngày đi (YYYY-MM-DD)
        adults: Số người lớn (1-9)
        travel_class: Hạng vé — economy | premium_economy | business (null = tất cả)
        max_price: Giá tối đa VND
        sort_by: Sắp xếp — price | departure | duration

    Returns:
        JSON string danh sách chuyến bay với giá, giờ, hãng, ghế trống.
    """
    results = await _flight_service.search_flights(
        origin_code=origin, destination_code=destination,
        departure_date=departure_date, adults=adults,
        travel_class=travel_class, max_price=max_price,
        sort_by=sort_by,
    )
    return json.dumps(results, ensure_ascii=False)


@tool
async def get_airports() -> str:
    """
    Lấy danh sách tất cả sân bay trong hệ thống.

    Returns:
        JSON string danh sách sân bay: IATA code, tên, thành phố.
    """
    results = await _flight_service.get_airports()
    return json.dumps(results, ensure_ascii=False)


@tool
async def get_popular_flight_routes() -> str:
    """
    Lấy các tuyến bay phổ biến nhất.

    Returns:
        JSON string danh sách tuyến bay phổ biến.
    """
    results = await _flight_service.get_popular_routes()
    return json.dumps(results, ensure_ascii=False)
```

```python
# Backend/app/v1/mcp/src/tools/hotel_tools.py — REWRITE for internal

@tool
async def search_hotels(
    city: str,
    checkin_date: str,
    checkout_date: str,
    adults: int = 2,
    rooms: int = 1,
    star_ratings: list[int] | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
) -> str:
    """
    Tìm kiếm khách sạn từ cơ sở dữ liệu nội bộ.

    Args:
        city: Thành phố (vd: "Đà Lạt", "Nha Trang", "TP. Hồ Chí Minh")
        checkin_date: Ngày nhận phòng (YYYY-MM-DD)
        checkout_date: Ngày trả phòng (YYYY-MM-DD)
        adults: Số người lớn
        rooms: Số phòng
        star_ratings: Lọc số sao [3,4,5]
        min_price: Giá tối thiểu VND/đêm
        max_price: Giá tối đa VND/đêm

    Returns:
        JSON string danh sách khách sạn + phòng trống + giá.
    """
    results = await _hotel_service.search_hotels(
        city=city, checkin_date=checkin_date, checkout_date=checkout_date,
        adults=adults, rooms=rooms, star_ratings=star_ratings,
        min_price=min_price, max_price=max_price,
    )
    return json.dumps(results, ensure_ascii=False)


@tool
async def get_hotel_detail(hotel_id: str) -> str:
    """
    Chi tiết khách sạn + tất cả loại phòng.

    Args:
        hotel_id: ID khách sạn

    Returns:
        JSON string chi tiết khách sạn, phòng, tiện ích, giá.
    """
    result = await _hotel_service.get_hotel_detail(hotel_id)
    return json.dumps(result, ensure_ascii=False)
```

```python
# Backend/app/v1/mcp/src/tools/transport_tools.py — REWRITE for internal

@tool
async def search_transport(
    origin: str,
    destination: str,
    travel_date: str,
    transport_type: str | None = None,
    seat_type: str | None = None,
    max_price: int | None = None,
) -> str:
    """
    Tìm kiếm vé xe/tàu từ cơ sở dữ liệu nội bộ.

    Args:
        origin: Thành phố đi (vd: "TP. Hồ Chí Minh")
        destination: Thành phố đến (vd: "Đà Lạt")
        travel_date: Ngày đi (YYYY-MM-DD)
        transport_type: bus | train | limousine | van | ferry (null = tất cả)
        seat_type: Loại ghế (null = tất cả)
        max_price: Giá tối đa VND

    Returns:
        JSON string danh sách chuyến xe/tàu + giá + ghế trống.
    """
    results = await _transport_service.search_transport(
        origin_city=origin, destination_city=destination,
        travel_date=travel_date, transport_type=transport_type,
        seat_type=seat_type, max_price=max_price,
    )
    return json.dumps(results, ensure_ascii=False)
```

### 12.5 Admin Catalog CRUD — Thêm vào Admin Panel

#### Admin Flights Catalog

```python
# Backend/app/v1/api/endpoints/admin_flight_catalog.py

from fastapi import APIRouter, Depends
from typing import Dict
from ...services.admin_flight_catalog_service import AdminFlightCatalogService
from ...core.dependencies import get_current_admin

router = APIRouter(prefix="/admin/catalog/flights", tags=["Admin — Flight Catalog"])

# ---- Airlines ----
@router.get("/airlines")
async def list_airlines(admin: Dict = Depends(get_current_admin)):
    return AdminFlightCatalogService().get_airlines()

@router.post("/airlines")
async def create_airline(
    code: str, name: str, logo_url: str | None = None,
    admin: Dict = Depends(get_current_admin),
):
    return AdminFlightCatalogService().create_airline(code, name, logo_url)

@router.put("/airlines/{airline_id}")
async def update_airline(airline_id: str, data: dict, admin: Dict = Depends(get_current_admin)):
    return AdminFlightCatalogService().update_airline(airline_id, data)

@router.delete("/airlines/{airline_id}")
async def delete_airline(airline_id: str, admin: Dict = Depends(get_current_admin)):
    return AdminFlightCatalogService().delete_airline(airline_id)

# ---- Airports ----
@router.get("/airports")
async def list_airports(admin: Dict = Depends(get_current_admin)):
    return AdminFlightCatalogService().get_airports()

@router.post("/airports")
async def create_airport(data: dict, admin: Dict = Depends(get_current_admin)):
    return AdminFlightCatalogService().create_airport(data)

@router.put("/airports/{airport_id}")
async def update_airport(airport_id: str, data: dict, admin: Dict = Depends(get_current_admin)):
    return AdminFlightCatalogService().update_airport(airport_id, data)

@router.delete("/airports/{airport_id}")
async def delete_airport(airport_id: str, admin: Dict = Depends(get_current_admin)):
    return AdminFlightCatalogService().delete_airport(airport_id)

# ---- Flights ----
@router.get("")
async def list_flights(
    page: int = 1, limit: int = 20,
    airline_id: str | None = None,
    origin_id: str | None = None,
    destination_id: str | None = None,
    is_active: bool | None = None,
    admin: Dict = Depends(get_current_admin),
):
    return AdminFlightCatalogService().get_flights(
        page=page, limit=limit, airline_id=airline_id,
        origin_id=origin_id, destination_id=destination_id, is_active=is_active,
    )

@router.post("")
async def create_flight(data: dict, admin: Dict = Depends(get_current_admin)):
    """Tạo chuyến bay mới với travel_classes JSON."""
    return AdminFlightCatalogService().create_flight(data)

@router.put("/{flight_id}")
async def update_flight(flight_id: str, data: dict, admin: Dict = Depends(get_current_admin)):
    return AdminFlightCatalogService().update_flight(flight_id, data)

@router.delete("/{flight_id}")
async def delete_flight(flight_id: str, admin: Dict = Depends(get_current_admin)):
    return AdminFlightCatalogService().delete_flight(flight_id)

# ---- Flight Prices (giá theo ngày) ----
@router.get("/{flight_id}/prices")
async def get_flight_prices(
    flight_id: str,
    date_from: str | None = None,
    date_to: str | None = None,
    admin: Dict = Depends(get_current_admin),
):
    return AdminFlightCatalogService().get_flight_prices(flight_id, date_from, date_to)

@router.post("/{flight_id}/prices")
async def set_flight_price(
    flight_id: str,
    travel_date: str,
    travel_class: str,
    price: float,
    available_seats: int,
    is_promo: bool = False,
    admin: Dict = Depends(get_current_admin),
):
    """Set giá cho 1 ngày cụ thể (override base_price)."""
    return AdminFlightCatalogService().set_flight_price(
        flight_id, travel_date, travel_class, price, available_seats, is_promo,
    )

@router.post("/{flight_id}/prices/bulk")
async def bulk_set_prices(
    flight_id: str,
    prices: list[dict],  # [{date, class, price, seats}]
    admin: Dict = Depends(get_current_admin),
):
    """Set giá hàng loạt cho nhiều ngày (vd: set giá cả tháng)."""
    return AdminFlightCatalogService().bulk_set_prices(flight_id, prices)
```

```python
# Backend/app/v1/services/admin_flight_catalog_service.py

class AdminFlightCatalogService:

    # ---- Airlines ----
    def get_airlines(self):
        result = self.supabase.table("airlines").select("*").order("name").execute()
        return {"EC": 0, "data": result.data}

    def create_airline(self, code: str, name: str, logo_url: str | None = None):
        result = self.supabase.table("airlines").insert({
            "code": code.upper(), "name": name, "logo_url": logo_url,
        }).execute()
        return {"EC": 0, "EM": "Airline created", "data": result.data[0]}

    def update_airline(self, airline_id: str, data: dict):
        result = self.supabase.table("airlines").update(data).eq("airline_id", airline_id).execute()
        if not result.data:
            return {"EC": 1, "EM": "Airline not found"}
        return {"EC": 0, "EM": "Updated", "data": result.data[0]}

    def delete_airline(self, airline_id: str):
        # Check if has flights
        flights = self.supabase.table("flights").select("flight_id").eq("airline_id", airline_id).execute()
        if flights.data:
            return {"EC": 2, "EM": f"Cannot delete: airline has {len(flights.data)} flights"}
        self.supabase.table("airlines").delete().eq("airline_id", airline_id).execute()
        return {"EC": 0, "EM": "Deleted"}

    # ---- Airports ----
    def get_airports(self):
        result = self.supabase.table("airports").select("*").order("city").execute()
        return {"EC": 0, "data": result.data}

    def create_airport(self, data: dict):
        result = self.supabase.table("airports").insert(data).execute()
        return {"EC": 0, "EM": "Airport created", "data": result.data[0]}

    def update_airport(self, airport_id: str, data: dict):
        result = self.supabase.table("airports").update(data).eq("airport_id", airport_id).execute()
        if not result.data:
            return {"EC": 1, "EM": "Airport not found"}
        return {"EC": 0, "EM": "Updated", "data": result.data[0]}

    def delete_airport(self, airport_id: str):
        self.supabase.table("airports").delete().eq("airport_id", airport_id).execute()
        return {"EC": 0, "EM": "Deleted"}

    # ---- Flights ----
    def get_flights(self, **filters):
        query = self.supabase.table("flights").select(
            "*, airlines(code, name), origin:airports!flights_origin_id_fkey(*), "
            "destination:airports!flights_destination_id_fkey(*)"
        ).order("created_at", desc=True)

        if filters.get("airline_id"):
            query = query.eq("airline_id", filters["airline_id"])
        if filters.get("origin_id"):
            query = query.eq("origin_id", filters["origin_id"])
        if filters.get("destination_id"):
            query = query.eq("destination_id", filters["destination_id"])
        if filters.get("is_active") is not None:
            query = query.eq("is_active", filters["is_active"])

        page, limit = filters.get("page", 1), filters.get("limit", 20)
        result = query.range((page - 1) * limit, page * limit - 1).execute()
        return {"EC": 0, "data": result.data}

    def create_flight(self, data: dict):
        result = self.supabase.table("flights").insert(data).execute()
        return {"EC": 0, "EM": "Flight created", "data": result.data[0]}

    def update_flight(self, flight_id: str, data: dict):
        result = self.supabase.table("flights").update(data).eq("flight_id", flight_id).execute()
        if not result.data:
            return {"EC": 1, "EM": "Flight not found"}
        return {"EC": 0, "EM": "Updated", "data": result.data[0]}

    def delete_flight(self, flight_id: str):
        self.supabase.table("flights").delete().eq("flight_id", flight_id).execute()
        return {"EC": 0, "EM": "Deleted"}

    # ---- Prices ----
    def get_flight_prices(self, flight_id: str, date_from: str | None, date_to: str | None):
        query = self.supabase.table("flight_prices").select("*").eq("flight_id", flight_id)
        if date_from:
            query = query.gte("travel_date", date_from)
        if date_to:
            query = query.lte("travel_date", date_to)
        result = query.order("travel_date").execute()
        return {"EC": 0, "data": result.data}

    def set_flight_price(self, flight_id, travel_date, travel_class, price, available_seats, is_promo):
        # Upsert: nếu đã có giá cho ngày này thì update, không thì insert
        existing = self.supabase.table("flight_prices").select("price_id").eq(
            "flight_id", flight_id
        ).eq("travel_date", travel_date).eq("travel_class", travel_class).execute()

        if existing.data:
            self.supabase.table("flight_prices").update({
                "price": price, "available_seats": available_seats, "is_promo": is_promo,
            }).eq("price_id", existing.data[0]["price_id"]).execute()
        else:
            self.supabase.table("flight_prices").insert({
                "flight_id": flight_id, "travel_date": travel_date,
                "travel_class": travel_class, "price": price,
                "available_seats": available_seats, "is_promo": is_promo,
            }).execute()

        return {"EC": 0, "EM": "Price set"}

    def bulk_set_prices(self, flight_id: str, prices: list[dict]):
        for p in prices:
            self.set_flight_price(
                flight_id, p["date"], p["travel_class"],
                p["price"], p.get("available_seats", 180), p.get("is_promo", False),
            )
        return {"EC": 0, "EM": f"Set {len(prices)} prices"}
```

#### Admin Hotels Catalog

```python
# Backend/app/v1/api/endpoints/admin_hotel_catalog.py

router = APIRouter(prefix="/admin/catalog/hotels", tags=["Admin — Hotel Catalog"])

# ---- Hotels ----
@router.get("")            # list hotels with filters
@router.post("")           # create hotel
@router.get("/{hotel_id}") # detail + rooms
@router.put("/{hotel_id}") # update hotel info
@router.delete("/{hotel_id}") # delete hotel
@router.post("/{hotel_id}/images") # upload images to Cloudinary

# ---- Rooms ----
@router.get("/{hotel_id}/rooms")        # list rooms
@router.post("/{hotel_id}/rooms")       # add room type
@router.put("/rooms/{room_id}")         # update room
@router.delete("/rooms/{room_id}")      # delete room

# ---- Room Prices ----
@router.get("/rooms/{room_id}/prices")        # price calendar
@router.post("/rooms/{room_id}/prices")       # set price for date
@router.post("/rooms/{room_id}/prices/bulk")  # bulk set prices
```

#### Admin Transport Catalog

```python
# Backend/app/v1/api/endpoints/admin_transport_catalog.py

router = APIRouter(prefix="/admin/catalog/transport", tags=["Admin — Transport Catalog"])

# ---- Providers ----
@router.get("/providers")
@router.post("/providers")
@router.put("/providers/{provider_id}")
@router.delete("/providers/{provider_id}")

# ---- Routes ----
@router.get("/routes")
@router.post("/routes")
@router.put("/routes/{route_id}")
@router.delete("/routes/{route_id}")

# ---- Schedules ----
@router.get("/routes/{route_id}/schedules")
@router.post("/routes/{route_id}/schedules")
@router.put("/schedules/{schedule_id}")
@router.delete("/schedules/{schedule_id}")

# ---- Prices ----
@router.get("/schedules/{schedule_id}/prices")
@router.post("/schedules/{schedule_id}/prices")
@router.post("/schedules/{schedule_id}/prices/bulk")
```

### 12.6 Frontend Admin — Catalog Management Pages

#### Cấu trúc component mới

```
Frontend/src/app/pages/admin/
├── flight-catalog/                # Quản lý chuyến bay (internal)
│   ├── flight-catalog.component.ts
│   └── flight-catalog.component.html
│   # Tab 1: Airlines (CRUD table)
│   # Tab 2: Airports (CRUD table)
│   # Tab 3: Flights (CRUD table + modal form phức tạp)
│   # Tab 4: Flight Prices (calendar view — set giá theo ngày)
│
├── hotel-catalog/                 # Quản lý khách sạn (internal)
│   ├── hotel-catalog.component.ts
│   └── hotel-catalog.component.html
│   # Tab 1: Hotels (CRUD + image upload)
│   # Tab 2: Rooms (CRUD per hotel)
│   # Tab 3: Room Prices (calendar view)
│
├── transport-catalog/             # Quản lý xe/tàu (internal)
│   ├── transport-catalog.component.ts
│   └── transport-catalog.component.html
│   # Tab 1: Providers (CRUD)
│   # Tab 2: Routes (CRUD)
│   # Tab 3: Schedules (CRUD per route)
│   # Tab 4: Prices (calendar view)

Frontend/src/app/services/admin/
├── admin-flight-catalog.service.ts
├── admin-hotel-catalog.service.ts
└── admin-transport-catalog.service.ts
```

#### Admin Flight Catalog Component

```typescript
// Frontend/src/app/pages/admin/flight-catalog/flight-catalog.component.ts

@Component({
  selector: 'app-admin-flight-catalog',
  templateUrl: './flight-catalog.component.html',
  standalone: true,
})
export class AdminFlightCatalogComponent implements OnInit {
  activeTab = 'flights'; // airlines | airports | flights | prices

  // Airlines
  airlines: any[] = [];
  showAirlineModal = false;
  airlineForm = { code: '', name: '', logo_url: '' };

  // Airports
  airports: any[] = [];
  showAirportModal = false;
  airportForm = { iata_code: '', name: '', city: '', country: 'Vietnam', latitude: null, longitude: null };

  // Flights
  flights: any[] = [];
  showFlightModal = false;
  flightForm = {
    flight_code: '',
    airline_id: '',
    origin_id: '',
    destination_id: '',
    departure_time: '',
    arrival_time: '',
    duration_minutes: 0,
    aircraft_type: '',
    travel_classes: {
      economy: { base_price: 0, baggage_included: 20, meal_included: false, refundable: false, change_fee: 300000 },
    },
    frequency: ['daily'],
    effective_from: '',
  };

  // Price Calendar
  selectedFlightForPrices: any = null;
  priceMonth: string = ''; // "2026-06"
  priceCalendar: any[] = []; // [{date, economy: {price, seats}, business: {price, seats}}]
  showPriceModal = false;
  priceForm = { date: '', travel_class: 'economy', price: 0, available_seats: 180, is_promo: false };

  constructor(
    private catalogService: AdminFlightCatalogService,
  ) {}

  ngOnInit() {
    this.loadData();
  }

  async loadData() {
    const [airlines, airports, flights]: any[] = await Promise.all([
      this.catalogService.getAirlines().toPromise(),
      this.catalogService.getAirports().toPromise(),
      this.catalogService.getFlights().toPromise(),
    ]);
    this.airlines = airlines?.data || [];
    this.airports = airports?.data || [];
    this.flights = flights?.data || [];
  }

  // Airlines CRUD
  async saveAirline() {
    const res: any = await this.catalogService.createAirline(this.airlineForm).toPromise();
    if (res?.EC === 0) { this.showAirlineModal = false; this.loadData(); }
  }

  async deleteAirline(id: string) {
    if (!confirm('Xóa hãng bay này?')) return;
    const res: any = await this.catalogService.deleteAirline(id).toPromise();
    if (res?.EC === 0) this.loadData();
    else alert(res?.EM || 'Xóa thất bại');
  }

  // Flights CRUD
  async saveFlight() {
    const res: any = this.flightForm['flight_id']
      ? await this.catalogService.updateFlight(this.flightForm['flight_id'], this.flightForm).toPromise()
      : await this.catalogService.createFlight(this.flightForm).toPromise();
    if (res?.EC === 0) { this.showFlightModal = false; this.loadData(); }
  }

  // Price Calendar
  async loadPriceCalendar(flight: any) {
    this.selectedFlightForPrices = flight;
    const [year, month] = this.priceMonth.split('-');
    const dateFrom = `${year}-${month}-01`;
    const dateTo = `${year}-${month}-31`;
    const res: any = await this.catalogService.getFlightPrices(
      flight.flight_id, dateFrom, dateTo
    ).toPromise();
    this.priceCalendar = res?.data || [];
  }

  async savePrice() {
    const res: any = await this.catalogService.setFlightPrice(
      this.selectedFlightForPrices.flight_id,
      this.priceForm.date,
      this.priceForm.travel_class,
      this.priceForm.price,
      this.priceForm.available_seats,
      this.priceForm.is_promo,
    ).toPromise();
    if (res?.EC === 0) {
      this.showPriceModal = false;
      this.loadPriceCalendar(this.selectedFlightForPrices);
    }
  }

  // Bulk price — set giá cho cả tháng
  async bulkSetPrices() {
    const prices = [];
    const [year, month] = this.priceMonth.split('-');
    const daysInMonth = new Date(parseInt(year), parseInt(month), 0).getDate();
    for (let d = 1; d <= daysInMonth; d++) {
      prices.push({
        date: `${year}-${month}-${String(d).padStart(2, '0')}`,
        travel_class: this.priceForm.travel_class,
        price: this.priceForm.price,
        available_seats: this.priceForm.available_seats,
      });
    }
    const res: any = await this.catalogService.bulkSetPrices(
      this.selectedFlightForPrices.flight_id, prices
    ).toPromise();
    if (res?.EC === 0) this.loadPriceCalendar(this.selectedFlightForPrices);
  }
}
```

#### Template — Tab Layout

```html
<!-- flight-catalog.component.html -->
<div class="p-6">
  <h2 class="text-2xl font-bold mb-6">Quản lý Chuyến bay (Catalog)</h2>

  <!-- Tabs -->
  <div class="flex gap-1 mb-6 border-b">
    <button *ngFor="let tab of [
      {key:'airlines', label:'Hãng bay'},
      {key:'airports', label:'Sân bay'},
      {key:'flights', label:'Chuyến bay'},
      {key:'prices', label:'Giá vé'}
    ]"
      (click)="activeTab = tab.key"
      [class]="activeTab === tab.key
        ? 'px-4 py-2 border-b-2 border-blue-600 text-blue-600 font-medium'
        : 'px-4 py-2 text-gray-500 hover:text-gray-700'">
      {{ tab.label }}
    </button>
  </div>

  <!-- Tab: Airlines -->
  <div *ngIf="activeTab === 'airlines'">
    <div class="flex justify-between mb-4">
      <h3 class="text-lg font-semibold">Danh sách hãng bay</h3>
      <button (click)="showAirlineModal = true" class="px-4 py-2 bg-blue-600 text-white rounded-lg">
        + Thêm hãng bay
      </button>
    </div>
    <table class="w-full bg-white rounded-lg shadow">
      <thead class="bg-gray-50">
        <tr>
          <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Mã</th>
          <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tên</th>
          <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Logo</th>
          <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Trạng thái</th>
          <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Thao tác</th>
        </tr>
      </thead>
      <tbody class="divide-y">
        <tr *ngFor="let a of airlines" class="hover:bg-gray-50">
          <td class="px-4 py-3 font-mono font-bold">{{ a.code }}</td>
          <td class="px-4 py-3">{{ a.name }}</td>
          <td class="px-4 py-3"><img *ngIf="a.logo_url" [src]="a.logo_url" class="h-8"></td>
          <td class="px-4 py-3">
            <span [class]="a.is_active ? 'text-green-600' : 'text-red-600'">
              {{ a.is_active ? 'Hoạt động' : 'Đã ẩn' }}
            </span>
          </td>
          <td class="px-4 py-3">
            <button (click)="editAirline(a)" class="text-blue-600 mr-2">Sửa</button>
            <button (click)="deleteAirline(a.airline_id)" class="text-red-600">Xóa</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- Tab: Airports (same table pattern) -->

  <!-- Tab: Flights -->
  <div *ngIf="activeTab === 'flights'">
    <div class="flex justify-between mb-4">
      <h3 class="text-lg font-semibold">Danh sách chuyến bay</h3>
      <button (click)="openAddFlight()" class="px-4 py-2 bg-blue-600 text-white rounded-lg">
        + Thêm chuyến bay
      </button>
    </div>
    <table class="w-full bg-white rounded-lg shadow">
      <thead class="bg-gray-50">
        <tr>
          <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Mã chuyến</th>
          <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Hãng</th>
          <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tuyến</th>
          <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Giờ bay</th>
          <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Bay vào</th>
          <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Thời lượng</th>
          <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Giá từ</th>
          <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Thao tác</th>
        </tr>
      </thead>
      <tbody class="divide-y">
        <tr *ngFor="let f of flights" class="hover:bg-gray-50">
          <td class="px-4 py-3 font-mono font-bold">{{ f.flight_code }}</td>
          <td class="px-4 py-3">{{ f.airlines?.name }}</td>
          <td class="px-4 py-3">{{ f.origin?.iata_code }} → {{ f.destination?.iata_code }}</td>
          <td class="px-4 py-3">{{ f.departure_time }}</td>
          <td class="px-4 py-3">
            <span *ngFor="let day of f.frequency" class="px-1 text-xs">{{ day }}</span>
          </td>
          <td class="px-4 py-3">{{ f.duration_minutes }} phút</td>
          <td class="px-4 py-3 font-medium">
            {{ formatPrice(f.travel_classes?.economy?.base_price || 0) }}
          </td>
          <td class="px-4 py-3">
            <button (click)="openEditFlight(f)" class="text-blue-600 mr-2">Sửa</button>
            <button (click)="openPriceCalendar(f)" class="text-green-600 mr-2">Giá</button>
            <button (click)="deleteFlight(f.flight_id)" class="text-red-600">Xóa</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- Tab: Price Calendar -->
  <div *ngIf="activeTab === 'prices' && selectedFlightForPrices">
    <div class="flex justify-between items-center mb-4">
      <h3 class="text-lg font-semibold">
        Giá vé: {{ selectedFlightForPrices.flight_code }}
        ({{ selectedFlightForPrices.origin?.iata_code }} → {{ selectedFlightForPrices.destination?.iata_code }})
      </h3>
      <div class="flex gap-2 items-center">
        <input type="month" [(ngModel)]="priceMonth" (ngModelChange)="loadPriceCalendar(selectedFlightForPrices)"
               class="border rounded px-3 py-2">
        <button (click)="bulkSetPrices()" class="px-4 py-2 bg-orange-500 text-white rounded-lg">
          Set giá cả tháng
        </button>
      </div>
    </div>

    <!-- Calendar Grid -->
    <div class="grid grid-cols-7 gap-1">
      <div *ngFor="let day of ['T2','T3','T4','T5','T6','T7','CN']"
           class="text-center text-xs font-medium text-gray-500 py-2">{{ day }}</div>
      <div *ngFor="let d of calendarDays" class="border rounded p-2 min-h-[80px]"
           [class.bg-blue-50]="d.isToday">
        <div class="text-xs text-gray-400 mb-1">{{ d.day }}</div>
        <div *ngIf="d.prices" class="text-xs">
          <div *ngFor="let p of d.prices" class="mb-1">
            <span class="font-medium">{{ p.travel_class }}:</span>
            <span class="text-green-600">{{ formatPrice(p.price) }}</span>
            <br><span class="text-gray-400">{{ p.available_seats }} ghế</span>
          </div>
        </div>
        <button *ngIf="d.day" (click)="openSetPriceModal(d)"
                class="text-xs text-blue-500 hover:underline mt-1">
          {{ d.prices ? 'Sửa' : '+ Thêm' }}
        </button>
      </div>
    </div>
  </div>
</div>

<!-- Airline Modal -->
<div *ngIf="showAirlineModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
  <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6">
    <h3 class="text-lg font-semibold mb-4">{{ airlineForm.airline_id ? 'Sửa' : 'Thêm' }} hãng bay</h3>
    <div class="space-y-4">
      <div>
        <label class="block text-sm font-medium mb-1">Mã hãng *</label>
        <input [(ngModel)]="airlineForm.code" class="w-full border rounded px-3 py-2" placeholder="VN" maxlength="10">
      </div>
      <div>
        <label class="block text-sm font-medium mb-1">Tên hãng *</label>
        <input [(ngModel)]="airlineForm.name" class="w-full border rounded px-3 py-2" placeholder="Vietnam Airlines">
      </div>
    </div>
    <div class="flex gap-3 mt-6">
      <button (click)="showAirlineModal = false" class="flex-1 px-4 py-2 border rounded-lg">Hủy</button>
      <button (click)="saveAirline()" class="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg">Lưu</button>
    </div>
  </div>
</div>

<!-- Flight Modal (form phức tạp hơn) -->
<div *ngIf="showFlightModal" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
  <div class="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[95vh] overflow-y-auto">
    <div class="px-6 py-4 border-b">
      <h3 class="text-lg font-semibold">Thêm chuyến bay mới</h3>
    </div>
    <div class="p-6 space-y-6">
      <!-- Basic -->
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium mb-1">Mã chuyến *</label>
          <input [(ngModel)]="flightForm.flight_code" class="w-full border rounded px-3 py-2" placeholder="VN247">
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Hãng bay *</label>
          <select [(ngModel)]="flightForm.airline_id" class="w-full border rounded px-3 py-2">
            <option *ngFor="let a of airlines" [value]="a.airline_id">{{ a.name }} ({{ a.code }})</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Sân bay đi *</label>
          <select [(ngModel)]="flightForm.origin_id" class="w-full border rounded px-3 py-2">
            <option *ngFor="let apt of airports" [value]="apt.airport_id">{{ apt.city }} ({{ apt.iata_code }})</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Sân bay đến *</label>
          <select [(ngModel)]="flightForm.destination_id" class="w-full border rounded px-3 py-2">
            <option *ngFor="let apt of airports" [value]="apt.airport_id">{{ apt.city }} ({{ apt.iata_code }})</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Giờ khởi hành *</label>
          <input [(ngModel)]="flightForm.departure_time" type="time" class="w-full border rounded px-3 py-2">
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Giờ đến *</label>
          <input [(ngModel)]="flightForm.arrival_time" type="time" class="w-full border rounded px-3 py-2">
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Thời lượng (phút) *</label>
          <input [(ngModel)]="flightForm.duration_minutes" type="number" class="w-full border rounded px-3 py-2">
        </div>
        <div>
          <label class="block text-sm font-medium mb-1">Loại máy bay</label>
          <input [(ngModel)]="flightForm.aircraft_type" class="w-full border rounded px-3 py-2" placeholder="Airbus A321">
        </div>
      </div>

      <!-- Travel Classes -->
      <div>
        <h4 class="font-medium mb-2">Hạng vé & Giá cơ bản</h4>
        <div class="space-y-3">
          <div class="grid grid-cols-4 gap-3 items-end bg-gray-50 p-3 rounded">
            <div>
              <label class="block text-xs font-medium mb-1">Hạng</label>
              <span class="text-sm font-medium">Economy</span>
            </div>
            <div>
              <label class="block text-xs font-medium mb-1">Giá cơ bản (VND)</label>
              <input [(ngModel)]="flightForm.travel_classes.economy.base_price" type="number"
                     class="w-full border rounded px-2 py-1 text-sm">
            </div>
            <div>
              <label class="block text-xs font-medium mb-1">Hành lý (kg)</label>
              <input [(ngModel)]="flightForm.travel_classes.economy.baggage_included" type="number"
                     class="w-full border rounded px-2 py-1 text-sm">
            </div>
            <label class="flex items-center gap-2">
              <input [(ngModel)]="flightForm.travel_classes.economy.meal_included" type="checkbox">
              <span class="text-sm">Bao ăn</span>
            </label>
          </div>
          <!-- Similar for premium_economy, business -->
        </div>
      </div>

      <!-- Frequency -->
      <div>
        <label class="block text-sm font-medium mb-1">Ngày bay *</label>
        <div class="flex gap-2">
          <button *ngFor="let day of ['mon','tue','wed','thu','fri','sat','sun']"
                  (click)="toggleDay(day)"
                  [class]="flightForm.frequency.includes(day)
                    ? 'px-3 py-1 bg-blue-600 text-white rounded text-sm'
                    : 'px-3 py-1 bg-gray-200 rounded text-sm'">
            {{ day }}
          </button>
          <button (click)="flightForm.frequency = ['daily']"
                  [class]="flightForm.frequency.includes('daily')
                    ? 'px-3 py-1 bg-green-600 text-white rounded text-sm'
                    : 'px-3 py-1 bg-gray-200 rounded text-sm'">
            Hàng ngày
          </button>
        </div>
      </div>
    </div>
    <div class="px-6 py-4 border-t bg-gray-50 flex justify-end gap-3">
      <button (click)="showFlightModal = false" class="px-4 py-2 border rounded-lg">Hủy</button>
      <button (click)="saveFlight()" class="px-6 py-2 bg-blue-600 text-white rounded-lg">Lưu</button>
    </div>
  </div>
</div>
```

### 12.7 Updated Admin Routes

```typescript
// app.routes.ts — admin children bổ sung catalog routes
{
  path: 'admin',
  component: AdminLayoutComponent,
  children: [
    // ... existing routes ...

    // Catalog management (internal data)
    { path: 'catalog/flights', component: AdminFlightCatalogComponent },
    { path: 'catalog/hotels', component: AdminHotelCatalogComponent },
    { path: 'catalog/transport', component: AdminTransportCatalogComponent },

    // Booking management (user bookings)
    { path: 'flights', component: AdminFlightBookingListComponent },
    { path: 'hotels', component: AdminHotelBookingListComponent },
    { path: 'transport', component: AdminTransportBookingListComponent },

    // Tour Builder management
    { path: 'tour-sessions', component: AdminSessionListComponent },
    { path: 'custom-tours', component: AdminCustomTourListComponent },
  ]
}
```

### 12.8 Admin Sidebar — Updated Menu

```typescript
// Menu items với Catalog group
{
  label: 'Catalog Data',  // Group header
  items: [
    { label: 'Chuyến bay', icon: 'fa-plane', route: '/admin/catalog/flights' },
    { label: 'Khách sạn', icon: 'fa-hotel', route: '/admin/catalog/hotels' },
    { label: 'Xe & Tàu', icon: 'fa-bus', route: '/admin/catalog/transport' },
    { label: 'Tour Sessions', icon: 'fa-puzzle-piece', route: '/admin/tour-sessions' },
  ]
},
{
  label: 'Quản lý Booking',
  items: [
    { label: 'Booking Tour', icon: 'fa-bookmark', route: '/admin/bookings' },
    { label: 'Vé máy bay', icon: 'fa-ticket', route: '/admin/flights' },
    { label: 'Khách sạn', icon: 'fa-bed', route: '/admin/hotels' },
    { label: 'Vé xe/tàu', icon: 'fa-bus', route: '/admin/transport' },
    { label: 'Custom Tours', icon: 'fa-map', route: '/admin/custom-tours' },
  ]
},
```

### 12.9 Tổng hợp files Internal Catalog

```
Backend/
├── app/v1/services/
│   ├── internal_flight_service.py        # Search flights từ internal DB
│   ├── internal_hotel_service.py         # Search hotels từ internal DB
│   └── internal_transport_service.py     # Search transport từ internal DB
├── app/v1/api/endpoints/
│   ├── admin_flight_catalog.py           # CRUD airlines, airports, flights, prices
│   ├── admin_hotel_catalog.py            # CRUD hotels, rooms, room prices
│   └── admin_transport_catalog.py        # CRUD providers, routes, schedules, prices
├── app/v1/services/
│   ├── admin_flight_catalog_service.py
│   ├── admin_hotel_catalog_service.py
│   └── admin_transport_catalog_service.py
├── app/v1/mcp/src/tools/
│   ├── flight_tools.py                   # REWRITE: search internal DB
│   ├── hotel_tools.py                    # REWRITE: search internal DB
│   └── transport_tools.py               # REWRITE: search internal DB

Frontend/
├── pages/admin/
│   ├── flight-catalog/                   # Tab: Airlines | Airports | Flights | Prices
│   ├── hotel-catalog/                    # Tab: Hotels | Rooms | Prices
│   └── transport-catalog/                # Tab: Providers | Routes | Schedules | Prices
├── services/admin/
│   ├── admin-flight-catalog.service.ts
│   ├── admin-hotel-catalog.service.ts
│   └── admin-transport-catalog.service.ts

Database:
├── airlines, airports, flights, flight_prices
├── hotels, hotel_rooms, hotel_room_prices
├── transport_providers, transport_routes, transport_schedules, transport_prices
```

### 12.10 So sánh: External API vs Internal Catalog

| Khía cạnh | External API | Internal Catalog |
|---|---|---|
| **Chi phí** | Trả phí theo API call | Miễn phí (data tự quản lý) |
| **Dependency** | Phụ thuộc bên thứ 3 | Hoàn toàn tự chủ |
| **Data control** | Giới hạn bởi API | Toàn quyền thêm/sửa/xóa |
| **Tính năng** | Real-time đầy đủ | Cần admin nhập data |
| **Phù hợp** | MVP nhanh, test thị trường | Sản phẩm production, ổn định |
| **Khuyến nghị** | Dùng khi bắt đầu | Chuyển dần sang internal |

**Chiến lược hybrid (khuyến nghị):**
1. Bắt đầu với external API để có data nhanh
2. Song song xây internal catalog
3. Internal làm primary, external làm fallback
4. Khi internal data đủ → bỏ external dependency

---

## 13. Testing Strategy

> Phần này sẽ được bổ sung trong một revision riêng (pytest cho services, FastMCP in-memory client, Angular Jest + Playwright). Trước mắt dùng pattern test có sẵn ở `Backend/tests/` cho services hiện có.

---

## 14. Azure AI Travel Agents Pattern Integration

### 14.1 Bối cảnh và mục tiêu

Azure-Samples/azure-ai-travel-agents minh hoạ một travel-agency app dùng **nhiều AI agent chuyên biệt**, mỗi agent giải một bài toán hẹp và được orchestrate bởi LangChain.js / LlamaIndex.TS / Microsoft Agent Framework. Tool sống ở nhiều **MCP server tách biệt** (Python, Node, Java, .NET). Bốn agent mẫu trong repo:

| Agent | Vai trò |
|---|---|
| Customer Query Understanding | Trích xuất preference từ câu hỏi tự do |
| Destination Recommendation | Gợi ý điểm đến dựa trên preference |
| Itinerary Planning | Lập lịch trình chi tiết |
| Echo Ping | MCP server mẫu để debug protocol |

Mục tiêu của Section này là **đem pattern đó vào codebase Python hiện tại** (LangGraph + FastMCP + FastAPI + Angular) mà không phá kiến trúc đã chạy. Quan điểm thiết kế:

- Giữ nguyên `SupervisorGraph`, `RecommendationAgent`, `AdminGraph`, `NewsSearchAgent`.
- Thêm hai agent chuyên biệt mới: `CustomerQueryAgent` và `ItineraryAgent`.
- Đẩy `RecommendationAgent` hiện có lên ngang hàng với hai agent mới, để Supervisor route tới chúng qua tool.
- Tách MCP server theo domain (vẫn dùng FastMCP) để dễ scale và dễ test, mở đường cho việc thay-thế ngôn ngữ cho từng MCP server.
- Có một MCP server `echo` rất nhỏ để kiểm tra hệ thống MCP.

### 14.2 Mapping pattern Azure ↔ codebase hiện tại

| Azure agent | Trạng thái KLTN | Hành động đề xuất |
|---|---|---|
| Customer Query Understanding | **Chưa có** | Thêm `CustomerQueryAgent` (LangGraph node) làm bước NLU đầu vào |
| Destination Recommendation | **Đã có** (`RecommendationAgent`) | Thêm tool `recommend_destinations` để Supervisor gọi explicit |
| Itinerary Planning | **Chưa có** | Thêm `ItineraryAgent` + MCP tool `build_itinerary` |
| Echo Ping | **Chưa có** | Thêm sub-server `echo_mcp` để debug, không động tới luồng chính |
| Orchestrator (LangChain.js / LlamaIndex.TS / MS Agent Framework) | **LangGraph SupervisorGraph** | Mở rộng SupervisorGraph thành router thuần, không tự gọi LLM trả lời cuối |
| MCP servers (Python/Node/Java/.NET) | **FastMCP gộp 4 sub-server** | Tách thêm sub-server theo domain, vẫn FastMCP để Python-only |
| Aspire Dashboard OpenTelemetry | **Chưa có** | Bật OpenTelemetry FastAPI + LangChain, export sang OTLP collector |

### 14.3 Kiến trúc đề xuất

```
+-------------------------------------------------------------+
|                    Angular Frontend                         |
|  ai-chatbot (toggle: classic | multi-agent mode)            |
+-----------------------------+-------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|              FastAPI  /api/v1                               |
|                                                             |
|  /chat/stream   ->  AgentRouter                             |
|                       |                                     |
|                       v                                     |
|  SupervisorGraph (LangGraph)                                |
|    1) customer_query_agent  (NLU: parse intent + slots)     |
|    2) route_to_specialist                                   |
|         |--- destination -> RecommendationAgent             |
|         |--- itinerary   -> ItineraryAgent                  |
|         |--- booking     -> chat_tools (booking tools)      |
|         |--- transactional -> chat_tools (payment, OTP)     |
|    3) reply_synthesizer    (gop output -> noi tu nhien)     |
|                                                             |
|  AdminGraph (rieng)        NewsSearchAgent (rieng)          |
+-----------------------------+-------------------------------+
                              |
                              | fastmcp.Client (HTTP/SSE)
                              v
+-------------------------------------------------------------+
| FastMCP composite server  /mcp                              |
|   booking_mcp       (booking, payment, OTP)                 |
|   tour_search_mcp   (search_tour_packages, episodes)        |
|   destination_mcp   (NEW: recommend_destinations)           |
|   itinerary_mcp     (NEW: build_itinerary, optimize_route)  |
|   flight_mcp        (search_flights, offers, book)          |
|   weather_mcp       (current, forecast)                     |
|   echo_mcp          (NEW: ping/echo - debug)                |
+-------------------------------------------------------------+
                              |
                              v
        Supabase pgvector | Redis | Mem0 | Cloudinary
        OpenWeatherMap | AviationStack | Amadeus | VNPay
```

### 14.4 Multi-MCP server: tách theo domain

`Backend/app/v1/mcp/server.py` hiện đã có pattern `import_server`. Mở rộng cấu trúc:

```
Backend/app/v1/mcp/src/tools/
  booking_tools.py                     # da co
  tour_search_tools.py                 # da co
  search_personalization.py            # da co
  weather_tools.py                     # da co
  flight_tools.py                      # da co
  destination_tools.py                 # NEW (Section 14.6)
  itinerary_tools.py                   # NEW (Section 14.7)
  echo_tools.py                        # NEW (Section 14.8)
```

```python
# Backend/app/v1/mcp/server.py (cap nhat)

from fastmcp import FastMCP

from .src.tools.booking_tools import register_booking_tools
from .src.tools.tour_search_tools import register_tour_search_tools
from .src.tools.search_personalization import register_search_personalization_tools
from .src.tools.weather_tools import register_weather_tools
from .src.tools.flight_tools import register_flight_tools
from .src.tools.destination_tools import register_destination_tools
from .src.tools.itinerary_tools import register_itinerary_tools
from .src.tools.echo_tools import register_echo_tools


def build_main_mcp() -> FastMCP:
    main = FastMCP("kltn-travel")

    booking_mcp = FastMCP("booking")
    register_booking_tools(booking_mcp)

    search_mcp = FastMCP("search")
    register_tour_search_tools(search_mcp)
    register_search_personalization_tools(search_mcp)

    weather_mcp = FastMCP("weather")
    register_weather_tools(weather_mcp)

    flight_mcp = FastMCP("flight")
    register_flight_tools(flight_mcp)

    destination_mcp = FastMCP("destination")
    register_destination_tools(destination_mcp)

    itinerary_mcp = FastMCP("itinerary")
    register_itinerary_tools(itinerary_mcp)

    echo_mcp = FastMCP("echo")
    register_echo_tools(echo_mcp)

    for sub in (
        booking_mcp, search_mcp, weather_mcp, flight_mcp,
        destination_mcp, itinerary_mcp, echo_mcp,
    ):
        main.import_server(sub, prefix=sub.name)

    return main


mcp = build_main_mcp()
```

Lợi ích so với bản gộp 1-file:

- Mỗi sub-server có namespace (prefix) riêng, không xung đột tên tool.
- Có thể tách thành micro-process khi cần (chạy 1 FastMCP process / domain) bằng cách thay `import_server` bằng MCP HTTP client.
- Test từng sub-server độc lập với `Client(sub_server)` (FastMCP in-memory).

### 14.5 Agent mới #1 — Customer Query Understanding

Mục đích: chuyển câu hỏi tự do thành **struct JSON** chuẩn (intent + slot), giúp các agent sau làm việc deterministic.

```python
# Backend/app/v1/services/agent_services/customer_query_agent.py

from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI


Intent = Literal[
    "search_tour",
    "recommend_destination",
    "plan_itinerary",
    "search_flight",
    "search_hotel",
    "search_transport",
    "booking_action",
    "small_talk",
]


class CustomerPreferences(BaseModel):
    intent: Intent
    origin: str | None = Field(None, description="Diem di IATA hoac ten thanh pho")
    destination: str | None = None
    start_date: str | None = Field(None, description="YYYY-MM-DD")
    end_date: str | None = None
    adults: int | None = None
    children: int | None = None
    budget_vnd: int | None = None
    interests: list[str] = Field(default_factory=list)
    travel_style: Literal["relaxed", "adventurous", "budget", "luxury"] | None = None
    constraints: list[str] = Field(default_factory=list)
    raw_query: str


class CustomerQueryAgent:
    """Single-shot NLU: free text -> CustomerPreferences."""

    def __init__(self, llm: ChatOpenAI) -> None:
        self.llm = llm.with_structured_output(CustomerPreferences)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Ban la NLU agent. Trich xuat intent va cac slot tu cau hoi "
                    "cua khach hang du lich. Khong tu hoi lai, chi tra ve JSON. "
                    "Neu thieu, de None / list rong. Tra loi bang JSON dung schema.",
                ),
                ("human", "{query}"),
            ]
        )

    async def parse(self, query: str) -> CustomerPreferences:
        chain = self.prompt | self.llm
        return await chain.ainvoke({"query": query})
```

Tích hợp vào `SupervisorGraph` như một **node đầu vào**:

```python
# Backend/app/v1/services/agent_services/graphs/supervisor_graph.py (snippet)

from langgraph.graph import StateGraph, START, END

from ..customer_query_agent import CustomerQueryAgent, CustomerPreferences


class SupervisorState(TypedDict):
    user_id: str
    user_query: str
    preferences: CustomerPreferences | None
    route: str | None
    tool_results: list[dict]
    final_answer: str | None


async def node_understand(state: SupervisorState) -> dict:
    prefs = await customer_query_agent.parse(state["user_query"])
    return {"preferences": prefs, "route": prefs.intent}


def build_supervisor() -> StateGraph:
    graph = StateGraph(SupervisorState)
    graph.add_node("understand", node_understand)
    graph.add_node("recommend_destination", recommendation_node)
    graph.add_node("plan_itinerary", itinerary_node)
    graph.add_node("chat_tools", chat_tools_node)
    graph.add_node("reply", reply_synth_node)

    graph.add_edge(START, "understand")
    graph.add_conditional_edges(
        "understand",
        lambda s: s["route"],
        {
            "recommend_destination": "recommend_destination",
            "plan_itinerary": "plan_itinerary",
            "search_tour": "chat_tools",
            "search_flight": "chat_tools",
            "search_hotel": "chat_tools",
            "search_transport": "chat_tools",
            "booking_action": "chat_tools",
            "small_talk": "reply",
        },
    )
    for node in ("recommend_destination", "plan_itinerary", "chat_tools"):
        graph.add_edge(node, "reply")
    graph.add_edge("reply", END)
    return graph
```

### 14.6 Agent mới #2 — Destination Recommendation (tool hoá)

`RecommendationAgent` đã có. Việc cần làm là expose nó như **một MCP tool** để Supervisor / chat_tools đều gọi được.

```python
# Backend/app/v1/mcp/src/tools/destination_tools.py

import json

from fastmcp import FastMCP

from app.v1.services.agent_services.recommendation_agent import RecommendationAgent


def register_destination_tools(mcp: FastMCP) -> None:
    agent = RecommendationAgent()

    @mcp.tool()
    async def recommend_destinations(
        interests: list[str],
        travel_style: str | None = None,
        budget_vnd: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        adults: int = 1,
        top_k: int = 5,
    ) -> str:
        """Recommend Vietnam destinations using semantic search + reasoning."""
        result = await agent.recommend(
            interests=interests,
            travel_style=travel_style,
            budget_vnd=budget_vnd,
            start_date=start_date,
            end_date=end_date,
            adults=adults,
            top_k=top_k,
        )
        return json.dumps(result, ensure_ascii=False)
```

### 14.7 Agent mới #3 — Itinerary Planning

Mục đích: nhận `CustomerPreferences` + danh sách điểm đến đã chọn, sinh lịch trình ngày-theo-ngày, có gắn weather + transport gợi ý.

```python
# Backend/app/v1/services/agent_services/itinerary_agent.py

from datetime import date, timedelta
from pydantic import BaseModel
from langchain_openai import ChatOpenAI


class ItineraryDay(BaseModel):
    day_index: int
    date: str
    theme: str
    morning: str
    afternoon: str
    evening: str
    estimated_cost_vnd: int
    notes: str | None = None


class Itinerary(BaseModel):
    destination: str
    start_date: str
    end_date: str
    total_estimated_cost_vnd: int
    days: list[ItineraryDay]


class ItineraryAgent:
    """Plan day-by-day itinerary from preferences."""

    def __init__(self, llm: ChatOpenAI) -> None:
        self.llm = llm.with_structured_output(Itinerary)

    async def build(
        self,
        destination: str,
        start_date: str,
        end_date: str,
        interests: list[str],
        budget_vnd: int,
        adults: int,
        weather_summary: str | None = None,
    ) -> Itinerary:
        num_days = (
            date.fromisoformat(end_date) - date.fromisoformat(start_date)
        ).days + 1
        prompt = (
            "Plan a {n} day itinerary in {dest} for {adults} adult(s), "
            "budget about {budget:,} VND, interests: {interests}. "
            "Weather context: {weather}. Output strict JSON per schema."
        ).format(
            n=num_days,
            dest=destination,
            adults=adults,
            budget=budget_vnd,
            interests=", ".join(interests) or "general",
            weather=weather_summary or "unknown",
        )
        return await self.llm.ainvoke(prompt)
```

```python
# Backend/app/v1/mcp/src/tools/itinerary_tools.py

import json

from fastmcp import FastMCP

from app.v1.services.agent_services.itinerary_agent import ItineraryAgent


def register_itinerary_tools(mcp: FastMCP) -> None:
    agent = ItineraryAgent(llm=...)

    @mcp.tool()
    async def build_itinerary(
        destination: str,
        start_date: str,
        end_date: str,
        interests: list[str],
        budget_vnd: int,
        adults: int = 1,
    ) -> str:
        """Build a day-by-day itinerary as JSON."""
        plan = await agent.build(
            destination, start_date, end_date,
            interests, budget_vnd, adults,
        )
        return plan.model_dump_json()
```

### 14.8 Echo Ping — MCP server mẫu

`echo` là health-check protocol-level cho hệ MCP, độc lập với business logic. Hữu ích khi debug client.

```python
# Backend/app/v1/mcp/src/tools/echo_tools.py

from datetime import datetime, timezone

from fastmcp import FastMCP


def register_echo_tools(mcp: FastMCP) -> None:

    @mcp.tool()
    async def ping() -> str:
        """Return current server time, useful as MCP liveness probe."""
        return datetime.now(timezone.utc).isoformat()

    @mcp.tool()
    async def echo(message: str) -> str:
        """Return the message back. Used to verify transport round-trip."""
        return message
```

### 14.9 Sửa Supervisor — orchestrator thuần

`SupervisorGraph` hiện tự gọi LLM để trả lời. Sau khi có Customer Query Agent, đổi vai trò:

- Node `understand`: NLU (Customer Query Agent), set `route`.
- Node `chat_tools`: chỉ chạy khi route yêu cầu booking / search trực tiếp.
- Node `recommend_destination`, `plan_itinerary`: gọi tool MCP tương ứng.
- Node `reply`: chốt câu trả lời cuối cùng cho user (LLM nhỏ, prompt ngắn).

Điều này khớp với mẫu Azure: orchestrator tách bạch khâu routing và khâu trả lời, mỗi specialist agent trả về data thuần (JSON / model), không trả lời tự nhiên ngữ.

### 14.10 Cập nhật `agent.yaml`

```yaml
# Backend/agent.yaml -> tool_calling.available_tools (them)
tool_calling:
  available_tools:
    # Booking, payment, OTP - khong doi
    ...
    # New: destination recommendation
    recommend_destinations:
      description: Suggest Vietnam destinations from preferences
    # New: itinerary planning
    build_itinerary:
      description: Build day-by-day itinerary as JSON
    # New: debug
    ping:
      description: Health check MCP transport
    echo:
      description: Round-trip echo for debugging
```

### 14.11 OpenTelemetry — bản tương đương Aspire Dashboard

Azure sample dùng Aspire Dashboard để xem trace. Trên stack Python tự host:

- Cài: `opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-httpx`, `opentelemetry-exporter-otlp`.
- Chạy local OTLP collector + Grafana Tempo / Jaeger.
- Trong `main.py`:

```python
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

FastAPIInstrumentor.instrument_app(app)
HTTPXClientInstrumentor().instrument()
```

- LangGraph: bật `LANGSMITH_TRACING=true` + `LANGSMITH_API_KEY` để xem trace từng node của Supervisor (đã tích hợp sẵn ở LangChain ecosystem, free tier đủ dùng).

### 14.12 Frontend toggle — Multi-Agent Mode

Thêm cờ `multiAgent` cho `ai-chatbot` để A/B classic vs new pipeline:

```typescript
// Frontend/src/app/components/ai-chatbot/ai-chatbot.component.ts (snippet)

export interface ChatStreamRequest {
  message: string;
  roomId?: string;
  mode?: 'classic' | 'multi_agent';
}

sendMessage(text: string): void {
  this.chatService
    .stream({ message: text, roomId: this.roomId, mode: this.multiAgentMode ? 'multi_agent' : 'classic' })
    .subscribe(/* ... */);
}
```

Backend `chat.py` endpoint nhận thêm field `mode` và route vào `SupervisorGraph` cũ hoặc graph mới (Section 14.5).

### 14.13 Roadmap triển khai

| Bước | Phạm vi | Thời gian ước tính |
|---|---|---|
| 1 | Echo MCP + tách sub-server theo domain (`14.4`, `14.8`) | 0.5 ngày |
| 2 | `CustomerQueryAgent` + node `understand` (`14.5`) | 1 ngày |
| 3 | Expose `recommend_destinations` tool (`14.6`) | 0.5 ngày |
| 4 | `ItineraryAgent` + tool (`14.7`) | 1.5 ngày |
| 5 | Sửa SupervisorGraph thành router (`14.9`) + toggle FE (`14.12`) | 1 ngày |
| 6 | OpenTelemetry + LangSmith tracing (`14.11`) | 0.5 ngày |
| 7 | Test E2E + tài liệu hoá | 1 ngày |

Tổng cộng khoảng 6 ngày công cho 1 dev, không bao gồm refactor lớn ở các module khác.

### 14.14 Những điểm khác biệt so với Azure sample (chủ động bỏ)

| Điểm trong sample | Lý do không port nguyên bản |
|---|---|
| Đa-language MCP servers (Node/Java/.NET) | Stack KLTN là Python-only, FastMCP đã đủ; có thể thêm sub-server ngôn ngữ khác sau khi production hoá |
| Microsoft Agent Framework / LlamaIndex.TS | Đã có LangGraph, giữ thống nhất một orchestrator giảm chi phí học |
| Azure Container Apps deploy (`azd up`) | Project deploy Modal + Docker, không phụ thuộc Azure |
| Aspire Dashboard | Thay bằng LangSmith + OTLP collector tự host |
| Phi4 14B local | Đã dùng `gpt-5-mini` qua OpenAI/Modal; có thể giữ option Modal local model |

---
