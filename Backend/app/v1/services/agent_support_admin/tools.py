"""
Admin Agent Tools
Database query tools for admin agent
"""
import logging
from typing import Dict, Any, List
from langchain_core.tools import tool, StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class QueryDatabaseInput(BaseModel):
    """Input schema for query_database tool"""
    sql_query: str = Field(
        description="SQL SELECT query to execute. Must be a valid SELECT statement."
    )
    explanation: str = Field(
        default="",
        description="Brief explanation of what this query does"
    )


def _get_supabase_client():
    """Get Supabase client (legacy — hiện dùng Neon trực tiếp)."""
    from app.v1.core.supabase import get_supabase_client
    return get_supabase_client()


def _execute_admin_query(sql_query: str) -> Dict[str, Any]:
    """
    Execute admin query qua Neon (hàm admin_execute_query — SECURITY DEFINER,
    chỉ cho phép SELECT). Trước đây dùng Supabase RPC nhưng data giờ nằm ở Neon.

    Args:
        sql_query: SQL SELECT query

    Returns:
        Query result as dict
    """
    try:
        # Safety guard: chỉ cho phép SELECT/WITH (chặn INSERT/UPDATE/DELETE/DDL)
        stripped = sql_query.strip().lower()
        if not stripped.startswith(("select", "with")):
            return {"success": False, "error": "Only SELECT/WITH queries are allowed", "query": sql_query}

        import psycopg2
        from app.v1.core.config import settings

        conn = psycopg2.connect(settings.DATABASE_URL)
        try:
            with conn.cursor() as cur:
                # Hàm admin_execute_query trả về jsonb -> psycopg2 parse thành list/dict
                cur.execute("SELECT admin_execute_query(%s)", (sql_query,))
                row = cur.fetchone()
            data = row[0] if row else []
        finally:
            conn.close()

        if isinstance(data, dict) and data.get("error"):
            return {"success": False, "error": data.get("message", str(data)), "query": sql_query}
        if not isinstance(data, list):
            data = [data] if data else []
        return {
            "success": True,
            "data": data,
            "row_count": len(data),
            "query": sql_query,
        }

    except Exception as e:
        logger.error(f"Error executing admin query: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "query": sql_query
        }


@tool(args_schema=QueryDatabaseInput)
def query_database(sql_query: str, explanation: str = "") -> Dict[str, Any]:
    """
    Execute a SELECT query on the database.

    Available tables:
    - tour_packages: package_id, package_name, destination, price, duration_days, available_slots, start_date, end_date, is_active, created_at
    - bookings: booking_id, package_id, user_id, number_of_people, total_amount, status (pending/confirmed/cancelled/completed), created_at
    - users: user_id, email, full_name, phone_number, role (user/admin), is_active, created_at, last_access_time
    - payments: payment_id, booking_id, user_id, amount, payment_status, payment_method, created_at
    - reviews: review_id, package_id, user_id, rating (1-5), comment, created_at
    - promotions: promotion_id, code, discount_type, discount_value, is_active, start_date, end_date

    RULES:
    - Only SELECT queries allowed (no INSERT/UPDATE/DELETE)
    - Always include LIMIT (max 100 recommended)
    - Use aggregate functions: COUNT, SUM, AVG, MAX, MIN
    - Use JOINs when needed to combine data

    Example queries:
    - "SELECT COUNT(*) as total FROM bookings WHERE status = 'confirmed'"
    - "SELECT destination, COUNT(*) as cnt FROM tour_packages GROUP BY destination ORDER BY cnt DESC LIMIT 5"
    - "SELECT EXTRACT(MONTH FROM created_at) as month, SUM(total_amount) as revenue FROM bookings GROUP BY month"

    Args:
        sql_query: Valid SQL SELECT statement
        explanation: Brief explanation of the query purpose

    Returns:
        Query results as JSON with data array
    """
    logger.info(f"🔍 Admin Query: {sql_query[:100]}...")

    result = _execute_admin_query(sql_query)

    if result["success"]:
        logger.info(f"✅ Query returned {result['row_count']} rows")
    else:
        logger.warning(f"❌ Query failed: {result.get('error')}")

    return result


def get_admin_tools() -> List[StructuredTool]:
    """Get all admin tools"""
    return [query_database]
