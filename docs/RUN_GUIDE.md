# Hướng Dẫn Chạy Code - AI Tour Booking System

> **KLTN 22590669 - Huỳnh Đăng Khoa**

---

## 1. Yêu Cầu Hệ Thống

| Công cụ | Phiên bản | Ghi chú |
|---------|-----------|---------|
| **Python** | >= 3.10 | Khuyên dùng 3.11+ |
| **Node.js** | >= 18 | Khuyên dùng LTS |
| **uv** | Mới nhất | Package manager cho Python |
| **Angular CLI** | 19.x | `npm i -g @angular/cli@19` |
| **Git** | Mới nhất | |
| **Docker** (tuỳ chọn) | Mới nhất | Chạy full-stack bằng Docker |

---

## 2. Cấu Hình Backend

### 2.1. File `.env`

```bash
cd Backend
cp .env.example .env
```

Chỉnh sửa `Backend/.env` với các key thật. Các biến quan trọng:

```bash
# === Bắt buộc ===
OPENAI_API_KEY=sk-...                    # OpenAI API key (LLM + Embeddings)
SUPABASE_URL=https://xxx.supabase.co     # Supabase project URL
SUPABASE_KEY=eyJ...                      # Supabase anon key
DATABASE_URL=postgresql://user:pass@dpg-xxxxx.region-postgres.render.com/dbname  # Render PostgreSQL (primary)
JWT_SECRET=your-random-secret            # JWT signing secret

# === AI / Agent ===
MEM0_API_KEY=m0-...                      # Mem0 long-term memory
PERPLEXITY_API_KEY=pplx-...              # Perplexity news search (hoặc TAVILY_API_KEY)
SEARCH_PROVIDER=tavily                   # "tavily" hoặc "perplexity"

# === External Services ===
SENDGRID_API_KEY=SG.xxx                  # Email OTP
CLOUDINARY_CLOUD_NAME=xxx                # Image upload
VNPAY_TMN_CODE=xxx                       # VNPay sandbox
VNPAY_HASH_SECRET=xxx                    # VNPay sandbox
GOOGLE_CLIENT_ID=xxx                     # Google OAuth
GOOGLE_CLIENT_SECRET=xxx                 # Google OAuth

# === LangSmith (tuỳ chọn - tracing) ===
LANGCHAIN_TRACING=true
LANGCHAIN_API_KEY=lsv2_sk-...
LANGSMITH_PROJECT="UITravel"

# === CORS & Frontend ===
CORS_ORIGINS=http://localhost:4200,http://127.0.0.1:4200
FRONTEND_BASE_URL=http://localhost:4200/home
```

### 2.2. Database (Render PostgreSQL)

> **Database chính của dự án là Render PostgreSQL**, không phải Supabase.

1. Tạo PostgreSQL trên [Render Dashboard](https://dashboard.render.com) → New → PostgreSQL
2. Copy **External Database URL** vào `Backend/.env`:
   ```bash
   DATABASE_URL=postgresql://user:pass@dpg-xxxxx.region-postgres.render.com/dbname
   ```
3. Chạy SQL migrations theo thứ tự trong `Backend/migrations/` (bắt đầu `init_schema.sql`)
4. Import seed data (tuỳ chọn):
   ```bash
   python import_data.py
   ```

**Supabase** (nếu còn dùng): chỉ cho vector search tour / embeddings — cấu hình `SUPABASE_URL` + `SUPABASE_KEY` riêng, không thay `DATABASE_URL`.

**Lưu ý Render free tier:** DB có thể sleep sau idle — lần query đầu có thể chậm vài giây.

### 2.3. SSL Fix trên Windows

> **Quan trọng:** Trên Windows, Python/httpx có thể lỗi SSL certificate.
> Đã fix bằng cách thêm `pip-system-certs` vào dependencies.

Nếu gặp lỗi `SSL: CERTIFICATE_VERIFY_FAILED`:

```bash
cd Backend
uv add pip-system-certs --native-tls
```

---

## 3. Chạy Backend

### Cách 1: Dùng script (khuyên dùng)

**Linux/macOS:**
```bash
cd Backend
chmod +x run.sh
./run.sh
```

**Windows (PowerShell):**
```powershell
cd Backend
.\run.ps1
```

### Cách 2: Chạy thủ công

```bash
cd Backend

# Cài dependencies
uv sync

# Chạy dev server
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Cách 3: Docker

```bash
cd Backend
docker-compose up -d
```

### Xác minh Backend

```bash
curl http://localhost:8000/health
# Kết quả: {"status":"healthy"}
```

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **API prefix:** `/api/v1/`

---

## 4. Cấu Hình Frontend

### 4.1. Environment

File `Frontend/src/environments/environment.ts`:

```typescript
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api/v1'
};
```

---

## 5. Chạy Frontend

```bash
cd Frontend

# Cài dependencies
npm install

# Chạy dev server (mặc định port 4200)
ng serve

# Hoặc chỉ định port
ng serve --port 4200
```

### Xác minh Frontend

Mở trình duyệt: http://localhost:4200

---

## 6. Chạy Full-Stack Bằng Docker

```bash
cd Frontend
docker-compose up -d --build
```

Services:
- **Frontend (nginx):** http://localhost (port 80)
- **Backend:** http://localhost/api (proxied qua nginx)
- **Redis:** internal port 6379

---

## 7. Cấu Trúc API Endpoints Chính

| Endpoint | Method | Mô tả |
|----------|--------|--------|
| `/health` | GET | Health check |
| `/api/v1/auth/*` | POST | Đăng nhập, đăng ký, OTP |
| `/api/v1/tours/*` | GET/POST | Quản lý tour |
| `/api/v1/bookings/*` | GET/POST | Đặt tour |
| `/api/v1/payments/*` | POST | Thanh toán VNPay |
| `/api/v1/chat/stream` | POST (SSE) | AI Chat streaming |
| `/mcp/mcp` | POST | MCP server endpoint |

---

## 8. Troubleshooting

### Lỗi SSL trên Windows
```
httpx.ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED]
```
**Fix:** Đảm bảo `pip-system-certs` đã được cài:
```bash
cd Backend && uv add pip-system-certs --native-tls
```

### Lỗi kết nối Database
```
ConnectionRefusedError: cannot connect to PostgreSQL
```
**Fix:** Kiểm tra `DATABASE_URL` trỏ đúng Render External Database URL. Thêm `?sslmode=require` nếu lỗi SSL.

### Frontend không gọi được API
**Fix:** Kiểm tra `CORS_ORIGINS` trong Backend `.env` có chứa URL Frontend không.
```
CORS_ORIGINS=http://localhost:4200,http://127.0.0.1:4200
```

### uv not found
```bash
# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex

# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Angular CLI not found
```bash
npm install -g @angular/cli@19
```

---

## 9. Deploy

### CI/CD (GitHub Actions)

Push lên branch `main` → tự động deploy Frontend lên AWS Lightsail.

Cấu hình GitHub Secrets:
- `HOST`: IP server AWS
- `USERNAME`: SSH username
- `SSH_KEY`: SSH private key

### Backend Deploy (Modal - serverless)
```bash
cd Backend
./modal_deploy.sh
```

### Manual Deploy trên server
```bash
cd ~/doan
git pull origin main
docker compose down
docker compose up -d --build
```
