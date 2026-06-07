# PROJECT_SUMMARY.md - AI Tour Booking System (KLTN - 22590669 Huynh Dang Khoa)

## Tong Quan Du An

**De tai:** He thong Dat Tour Du Lich Thong Minh voi AI Agent  
**Sinh vien:** Huynh Dang Khoa - MSSV: 22590669  
**Loai:** Khoa Luan Tot Nghiep (KLTN)  
**Repo name:** 
---
## Kien Truc Tong The

### Backend (FastAPI + LangGraph)
- **Framework:** FastAPI 0.112+, Python 3.10+
- **AI/Agent:** LangGraph (SupervisorGraph), LangChain, FastMCP
- **LLM:** OpenAI GPT-5-mini, text-embedding-3-small
- **Database:** Supabase (PostgreSQL + pgvector)
- **Cache:** Redis
- **Memory:** Mem0 + FalkorDB (Graphiti) - long-term AI memory
- **Package Manager:** uv
- **Deploy:** Modal (serverless), Docker

### Frontend (Angular 19)
- **Framework:** Angular 19
- **UI Library:** PrimeNG 19
- **CSS:** TailwindCSS 3.4
- **Other:** Three.js (chua dung nhieu), ngx-owl-carousel-o
- **Deploy:** AWS Lightsail via Docker + GitHub Actions CI/CD

---

## Cac Tinh Nang Chinh

### 1. Authentication & Authorization
- Dang nhap/Dang ky bang Email (JWT)
- OAuth 2.0 voi Google
- Phan quyen Admin/User
- Xac thuc OTP qua Email (SendGrid)

### 2. Quan Ly Tour & Booking
- CRUD Tour Packages voi quan ly slots
- Dat tour voi xac thuc OTP
- Ap dung Promotion/Voucher
- Thanh toan VNPay
- Quan ly trang thai booking

### 3. AI-Powered Features (Trong Tam KLTN)
- **LangGraph Multi-Agent System:**
  - SupervisorGraph: Agent chinh cho user chat (ReAct pattern)
  - AdminGraph: Agent ho tro admin (SQL query)
  - NewsSearchAgent: Cap nhat tin tuc du lich (Perplexity)
- **MCP Tools:** Modular tool system (FastMCP)
  - booking_tools, tour_search_tools, flight_tools, weather_tools
- **Semantic Search:** Tim kiem tour bang vector embeddings (pgvector)
- **Long-term Memory:** Mem0 + FalkorDB/Graphiti

### 4. Trip Planning (Static Workflow) - Dang phat trien
- Plan Mode: Luong len ke hoach du lich step-by-step
- 6 buoc: Destination -> Budget -> Preferences -> Generate Plan -> Transportation -> Checkout
- Thiet ke nhu State Machine (khong de AI tu do, predictable)

### 5. Analytics & Reports
- Dashboard thong ke doanh thu
- Bao cao booking theo thoi gian
- Quan ly reviews & ratings

---

## Cau Truc Thu Muc

