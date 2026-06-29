r"""
Restore PostgreSQL backup -> Neon (hoặc Postgres sạch) — CHỈ schema public.

Nguồn: asset/db_public_only.sql (Supabase cluster dump: gồm public + extensions + storage +
system roles). App chỉ dùng schema public (17 bảng + functions + data).

Chiến lược:
  - Parser mức ký tự, theo dõi single-quote / dollar-quote $$ / comment -> tách statement đúng
    kể cả body CREATE FUNCTION có dấu ';'.
  - Nhận diện schema mỗi object qua comment header của pg_dump
    (-- Name: ..; Type: ..; Schema: <x>;). CHỈ giữ Schema: public.
  - autocommit: mỗi statement là 1 transaction độc lập -> 1 lỗi không hạ cả loạt.
  - tạo sẵn CREATE EXTENSION vector (cột embedding vector(1536)).
  - COPY ... FROM stdin chạy qua cursor.copy().

Dùng:
  python scripts/restore_to_neon.py --dry-run
  python scripts/restore_to_neon.py --dsn "postgresql://...?sslmode=require"
"""
from __future__ import annotations
import argparse
import io
import os
import re
import sys
from collections import Counter

_OWNER_RE = re.compile(r"\s+OWNER TO\s+[A-Za-z_][A-Za-z0-9_]*", re.IGNORECASE)
_DOLLAR_RE = re.compile(r"\$[A-Za-z_0-9]*\$")
# pg_dump header: -- Name: X; Type: Y; Schema: Z;   (hoặc -- Data for Name: X; Type: TABLE DATA; Schema: Z;)
_HEADER_SCHEMA_RE = re.compile(
    r"--\s*(?:Data for )?Name:\s*[^;]+;\s*Type:\s*[^;]+;\s*Schema:\s*([A-Za-z0-9_-]+)\s*;"
)
_SKIP_PREFIXES = (
    "CREATE ROLE", "ALTER ROLE", "CREATE POLICY", "DROP POLICY",
    "GRANT", "REVOKE",
)
# fragment rò rỉ từ các schema Supabase (do dollar-quote lồng làm split lệch)
_NONPUBLIC_SCHEMA_REF = re.compile(
    r"\b(storage|realtime|pgbouncer|graphql|extensions|supabase_functions|audit|pgsodium|net|http|vault|integration|migrations)\.",
    re.IGNORECASE,
)


def _transform_stmt(stmt: str) -> str | None:
    s = stmt.strip()
    if not s or s.startswith("\\"):
        return None
    up = s.upper()
    if up.startswith(_SKIP_PREFIXES):
        return None
    if re.search(r"\bOWNER TO\b", s, re.IGNORECASE):
        return None  # lệnh đổi owner -> không cần trên Neon (user sở hữu hết)
    if _NONPUBLIC_SCHEMA_REF.search(s):
        return None  # fragment rò rỉ từ schema khác -> bỏ
    return s


def parse_sql(path: str):
    """Yield ('exec'|'copy', schema, ...). schema = schema của object (từ header pg_dump)."""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    n = len(text)
    i = 0
    stmt: list[str] = []
    last_schema: str | None = None
    out: list = []

    while i < n:
        c = text[i]

        # line comment -- ...  (đồng thời bắt schema từ header pg_dump)
        if c == "-" and i + 1 < n and text[i + 1] == "-":
            nl = text.find("\n", i)
            cline = text[i:nl] if nl != -1 else text[i:]
            m = _HEADER_SCHEMA_RE.search(cline)
            if m:
                last_schema = m.group(1)
            i = nl + 1 if nl != -1 else n
            continue
        # block comment /* ... */
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            end = text.find("*/", i + 2)
            i = end + 2 if end != -1 else n
            continue
        # dollar-quote $tag$ ... $tag$
        if c == "$":
            m = _DOLLAR_RE.match(text, i)
            if m:
                tag = m.group(0)
                close = text.find(tag, i + len(tag))
                if close == -1:
                    stmt.append(text[i:]); i = n; continue
                stmt.append(text[i:close + len(tag)])
                i = close + len(tag)
                continue
        # single-quote '...'
        if c == "'":
            stmt.append("'")
            j = i + 1
            while j < n:
                if text[j] == "'":
                    if j + 1 < n and text[j + 1] == "'":
                        stmt.append("''"); j += 2; continue
                    stmt.append("'"); j += 1; break
                stmt.append(text[j]); j += 1
            i = j
            continue
        # top-level ';'
        if c == ";":
            stmt.append(";")
            i += 1
            cleaned = _transform_stmt("".join(stmt))
            stmt = []
            if cleaned is None:
                continue
            if re.match(r"\s*COPY\b", cleaned, re.IGNORECASE) and "FROM STDIN" in cleaned.upper():
                # bỏ newline (hoặc \r\n) ngay sau ';' để data không bị dư dòng trống đầu
                if i + 1 < n and text[i] == "\r" and text[i + 1] == "\n":
                    i += 2
                elif i < n and text[i] == "\n":
                    i += 1
                data_lines: list[str] = []
                while i < n:
                    nl = text.find("\n", i)
                    line = text[i:nl] if nl != -1 else text[i:]
                    if line.strip() == "\\.":
                        i = nl + 1 if nl != -1 else n
                        break
                    data_lines.append(line)
                    i = nl + 1 if nl != -1 else n
                out.append(("copy", last_schema, cleaned, "\n".join(data_lines) + "\n"))
            else:
                out.append(("exec", last_schema, cleaned))
            continue
        stmt.append(c)
        i += 1

    if stmt:
        cleaned = _transform_stmt("".join(stmt))
        if cleaned:
            out.append(("exec", last_schema, cleaned))
    return out


