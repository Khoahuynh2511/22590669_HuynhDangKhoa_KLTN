import re

# ==== FIX 1: review_service.py - is_approved -> status ====
with open('app/v1/services/review_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# SQL column references
content = content.replace('r.is_approved', 'r.status')
content = content.replace('rating, comment, is_approved, created_at, updated_at', 'rating, comment, status, created_at, updated_at')

# Function signature params
content = content.replace('is_approved: Optional[bool] = None', 'status: Optional[str] = None')
content = content.replace('is_approved: bool = True', "status: str = 'approved'")

# Filter logic in get_all_reviews
content = content.replace('if is_approved is not None:', 'if status is not None:')
content = content.replace('query += " AND r.is_approved = %s"', 'query += " AND r.status = %s"')
content = content.replace('params.append(is_approved)', 'params.append(status)')

# Response formatting
content = content.replace('"is_approved": row[\'is_approved\']', '"status": row[\'status\']')
content = content.replace("'is_approved': row['is_approved']", "'status': row['status']")

# Insert default value
content = content.replace('False,  # is_approved', "'pending',  # status")

# Update logic
content = content.replace("'is_approved' in update_data", "'status' in update_data")
content = content.replace("update_data['is_approved'] = False", "update_data['status'] = 'pending'")

# Stats query
content = content.replace('WHERE package_id = %s AND is_approved = %s', 'WHERE package_id = %s AND status = %s')
content = content.replace('cur.execute(query, (package_id, True))', "cur.execute(query, (package_id, 'approved'))")

# Function call params
content = content.replace('is_approved=is_approved', 'status=status')
content = content.replace("is_approved=True", "status='approved'")

# Docstrings
content = content.replace('is_approved: Filter by approval status', 'status: Filter by review status')
content = content.replace('is_approved: Only get approved reviews', "status: Filter by status")
content = content.replace('is_approved: Whether the review is approved', "status: Review status (pending/approved/rejected)")

# Admin check on is_approved
content = content.replace("Only admin can update is_approved", "Only admin can update status")
content = content.replace("Only admins can change approval status", "Only admins can change review status")

with open('app/v1/services/review_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed review_service.py")


# ==== FIX 2: report_service.py - datetime handling ====
with open('app/v1/services/report_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the created_at parsing - handle both datetime objects and strings
old_line = "created_at = datetime.fromisoformat(booking['created_at'].replace('Z', '+00:00')).date()"
new_line = """raw_created = booking['created_at']
                if isinstance(raw_created, str):
                    created_at = datetime.fromisoformat(raw_created.replace('Z', '+00:00')).date()
                else:
                    created_at = raw_created.date() if hasattr(raw_created, 'date') else raw_created"""

content = content.replace(old_line, new_line)

with open('app/v1/services/report_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed report_service.py")


# ==== FIX 3: booking_management_service.py - cancellations query ====
with open('app/v1/services/booking_management_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the cancellations query to match the actual DB schema
old_query = '''                # Build query
                query = """
                    SELECT
                        cancellation_id,
                        booking_id,
                        user_id,
                        package_id,
                        number_of_people,
                        total_amount,
                        contact_name,
                        contact_phone,
                        contact_email,
                        special_requests,
                        previous_status,
                        booking_created_at,
                        reason,
                        cancelled_at,
                        cancelled_by,
                        created_at
                    FROM booking_cancellations
                    WHERE 1=1
                """'''

new_query = '''                # Build query - JOIN with bookings and tour_packages for full info
                query = """
                    SELECT
                        bc.cancellation_id,
                        bc.booking_id,
                        bc.reason,
                        bc.cancelled_by,
                        bc.refund_amount,
                        bc.refund_status,
                        bc.created_at,
                        b.user_id,
                        b.package_id,
                        b.number_of_people,
                        b.total_amount,
                        b.contact_name,
                        b.contact_phone,
                        b.contact_email,
                        b.special_requests,
                        b.status as booking_status,
                        b.created_at as booking_created_at
                    FROM booking_cancellations bc
                    LEFT JOIN bookings b ON bc.booking_id = b.booking_id
                    WHERE 1=1
                """'''

content = content.replace(old_query, new_query)

# Fix the filter - cancelled_by is now a UUID (user ref), not a string like 'user'/'admin'
# Actually looking at render_schema, cancelled_by is UUID REFERENCES users(user_id)
# But the endpoint passes string like 'user'/'admin'/'system'
# Since the actual DB has cancelled_by as UUID, we need to remove that filter or adjust
# For now, let's just remove the cancelled_by filter since it's a UUID not a role string
old_filter = '''                # Apply filter
                if cancelled_by:
                    query += " AND cancelled_by = %s"
                    params.append(cancelled_by)'''

new_filter = '''                # Note: cancelled_by in DB is a UUID reference to users, not a role string
                # Skip this filter as it's incompatible with current schema
                # if cancelled_by:
                #     query += " AND bc.cancelled_by = %s"
                #     params.append(cancelled_by)'''

content = content.replace(old_filter, new_filter)

# Fix the count query
old_count = '''                count_query = "SELECT COUNT(*) as cnt FROM booking_cancellations WHERE 1=1"
                count_params = []
                if cancelled_by:
                    count_query += " AND cancelled_by = %s"
                    count_params.append(cancelled_by)'''

new_count = '''                count_query = "SELECT COUNT(*) as cnt FROM booking_cancellations WHERE 1=1"
                count_params = []'''

content = content.replace(old_count, new_count)

# Fix the ordering - cancelled_at doesn't exist, use created_at
content = content.replace('query += " ORDER BY cancelled_at DESC"', 'query += " ORDER BY bc.created_at DESC"')

# Fix the formatted_data section to match new column names
old_format = '''                for cancel in rows:
                    # Get tour info
                    tour_name = "Unknown Tour"
                    if cancel.get('package_id'):
                        try:
                            cursor.execute(
                                "SELECT package_name, destination FROM tour_packages WHERE package_id = %s",
                                (cancel['package_id'],)
                            )
                            tour_row = cursor.fetchone()
                            if tour_row:
                                tour_name = tour_row.get('package_name', 'Unknown Tour')
                        except Exception as e:
                            logger.warning(f"Could not fetch tour info for {cancel.get('package_id')}: {str(e)}")

                    # Get user info
                    user_email = None
                    user_full_name = None
                    if cancel.get('user_id'):
                        try:
                            cursor.execute(
                                "SELECT email, full_name FROM users WHERE user_id = %s",
                                (cancel['user_id'],)
                            )
                            user_row = cursor.fetchone()
                            if user_row:
                                user_email = user_row.get('email')
                                user_full_name = user_row.get('full_name')
                        except Exception as e:
                            logger.warning(f"Could not fetch user info for {cancel.get('user_id')}: {str(e)}")

                    formatted_data.append({
                        "cancellation_id": str(cancel.get('cancellation_id')) if cancel.get('cancellation_id') else None,
                        "booking_id": str(cancel.get('booking_id')) if cancel.get('booking_id') else None,
                        "user_id": str(cancel.get('user_id')) if cancel.get('user_id') else None,
                        "user_email": user_email,
                        "user_full_name": user_full_name,
                        "package_id": str(cancel.get('package_id')) if cancel.get('package_id') else None,
                        "tour_name": tour_name,
                        # Booking snapshot
                        "number_of_people": cancel.get('number_of_people'),
                        "total_amount": float(cancel.get('total_amount', 0)) if cancel.get('total_amount') else 0,
                        "contact_name": cancel.get('contact_name'),
                        "contact_phone": cancel.get('contact_phone'),
                        "contact_email": cancel.get('contact_email'),
                        "special_requests": cancel.get('special_requests'),
                        "previous_status": cancel.get('previous_status'),
                        "booking_created_at": cancel.get('booking_created_at'),
                        # Cancellation info
                        "reason": cancel.get('reason'),
                        "cancelled_at": cancel.get('cancelled_at'),
                        "cancelled_by": cancel.get('cancelled_by'),
                        "created_at": cancel.get('created_at')
                    })'''

new_format = '''                for cancel in rows:
                    # Get tour info
                    tour_name = "Unknown Tour"
                    if cancel.get('package_id'):
                        try:
                            cursor.execute(
                                "SELECT package_name, destination FROM tour_packages WHERE package_id = %s",
                                (cancel['package_id'],)
                            )
                            tour_row = cursor.fetchone()
                            if tour_row:
                                tour_name = tour_row.get('package_name', 'Unknown Tour')
                        except Exception as e:
                            logger.warning(f"Could not fetch tour info for {cancel.get('package_id')}: {str(e)}")

                    # Get user info
                    user_email = None
                    user_full_name = None
                    if cancel.get('user_id'):
                        try:
                            cursor.execute(
                                "SELECT email, full_name FROM users WHERE user_id = %s",
                                (cancel['user_id'],)
                            )
                            user_row = cursor.fetchone()
                            if user_row:
                                user_email = user_row.get('email')
                                user_full_name = user_row.get('full_name')
                        except Exception as e:
                            logger.warning(f"Could not fetch user info for {cancel.get('user_id')}: {str(e)}")

                    formatted_data.append({
                        "cancellation_id": str(cancel.get('cancellation_id')) if cancel.get('cancellation_id') else None,
                        "booking_id": str(cancel.get('booking_id')) if cancel.get('booking_id') else None,
                        "user_id": str(cancel.get('user_id')) if cancel.get('user_id') else None,
                        "user_email": user_email,
                        "user_full_name": user_full_name,
                        "package_id": str(cancel.get('package_id')) if cancel.get('package_id') else None,
                        "tour_name": tour_name,
                        # Booking snapshot (from JOIN with bookings)
                        "number_of_people": cancel.get('number_of_people'),
                        "total_amount": float(cancel.get('total_amount', 0)) if cancel.get('total_amount') else 0,
                        "contact_name": cancel.get('contact_name'),
                        "contact_phone": cancel.get('contact_phone'),
                        "contact_email": cancel.get('contact_email'),
                        "special_requests": cancel.get('special_requests'),
                        "previous_status": cancel.get('booking_status'),
                        "booking_created_at": cancel.get('booking_created_at'),
                        # Cancellation info
                        "reason": cancel.get('reason'),
                        "cancelled_at": cancel.get('created_at'),
                        "cancelled_by": str(cancel.get('cancelled_by')) if cancel.get('cancelled_by') else None,
                        "refund_amount": float(cancel.get('refund_amount', 0)) if cancel.get('refund_amount') else 0,
                        "refund_status": cancel.get('refund_status'),
                        "created_at": cancel.get('created_at')
                    })'''

content = content.replace(old_format, new_format)

with open('app/v1/services/booking_management_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed booking_management_service.py")


# ==== FIX 4: promotion_service.py - quantity -> usage_limit, remove name ====
with open('app/v1/services/promotion_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace quantity with usage_limit in service code
content = content.replace("promo['used_count'] < promo['quantity']", "promo['used_count'] < promo['usage_limit']")
content = content.replace("promo['used_count'] >= promo['quantity']", "promo['used_count'] >= promo['usage_limit']")
content = content.replace('"quantity >= %s"', '"usage_limit >= %s"')
content = content.replace('"quantity <= %s"', '"usage_limit <= %s"')

with open('app/v1/services/promotion_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed promotion_service.py")


# ==== FIX 4b: promotion_schema.py - quantity -> usage_limit, name -> optional ====
with open('app/v1/schema/promotion_schema.py', 'r', encoding='utf-8') as f:
    content = f.read()

# In PromotionCreate: name is not in DB, remove it or make it map to description
# DB has: code, description, discount_type, discount_value, min_order_value, max_discount, usage_limit, used_count, start_date, end_date, is_active
# Schema has: name (not in DB), description, discount_type, discount_value, start_date, end_date, quantity (should be usage_limit), is_active

# Replace 'name' field with mapping note - actually we should remove name from Create
# and change quantity to usage_limit
content = content.replace(
    'name: str = Field(..., description="T\u00ean khuy\u1ebfn m\u00e3i (VD: Sale h\u00e8 2024)")',
    'description: Optional[str] = Field(None, description="M\u00f4 t\u1ea3 khuy\u1ebfn m\u00e3i (VD: Sale h\u00e8 2024)")'
)
# Remove the duplicate description field that already exists
content = content.replace(
    '    description: Optional[str] = Field(None, description="M\u00f4 t\u1ea3 khuy\u1ebfn m\u00e3i (VD: Sale h\u00e8 2024)")\n    description: Optional[str] = Field(None, description="M\u00f4 t\u1ea3 chi ti\u1ebft khuy\u1ebfn m\u00e3i")',
    '    description: Optional[str] = Field(None, description="M\u00f4 t\u1ea3 chi ti\u1ebft khuy\u1ebfn m\u00e3i")'
)

# Change quantity to usage_limit
content = content.replace(
    'quantity: int = Field(default=5, ge=1, description="S\u1ed1 l\u01b0\u1ee3ng m\u00e3 ban \u0111\u1ea7u")',
    'usage_limit: int = Field(default=5, ge=1, description="S\u1ed1 l\u01b0\u1ee3ng m\u00e3 ban \u0111\u1ea7u")'
)

# In PromotionUpdate
content = content.replace(
    '    name: Optional[str] = Field(None, description="T\u00ean khuy\u1ebfn m\u00e3i")\n    description: Optional[str] = Field(None, description="M\u00f4 t\u1ea3 chi ti\u1ebft")',
    '    description: Optional[str] = Field(None, description="M\u00f4 t\u1ea3 chi ti\u1ebft")'
)
content = content.replace(
    'quantity: Optional[int] = Field(None, ge=1, description="S\u1ed1 l\u01b0\u1ee3ng m\u00e3")',
    'usage_limit: Optional[int] = Field(None, ge=1, description="S\u1ed1 l\u01b0\u1ee3ng m\u00e3")'
)

# In PromotionResponse
content = content.replace(
    '    name: str\n    description: Optional[str]',
    '    description: Optional[str]'
)
content = content.replace(
    '    quantity: int\n    used_count: int',
    '    usage_limit: int\n    used_count: int'
)

with open('app/v1/schema/promotion_schema.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed promotion_schema.py")

print("\nAll 4 fixes applied!")