```
22590669_KLTN_HuynhDangKhoa/
|-- Backend/
|   |-- main.py                  # FastAPI entry point
|   |-- pyproject.toml           # Dependencies (uv)
|   |-- agent.yaml               # Customer AI agent config
|   |-- admin_agent.yaml         # Admin AI agent config
|   |-- docker-compose.yml
|   |-- Dockerfile
|   |-- modal_app.py             # Modal serverless deploy
|   |-- app/v1/
|   |   |-- api/endpoints/       # REST API handlers
|   |   |-- core/                # Config, logging
|   |   |-- schema/              # Pydantic models
|   |   |-- model/               # DB models
|   |   |-- services/            # Business logic
|   |   |   |-- agent_services/  # LangGraph agents
|   |   |   |   |-- agents/
|   |   |   |   |-- graphs/supervisor_graph.py
|   |   |   |   |-- nodes/
|   |   |   |   |-- tools/mcp_tools.py
|   |   |   |   |-- memory/
|   |   |   |   |-- prompts/
|   |   |   |   +-- skills/
|   |   |   |-- agent_support_admin/
|   |   |   |-- search_new_agent/
|   |   |   +-- (auth, booking, payment, tour, vnpay, otp...)
|   |   +-- mcp/src/tools/       # FastMCP tool definitions
|   |-- migrations/              # Alembic DB migrations
|   |-- tests/
|   +-- docs/
|
|-- Frontend/
|   |-- src/app/
|   |   |-- pages/               # Route pages
|   |   |   |-- admin/
|   |   |   |-- home/
|   |   |   |-- tours/
|   |   |   |-- booking-pages/
|   |   |   |-- payment/
|   |   |   |-- my-bookings/
|   |   |   |-- my-payments/
|   |   |   |-- reviews/
|   |   |   |-- promotions/
|   |   |   |-- travel-news/
|   |   |   |-- hotel/
|   |   |   +-- profile/
|   |   |-- services/            # Angular services (API calls)
|   |   |-- components/          # Shared components
|   |   |-- guards/
|   |   |-- layouts/
|   |   +-- directives/
|   |-- angular.json
|   |-- tailwind.config.js
|   +-- docker-compose.yml + Dockerfile + nginx.conf
|
|-- docs/
|   |-- AGENT_FEATURES_DEVELOPMENT_GUIDE.md
|   +-- TRIP_PLANNING_STATIC_WORKFLOW.md
|
|-- .github/workflows/deploy.yml  # CI/CD: Frontend -> AWS Lightsail
+-- db_data_only.sql              # DB backup/seed
```

---

## Dich Vu Ben Ngoai (External Services)

| Service | Muc dich |
|---------|----------|
| Supabase | Database (PostgreSQL + pgvector + Auth) |
| OpenAI | LLM (GPT-5-mini) + Embeddings |
| Redis | Cache |
| Mem0 | Long-term AI memory |
| FalkorDB | Graph DB cho Graphiti (memory graph) |
| VNPay | Payment gateway |
| SendGrid | Email (OTP, notifications) |
| Cloudinary | Media/Image CDN |
| Perplexity AI | News search agent |
| Google OAuth | Social login |

---

## Deploy

- **Frontend:** AWS Lightsail, Docker container, auto-deploy on push to `main`
- **Backend:** Modal (serverless Python), co the chay Docker local
- **CI/CD:** GitHub Actions (`.github/workflows/deploy.yml`)

---

## Ke Hoach Phat Trien (Tu docs/)

### Dang lam / Se lam:
1. **Trip Planning Static Workflow** - Plan Mode step-by-step
2. **Flight Agent** - Tim kiem ve may bay
3. **Hotel Agent** - Tim kiem khach san
4. **Transport Agent** - Ve xe
5. **Modular Tour Builder** - Drag & Drop tao tour
6. **Internal Catalog System** - Tu quan ly data (khong phu thuoc external API)
7. **Azure AI Travel Agents Pattern** - Multi-agent architecture

---

## Lenh Chay Nhanh

```bash
# Backend
cd Backend
uv sync
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd Frontend
npm install
ng serve  # http://localhost:4200

# Docker
docker-compose up -d
```

---

## Ghi Chu Cho AI Assistant

- Backend dung `uv` (khong dung pip truc tiep)
- Frontend la Angular 19 + PrimeNG 19 + TailwindCSS
- Agent system nam trong `Backend/app/v1/services/agent_services/`
- MCP tools nam trong `Backend/app/v1/mcp/src/tools/`
- Supervisor graph la entry point chinh cho AI chat
- File `.env` chua tat ca secrets (khong commit)
- Response format chuan: `{ "EC": 0, "EM": "Success", "data": {...} }`
- API prefix: `/api/v1/`
- SSE streaming cho AI chat: `/api/v1/chat/stream`
