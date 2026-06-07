import psycopg2
import re

# Connect to Render
conn = psycopg2.connect(
    host='dpg-d8ban0n7f7vs73btkn5g-a.singapore-postgres.render.com',
    database='db_23520123',
    user='db_23520123_user',
    password='jAFPayJuom27rWsASpAqBhIInQL6UQ21'
)
conn.autocommit = False
cur = conn.cursor()

# Get column info for each table
def get_table_columns(table_name):
    cur.execute('''
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
    ''', (table_name,))
    return [r[0] for r in cur.fetchall()]

# Read backup
with open('db_cluster-27-01-2026@16-01-29.backup', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

lines = content.split('\n')

# Tables to import in FK order
target_tables = ['users', 'roles', 'tour_packages', 'bookings', 'booking_cancellations',
                 'otp_verifications', 'payments', 'promotions', 'reviews',
                 'chat_rooms', 'chat_history', 'notifications', 'favorite_tours',
                 'admin_settings', 'travel_news_urls']

results = {}

for target_table in target_tables:
    # Get columns in Render DB
    render_cols = get_table_columns(target_table)
    if not render_cols:
        print(f'{target_table}: table not found in Render')
        continue

    # Find COPY block in backup
    in_copy = False
    backup_cols = []
    data_rows = []

    for line in lines:
        if line.startswith(f'COPY public.{target_table} '):
            # Parse column names from COPY statement
            match = re.search(r'\(([^)]+)\)', line)
            if match:
                backup_cols = [c.strip() for c in match.group(1).split(',')]
            in_copy = True
            continue

        if in_copy:
            if line == r'\.':
                in_copy = False
                break
            data_rows.append(line)

    if not backup_cols or not data_rows:
        print(f'{target_table}: no data in backup')
        results[target_table] = 0
        continue

    # Find common columns
    common_cols = [c for c in backup_cols if c in render_cols]
    if not common_cols:
        print(f'{target_table}: no common columns')
        continue

    # Get indices of common columns in backup
    col_indices = [backup_cols.index(c) for c in common_cols]

    # Insert data
    inserted = 0
    errors = 0
    for row in data_rows:
        if not row.strip():
            continue
        values = row.split('\t')
        if len(values) < len(backup_cols):
            continue

        # Extract only common columns
        try:
            selected_values = []
            for idx in col_indices:
                v = values[idx] if idx < len(values) else r'\N'
                if v == r'\N':
                    selected_values.append(None)
                else:
                    selected_values.append(v)

            placeholders = ','.join(['%s'] * len(common_cols))
            col_names = ','.join(common_cols)
            sql = f'INSERT INTO {target_table} ({col_names}) VALUES ({placeholders}) ON CONFLICT DO NOTHING'
            cur.execute(sql, selected_values)
            inserted += 1
        except Exception as e:
            errors += 1
            if errors <= 2:
                print(f'{target_table} error: {e}')

    conn.commit()
    results[target_table] = inserted
    print(f'{target_table}: {inserted} rows inserted ({errors} errors)')

conn.close()
print('\nDone!')