def _exec_unit(cur, unit, errors, counters):
    kind = unit[0]
    if kind == "exec":
        counters["exec"] += 1
        try:
            cur.execute(unit[2])
        except Exception as e:
            counters["exec_err"] += 1
            errors.append((unit[2][:140].replace("\n", " "), str(e)[:160]))
    elif kind == "copy":
        counters["copy"] += 1
        copy_stmt, data_text = unit[2], unit[3]
        try:
            with cur.copy(copy_stmt) as cp:
                cp.write(data_text)
        except Exception:
            try:
                cur.copy_expert(copy_stmt, io.StringIO(data_text))
            except Exception as e2:
                counters["copy_err"] += 1
                errors.append((copy_stmt[:140], str(e2)[:160]))


def restore(dsn: str, sql_path: str, data_sql_path: str | None = None, verbose: bool = True):
    import psycopg2  # noqa

    pre = [
        'CREATE EXTENSION IF NOT EXISTS vector;',
        'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";',
        'CREATE EXTENSION IF NOT EXISTS pgcrypto;',
    ]

    conn = psycopg2.connect(dsn)
    conn.autocommit = True  # mỗi statement độc lập -> 1 lỗi không cascade
    errors: list[tuple[str, str]] = []
    counters: Counter = Counter()

    try:
        with conn.cursor() as cur:
            # Clean state để chạy lại idempotent (xoá partial từ lần trước)
            for drop in [
                "DROP SCHEMA IF EXISTS public CASCADE;",
                "DROP EXTENSION IF EXISTS vector CASCADE;",
                'DROP EXTENSION IF EXISTS "uuid-ossp" CASCADE;',
                "DROP EXTENSION IF EXISTS pgcrypto CASCADE;",
                "CREATE SCHEMA public;",
            ]:
                try:
                    cur.execute(drop)
                except Exception as e:
                    errors.append((drop, str(e)[:160]))
            for p in pre:
                try:
                    cur.execute(p)
                except Exception as e:
                    errors.append((p, str(e)[:160]))

            if verbose:
                print(f"[1/2] Parsing {sql_path} ...")
            units = parse_sql(sql_path)
            public = [u for u in units if u[1] == "public"]
            skipped = len(units) - len(public)
            if verbose:
                print(f"      total={len(units)}  public={len(public)}  skipped(non-public)={skipped}")
            for u in public:
                _exec_unit(cur, u, errors, counters)

            if data_sql_path:
                if verbose:
                    print(f"[+] Extra data: {data_sql_path} ...")
                for u in parse_sql(data_sql_path):
                    if u[1] == "public":
                        _exec_unit(cur, u, errors, counters)

            # --- Fixup: dump schema cũ thiếu cột PK mà COPY cần (2 bảng) ---
            copy_units = {u[2].split()[1]: u for u in units if u[0] == "copy" and u[1] == "public"}
            for tab, pk in [("booking_cancellations", "cancellation_id"),
                            ("notifications", "notification_id")]:
                if tab not in copy_units:
                    continue
                try:
                    cur.execute(f'ALTER TABLE public."{tab}" ADD COLUMN IF NOT EXISTS {pk} uuid')
                    cu = copy_units[tab]
                    cur.copy_expert(cu[2], io.StringIO(cu[3]))
                    if verbose:
                        print(f"      [fixup] {tab}: +{pk} & re-COPY OK")
                except Exception as e:
                    errors.append((f"fixup {tab}", str(e)[:160]))
                    if verbose:
                        print(f"      [fixup] {tab}: FAIL {str(e)[:80]}")

            if verbose:
                print("[2/2] Row counts (public):")
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' ORDER BY table_name;"
            )
            for (t,) in cur.fetchall():
                try:
                    cur.execute(f'SELECT COUNT(*) FROM public."{t}";')
                    print(f"      {t:32s} {cur.fetchone()[0]:>8}")
                except Exception as e:
                    print(f"      {t:32s} ERR {str(e)[:80]}")
    finally:
        conn.close()

    return counters, errors


def dry_run(sql_path: str, data_sql_path: str | None):
    print(f"=== DRY-RUN: {sql_path} ===")
    units = parse_sql(sql_path)
    from collections import Counter as C
    by_schema = C(u[1] for u in units)
    print("units by schema:", dict(by_schema))
    public = [u for u in units if u[1] == "public"]
    exec_n = sum(1 for u in public if u[0] == "exec")
    copy_n = sum(1 for u in public if u[0] == "copy")
    print(f"public: {len(public)} units (exec={exec_n}, copy={copy_n})")

    tables = []
    for u in public:
        if u[0] == "exec":
            m = re.match(r"CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(?:public\.)?\"?([A-Za-z_0-9]+)\"?",
                         u[2].lstrip(), re.IGNORECASE)
            if m:
                tables.append(m.group(1))
    print(f"CREATE TABLE public ({len(tables)}): {tables}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=os.environ.get("NEON_DATABASE_URL"))
    ap.add_argument("--sql", default="../../asset/db_public_only.sql")
    ap.add_argument("--data-sql", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    sql_path = args.sql
    if not os.path.isabs(sql_path):
        sql_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.sql)

    if args.dry_run:
        dry_run(sql_path, args.data_sql); return
    if not args.dsn:
        print("ERROR: cần --dsn hoặc NEON_DATABASE_URL"); sys.exit(2)

    counters, errors = restore(args.dsn, sql_path, args.data_sql)
    print("\n=== DONE ===  counters:", dict(counters))
    if errors:
        print(f"\n{len(errors)} lỗi:")
        for stmt, err in errors[:40]:
            print(f"  - [{err}] :: {stmt}")


if __name__ == "__main__":
    main()
