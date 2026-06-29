#!/usr/bin/env bash
# =============================================================================
# dev.sh - Khởi động nhanh Redis + Backend + Frontend (Windows / Git Bash)
# Cách dùng:
#   ./dev.sh           -> start tất cả (Redis + Backend + Frontend)
#   ./dev.sh all       -> same as above
#   ./dev.sh redis     -> chỉ Redis
#   ./dev.sh be        -> chỉ Backend
#   ./dev.sh fe        -> chỉ Frontend
#   ./dev.sh stop      -> dừng Redis + Backend + Frontend
# =============================================================================
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REDIS_DIR="$ROOT/tools/redis"
BACKEND_DIR="$ROOT/Backend"
FRONTEND_DIR="$ROOT/Frontend"
REDIS_PORT=6379
BE_PORT=8000
FE_PORT=4200

# màu
G="\033[1;32m"; Y="\033[1;33m"; R="\033[1;31m"; C="\033[1;36m"; N="\033[0m"
say(){ echo -e "${G}[dev]${N} $*"; }
warn(){ echo -e "${Y}[dev]${N} $*"; }
err(){ echo -e "${R}[dev]${N} $*"; }

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

# Trả về 0 nếu port đang mở (có service lắng nghe)
port_open() {
  python - "$1" <<'PY' 2>/dev/null
import socket, sys
s = socket.socket(); s.settimeout(0.4)
try:
    s.connect(("127.0.0.1", int(sys.argv[1]))); sys.exit(0)
except Exception:
    sys.exit(1)
PY
}

# Tìm redis-server.exe (tools/redis hoặc PATH)
find_redis() {
  if [ -x "$REDIS_DIR/redis-server.exe" ]; then echo "$REDIS_DIR/redis-server.exe"
  elif command -v redis-server >/dev/null 2>&1; then command -v redis-server
  else echo ""; fi
}

# Start Redis nếu chưa chạy. Quan trọng: phải sẵn sàng TRƯỚC Backend,
# vì OTPService cache redis_client lúc khởi tạo (fail lần đầu -> None luôn).
start_redis() {
  local exe; exe="$(find_redis)"
  if [ -z "$exe" ]; then
    err "Không tìm thấy redis-server. Đặt binary tại $REDIS_DIR hoặc cài Redis."
    return 1
  fi
  if port_open "$REDIS_PORT"; then
    say "Redis đang chạy ở :$REDIS_PORT (bỏ qua start)."
    return 0
  fi
  say "Khởi động Redis ($(basename "$exe")) ..."
  # Detached process (không đụng terminal hiện tại)
  python - "$exe" <<'PY' 2>/dev/null
import subprocess, sys
subprocess.Popen([sys.argv[1], "--port", "6379", "--bind", "127.0.0.1"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    creationflags=0x00000008)  # DETACHED_PROCESS
PY
  # Đợi Redis sẵn sàng (tối đa ~10s)
  for _ in $(seq 1 20); do
    port_open "$REDIS_PORT" && { say "Redis UP tại :$REDIS_PORT"; return 0; }
    sleep 0.5
  done
  err "Redis không lên được ở :$REDIS_PORT."
  return 1
}

# Mở 1 cửa sổ mới (mintty nếu có, ngược lại chạy nền terminal hiện tại)
run_in_window() {
  local title="$1"; shift
  if command -v mintty >/dev/null 2>&1; then
    mintty -t "$title" -h always -e bash -lc "$*; echo; echo '(cửa sổ sẽ giữ lại - đóng để dừng)'; read -r _" &
  else
    warn "mintty không có -> chạy '$title' trong nền (log trộn chung terminal này)."
    ( eval "$*" ) &
  fi
}

start_backend() {
  if port_open "$BE_PORT"; then warn "Port :$BE_PORT đang bận (Backend đã chạy?)."; return 0; fi
  if [ ! -f "$BACKEND_DIR/.env" ]; then
    warn "Backend/.env chưa có -> copy từ .env.example. Nhớ điền SMTP/DB trước khi chạy."
    [ -f "$BACKEND_DIR/.env.example" ] && cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
  fi
  say "Khởi động Backend (uv sync + uvicorn :$BE_PORT) ..."
  run_in_window "Backend" "cd '$BACKEND_DIR' && uv sync && uv run uvicorn main:app --reload --host 0.0.0.0 --port $BE_PORT"
}

start_frontend() {
  if port_open "$FE_PORT"; then warn "Port :$FE_PORT đang bận (Frontend đã chạy?)."; return 0; fi
  say "Khởi động Frontend (npm install nếu thiếu + ng serve :$FE_PORT) ..."
  run_in_window "Frontend" "cd '$FRONTEND_DIR' && { [ -d node_modules ] || npm install; } && ng serve --port $FE_PORT"
}

# Kill mọi process đang lắng nghe trên 1 port (Windows: netstat + taskkill)
kill_port() {
  local port="$1" pid
  pid="$(netstat -ano 2>/dev/null | grep -E "LISTENING" | grep ":${port}\s" | awk '{print $5}' | sort -u | head -1)"
  if [ -n "$pid" ]; then
    taskkill //F //PID "$pid" >/dev/null 2>&1 && say "Đã dừng process trên :$port (PID $pid)."
  else
    warn "Không có process nào trên :$port."
  fi
}

stop_all() {
  say "Dừng tất cả ..."
  kill_port "$FE_PORT"
  kill_port "$BE_PORT"
  kill_port "$REDIS_PORT"
}

banner() {
  echo -e "${C}============================================================${N}"
  echo -e "${C}  AI Tour Booking - Dev Launcher${N}"
  echo -e "${C}============================================================${N}"
}

urls() {
  echo
  say "Frontend : http://localhost:$FE_PORT"
  say "Backend  : http://localhost:$BE_PORT  (docs: /docs)"
  say "Redis    : 127.0.0.1:$REDIS_PORT"
  echo
}

# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
cmd="${1:-all}"
banner
case "$cmd" in
  redis) start_redis ;;
  be)    start_backend ;;
  fe)    start_frontend ;;
  all)
    start_redis || { err "Redis fail -> dừng (cần Redis để OTP hoạt động)."; exit 1; }
    sleep 1
    start_backend
    sleep 1
    start_frontend
    urls
    ;;
  stop)  stop_all; exit 0 ;;
  *) err "Lệnh không hợp lệ: $cmd"; echo "Dùng: $0 [all|redis|be|fe|stop]"; exit 1 ;;
esac
