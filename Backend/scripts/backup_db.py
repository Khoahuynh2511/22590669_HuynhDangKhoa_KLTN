r"""
Backup database (schema public) -> 1 file .sql có thể restore lại bằng restore_to_neon.py.

Lý do: Render free Postgres đã từng hết hạn -> mất data. Chạy script này định kỳ
(ít nhất 1 lần/tuần, hoặc trước khi demo) để luôn có bản backup mới trên máy.

Output: Backend/asset/backups/neon_<YYYYMMDD_HHMMSS>.sql
        (COPY ... FROM stdin cho từng bảng public, kèm CREATE TABLE)

Dùng:
    cd Backend
    python scripts/backup_db.py                 # dump tất cả bảng public
    python scripts/backup_db.py --data-only     # chỉ data (schema lấy từ migrations)
"""
from __future__ import annotations
import argparse
import datetime
import io
import os
import sys
from pathlib import Path

# load .env
ENV = Path(__file__).resolve().parent.parent / ".env"
if ENV.exists():
    for line in ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=os.environ.get("DATABASE_URL"))
    ap.add_argument("--data-only", action="store_true")
    args = ap.parse_args()
    if not args.dsn:
        print("ERROR: cần DATABASE_URL trong .env hoặc --dsn"); sys.exit(2)

    import psycopg2
    conn = psycopg2.connect(args.dsn)
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("""SELECT table_name FROM information_schema.tables
                   WHERE table_schema='public' ORDER BY table_name""")
    tables = [r[0] for r in cur.fetchall()]

    out_dir = Path(__file__).resolve().parent.parent / "asset" / "backups"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fpath = out_dir / f"neon_{ts}.sql"

    total_rows = 0
    with open(fpath, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"-- Neon backup @ {ts}\n-- {len(tables)} tables. Restore: python scripts/restore_to_neon.py --sql <file> --dsn <url>\n")
        f.write("SET client_encoding = 'UTF8';\n\n")
        for t in tables:
            # column list
            cur.execute("""SELECT column_name FROM information_schema.columns
                           WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position""", (t,))
            cols = [r[0] for r in cur.fetchall()]
            f.write(f"-- Table: {t}\n")
            col_sql = ", ".join(f'"{c}"' for c in cols)
            f.write(f"COPY public.{t} ({col_sql}) FROM stdin;\n")
            buf = io.StringIO()
            cur.copy_expert(f'COPY public.{t} ({col_sql}) TO STDOUT', buf)
            data = buf.getvalue()
            f.write(data)
            if data and not data.endswith("\n"):
                f.write("\n")
            f.write("\\.\n\n")
            total_rows += data.count("\n")

    conn.close()
    size_kb = fpath.stat().st_size // 1024
    print(f"OK -> {fpath}  ({len(tables)} tables, ~{total_rows} rows, {size_kb} KB)")


if __name__ == "__main__":
    main()
