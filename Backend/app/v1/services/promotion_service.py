"""
Promotion Service
Handles all promotion-related business logic
"""
import logging
import random
import string
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
from ..core.config import settings

logger = logging.getLogger(__name__)


class PromotionService:
    """Service for managing promotions and tour-promotion relationships"""

    def __init__(self):
        self.db_url = settings.DATABASE_URL

    def _get_conn(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    def _normalize(self, rows):
        return [dict(r) for r in rows]

    def _generate_promotion_code(self) -> str:
        """
        Tạo mã khuyến mãi ngẫu nhiên 8 ký tự (chữ và số)

        Returns:
            str: Mã khuyến mãi 8 ký tự
        """
        characters = string.ascii_uppercase + string.digits
        return ''.join(random.choice(characters) for _ in range(8))

    def create_promotion(self, promotion_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tạo mới một promotion

        Args:
            promotion_data: Dict chứa thông tin promotion

        Returns:
            Dict với EC, EM và promotion data
        """
        try:
            # Convert datetime to ISO format strings
            if isinstance(promotion_data.get('start_date'), datetime):
                promotion_data['start_date'] = promotion_data['start_date'].isoformat()
            if isinstance(promotion_data.get('end_date'), datetime):
                promotion_data['end_date'] = promotion_data['end_date'].isoformat()

            # Set default values
            if 'used_count' not in promotion_data:
                promotion_data['used_count'] = 0

            # Tạo mã khuyến mãi tự động
            if 'code' not in promotion_data or not promotion_data['code']:
                promotion_data['code'] = self._generate_promotion_code()

            # Insert into database
            with self._get_conn() as conn:
                cursor = conn.cursor()

                columns = promotion_data.keys()
                values = promotion_data.values()
                placeholders = ', '.join(['%s'] * len(columns))
                columns_str = ', '.join(columns)

                query = f"""
                    INSERT INTO promotions ({columns_str})
                    VALUES ({placeholders})
                    RETURNING *
                """

                cursor.execute(query, list(values))
                result = cursor.fetchone()
                conn.commit()

                if not result:
                    return {
                        "EC": 1,
                        "EM": "Failed to create promotion",
                        "promotion": None
                    }

                # Convert UUID to string
                result = dict(result)
                if 'promotion_id' in result:
                    result['promotion_id'] = str(result['promotion_id'])

                logger.info(f"Created promotion: {result['promotion_id']}")
                return {
                    "EC": 0,
                    "EM": "Promotion created successfully",
                    "promotion": result
                }

        except Exception as e:
            logger.error(f"Error creating promotion: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error creating promotion: {str(e)}",
                "promotion": None
            }

    def get_promotion_by_id(self, promotion_id: str) -> Dict[str, Any]:
        """
        Lấy thông tin chi tiết một promotion

        Args:
            promotion_id: UUID của promotion

        Returns:
            Dict với EC, EM và promotion data
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM promotions WHERE promotion_id = %s"
                cursor.execute(query, (promotion_id,))
                result = cursor.fetchone()

                if not result:
                    return {
                        "EC": 1,
                        "EM": f"Promotion not found: {promotion_id}",
                        "promotion": None
                    }

                # Convert UUID to string
                result = dict(result)
                if 'promotion_id' in result:
                    result['promotion_id'] = str(result['promotion_id'])

                return {
                    "EC": 0,
                    "EM": "Promotion found",
                    "promotion": result
                }

        except Exception as e:
            logger.error(f"Error getting promotion: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error getting promotion: {str(e)}",
                "promotion": None
            }

    def get_promotion_by_code(self, code: str) -> Dict[str, Any]:
        """
        Lấy thông tin chi tiết một promotion bằng code

        Args:
            code: Mã khuyến mãi (8 ký tự)

        Returns:
            Dict với EC, EM và promotion data
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM promotions WHERE code = %s"
                cursor.execute(query, (code,))
                result = cursor.fetchone()

                if not result:
                    return {
                        "EC": 1,
                        "EM": f"Promotion not found with code: {code}",
                        "promotion": None
                    }

                # Convert UUID to string
                result = dict(result)
                if 'promotion_id' in result:
                    result['promotion_id'] = str(result['promotion_id'])

                return {
                    "EC": 0,
                    "EM": "Promotion found",
                    "promotion": result
                }

        except Exception as e:
            logger.error(f"Error getting promotion by code: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error getting promotion: {str(e)}",
                "promotion": None
            }

    def get_all_promotions(
        self,
        is_active: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Lấy danh sách tất cả promotions

        Args:
            is_active: Lọc theo trạng thái
            limit: Giới hạn số lượng
            offset: Bỏ qua số lượng

        Returns:
            Dict với EC, EM, found và danh sách promotions
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                # Build query with filters
                conditions = []
                params = []

                if is_active is not None:
                    conditions.append("is_active = %s")
                    params.append(is_active)

                where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

                # Build pagination
                limit_clause = ""
                if limit is not None:
                    limit_clause = f"LIMIT {limit}"
                    if offset is not None:
                        limit_clause += f" OFFSET {offset}"

                query = f"SELECT * FROM promotions {where_clause} {limit_clause}"
                cursor.execute(query, params)
                results = cursor.fetchall()

                # Convert UUIDs to strings
                promotions = []
                for row in results:
                    row = dict(row)
                    if 'promotion_id' in row:
                        row['promotion_id'] = str(row['promotion_id'])
                    promotions.append(row)

                return {
                    "EC": 0,
                    "EM": "Promotions retrieved successfully",
                    "found": len(promotions),
                    "promotions": promotions
                }

        except Exception as e:
            logger.error(f"Error getting promotions: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error getting promotions: {str(e)}",
                "found": 0,
                "promotions": []
            }

    def filter_promotions_by_discount(
        self,
        min_discount_value: Optional[float] = None,
        max_discount_value: Optional[float] = None,
        is_active: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Lọc promotions theo khoảng discount_value
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                # Build query with filters
                conditions = []
                params = []

                if min_discount_value is not None:
                    conditions.append("discount_value >= %s")
                    params.append(min_discount_value)
                if max_discount_value is not None:
                    conditions.append("discount_value <= %s")
                    params.append(max_discount_value)
                if is_active is not None:
                    conditions.append("is_active = %s")
                    params.append(is_active)

                where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

                # Build pagination
                limit_clause = ""
                if limit is not None:
                    limit_clause = f"LIMIT {limit}"
                    if offset is not None:
                        limit_clause += f" OFFSET {offset}"

                query = f"SELECT * FROM promotions {where_clause} {limit_clause}"
                cursor.execute(query, params)
                results = cursor.fetchall()

                # Convert UUIDs to strings
                promotions = []
                for row in results:
                    row = dict(row)
                    if 'promotion_id' in row:
                        row['promotion_id'] = str(row['promotion_id'])
                    promotions.append(row)

                return {
                    "EC": 0,
                    "EM": "Promotions filtered by discount_value successfully",
                    "found": len(promotions),
                    "promotions": promotions
                }

        except Exception as e:
            logger.error(f"Error filtering promotions by discount_value: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error filtering promotions: {str(e)}",
                "found": 0,
                "promotions": []
            }

    def filter_promotions_by_date_range(
        self,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        is_active: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Filter promotions by date, comparing ONLY the calendar date (YYYY-MM-DD),
        ignoring time and timezone, implemented via half-open day ranges:
        - Only start_date: start_date in [start_date 00:00, start_date+1 00:00)
        - Only end_date: end_date in [end_date 00:00, end_date+1 00:00)
        - Both: intersection of both conditions
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                # Build day-range boundaries as ISO strings (Postgres will cast to timestamp)
                conditions = []
                params = []

                if start_date is not None:
                    start_day = start_date.date()
                    start_lower = start_day.isoformat()  # YYYY-MM-DD 00:00 implicit
                    # next day for upper bound (exclusive)
                    start_upper = (start_day + timedelta(days=1)).isoformat()
                    conditions.append("start_date >= %s")
                    params.append(start_lower)
                    conditions.append("start_date < %s")
                    params.append(start_upper)

                if end_date is not None:
                    end_day = end_date.date()
                    end_lower = end_day.isoformat()
                    end_upper = (end_day + timedelta(days=1)).isoformat()
                    conditions.append("end_date >= %s")
                    params.append(end_lower)
                    conditions.append("end_date < %s")
                    params.append(end_upper)

                if is_active is not None:
                    conditions.append("is_active = %s")
                    params.append(is_active)

                where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

                # Build pagination
                limit_clause = ""
                if limit is not None:
                    limit_clause = f"LIMIT {limit}"
                    if offset is not None:
                        limit_clause += f" OFFSET {offset}"

                query = f"SELECT * FROM promotions {where_clause} {limit_clause}"
                cursor.execute(query, params)
                results = cursor.fetchall()

                # Convert UUIDs to strings
                promotions = []
                for row in results:
                    row = dict(row)
                    if 'promotion_id' in row:
                        row['promotion_id'] = str(row['promotion_id'])
                    promotions.append(row)

                return {
                    "EC": 0,
                    "EM": "Promotions filtered by date range successfully",
                    "found": len(promotions),
                    "promotions": promotions
                }

        except Exception as e:
            logger.error(f"Error filtering promotions by date range: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error filtering promotions: {str(e)}",
                "found": 0,
                "promotions": []
            }

    def filter_promotions_by_quantity(
        self,
        min_quantity: Optional[int] = None,
        max_quantity: Optional[int] = None,
        is_active: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Lọc promotions theo khoảng quantity
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                # Build query with filters
                conditions = []
                params = []

                if min_quantity is not None:
                    conditions.append("usage_limit >= %s")
                    params.append(min_quantity)
                if max_quantity is not None:
                    conditions.append("usage_limit <= %s")
                    params.append(max_quantity)
                if is_active is not None:
                    conditions.append("is_active = %s")
                    params.append(is_active)

                where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

                # Build pagination
                limit_clause = ""
                if limit is not None:
                    limit_clause = f"LIMIT {limit}"
                    if offset is not None:
                        limit_clause += f" OFFSET {offset}"

                query = f"SELECT * FROM promotions {where_clause} {limit_clause}"
                cursor.execute(query, params)
                results = cursor.fetchall()

                # Convert UUIDs to strings
                promotions = []
                for row in results:
                    row = dict(row)
                    if 'promotion_id' in row:
                        row['promotion_id'] = str(row['promotion_id'])
                    promotions.append(row)

                return {
                    "EC": 0,
                    "EM": "Promotions filtered by quantity successfully",
                    "found": len(promotions),
                    "promotions": promotions
                }

        except Exception as e:
            logger.error(f"Error filtering promotions by quantity: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error filtering promotions: {str(e)}",
                "found": 0,
                "promotions": []
            }

    def filter_promotions_by_used_count(
        self,
        min_user_count: Optional[int] = None,
        max_user_count: Optional[int] = None,
        is_active: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Lọc promotions theo khoảng used_count (user_count)
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                # Build query with filters
                conditions = []
                params = []

                if min_user_count is not None:
                    conditions.append("used_count >= %s")
                    params.append(min_user_count)
                if max_user_count is not None:
                    conditions.append("used_count <= %s")
                    params.append(max_user_count)
                if is_active is not None:
                    conditions.append("is_active = %s")
                    params.append(is_active)

                where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

                # Build pagination
                limit_clause = ""
                if limit is not None:
                    limit_clause = f"LIMIT {limit}"
                    if offset is not None:
                        limit_clause += f" OFFSET {offset}"

                query = f"SELECT * FROM promotions {where_clause} {limit_clause}"
                cursor.execute(query, params)
                results = cursor.fetchall()

                # Convert UUIDs to strings
                promotions = []
                for row in results:
                    row = dict(row)
                    if 'promotion_id' in row:
                        row['promotion_id'] = str(row['promotion_id'])
                    promotions.append(row)

                return {
                    "EC": 0,
                    "EM": "Promotions filtered by user_count successfully",
                    "found": len(promotions),
                    "promotions": promotions
                }

        except Exception as e:
            logger.error(f"Error filtering promotions by user_count: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error filtering promotions: {str(e)}",
                "found": 0,
                "promotions": []
            }

    def update_promotion(self, promotion_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cập nhật thông tin promotion

        Args:
            promotion_id: UUID của promotion
            update_data: Dict chứa dữ liệu cần update

        Returns:
            Dict với EC, EM và promotion data
        """
        try:
            # Convert datetime to ISO format strings
            if isinstance(update_data.get('start_date'), datetime):
                update_data['start_date'] = update_data['start_date'].isoformat()
            if isinstance(update_data.get('end_date'), datetime):
                update_data['end_date'] = update_data['end_date'].isoformat()

            # Update database
            with self._get_conn() as conn:
                cursor = conn.cursor()

                # Build UPDATE query
                set_clauses = [f"{key} = %s" for key in update_data.keys()]
                set_clause = ', '.join(set_clauses)
                params = list(update_data.values()) + [promotion_id]

                query = f"""
                    UPDATE promotions
                    SET {set_clause}
                    WHERE promotion_id = %s
                    RETURNING *
                """

                cursor.execute(query, params)
                result = cursor.fetchone()
                conn.commit()

                if not result:
                    return {
                        "EC": 1,
                        "EM": f"Promotion not found: {promotion_id}",
                        "promotion": None
                    }

                # Convert UUID to string
                result = dict(result)
                if 'promotion_id' in result:
                    result['promotion_id'] = str(result['promotion_id'])

                logger.info(f"Updated promotion: {promotion_id}")
                return {
                    "EC": 0,
                    "EM": "Promotion updated successfully",
                    "promotion": result
                }

        except Exception as e:
            logger.error(f"Error updating promotion: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error updating promotion: {str(e)}",
                "promotion": None
            }

    def delete_promotion(self, promotion_id: str) -> Dict[str, Any]:
        """
        Xóa một promotion

        Args:
            promotion_id: UUID của promotion

        Returns:
            Dict với EC và EM
        """
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()

                query = """
                    DELETE FROM promotions
                    WHERE promotion_id = %s
                    RETURNING promotion_id
                """

                cursor.execute(query, (promotion_id,))
                result = cursor.fetchone()
                conn.commit()

                if not result:
                    return {
                        "EC": 1,
                        "EM": f"Promotion not found: {promotion_id}"
                    }

                logger.info(f"Deleted promotion: {promotion_id}")
                return {
                    "EC": 0,
                    "EM": "Promotion deleted successfully"
                }

        except Exception as e:
            logger.error(f"Error deleting promotion: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error deleting promotion: {str(e)}"
            }

    def get_available_promotions(self) -> Dict[str, Any]:
        """
        Lấy tất cả mã khuyến mãi còn hạn và còn số lượng
        Áp dụng cho TẤT CẢ tour

        Returns:
            Dict với EC, EM, found và danh sách promotions
        """
        try:
            # Get current time
            now = datetime.now()

            # Query all promotions
            with self._get_conn() as conn:
                cursor = conn.cursor()

                query = "SELECT * FROM promotions WHERE is_active = %s"
                cursor.execute(query, (True,))
                results = cursor.fetchall()

                if not results:
                    return {
                        "EC": 0,
                        "EM": "No promotions available",
                        "found": 0,
                        "promotions": []
                    }

                # Filter promotions: còn hạn, còn số lượng
                valid_promotions = []
                for promo_dict in results:
                    promo = dict(promo_dict)
                    try:
                        # Parse dates from database (handle string or datetime objects)
                        start_date_str = promo['start_date']
                        end_date_str = promo['end_date']

                        # Convert to datetime if string, or use directly if already datetime
                        if isinstance(start_date_str, str):
                            # Handle ISO format with or without timezone
                            if 'Z' in start_date_str:
                                start_date_str = start_date_str.replace('Z', '+00:00')
                            # Parse and remove timezone info for comparison
                            start_date = datetime.fromisoformat(start_date_str).replace(tzinfo=None)
                        else:
                            # Already a datetime object, just ensure no timezone
                            start_date = start_date_str.replace(tzinfo=None) if start_date_str.tzinfo else start_date_str

                        if isinstance(end_date_str, str):
                            # Handle ISO format with or without timezone
                            if 'Z' in end_date_str:
                                end_date_str = end_date_str.replace('Z', '+00:00')
                            # Parse and remove timezone info for comparison
                            end_date = datetime.fromisoformat(end_date_str).replace(tzinfo=None)
                        else:
                            # Already a datetime object, just ensure no timezone
                            end_date = end_date_str.replace(tzinfo=None) if end_date_str.tzinfo else end_date_str

                        # Check if still valid
                        is_valid_time = start_date <= now <= end_date
                        has_quantity = promo['used_count'] < promo['usage_limit']

                        if is_valid_time and has_quantity:
                            # Convert UUID to string
                            if 'promotion_id' in promo:
                                promo['promotion_id'] = str(promo['promotion_id'])
                            valid_promotions.append(promo)
                    except Exception as date_error:
                        logger.warning(f"Error parsing dates for promotion {promo.get('promotion_id')}: {str(date_error)}")
                        continue

                return {
                    "EC": 0,
                    "EM": "Promotions retrieved successfully",
                    "found": len(valid_promotions),
                    "promotions": valid_promotions
                }

        except Exception as e:
            logger.error(f"Error getting available promotions: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error getting promotions: {str(e)}",
                "found": 0,
                "promotions": []
            }

    def apply_promotion_to_booking(
        self,
        promotion_id: str,
        original_price: float
    ) -> Dict[str, Any]:
        """
        Áp dụng mã khuyến mãi: tính giá sau giảm và tăng used_count

        Args:
            promotion_id: UUID của promotion
            original_price: Giá gốc

        Returns:
            Dict với EC, EM, final_price và discount_amount
        """
        try:
            # Get promotion details
            promo_result = self.get_promotion_by_id(promotion_id)
            if promo_result['EC'] != 0:
                return {
                    "EC": 1,
                    "EM": "Promotion not found",
                    "final_price": original_price,
                    "discount_amount": 0
                }

            promo = promo_result['promotion']

            # Validate promotion
            now = datetime.now()

            # Parse dates from database (handle string or datetime objects)
            start_date_str = promo['start_date']
            end_date_str = promo['end_date']

            # Convert to datetime if string, or use directly if already datetime
            if isinstance(start_date_str, str):
                # Handle ISO format with or without timezone
                if 'Z' in start_date_str:
                    start_date_str = start_date_str.replace('Z', '+00:00')
                # Parse and remove timezone info for comparison
                start_date = datetime.fromisoformat(start_date_str).replace(tzinfo=None)
            else:
                # Already a datetime object, just ensure no timezone
                start_date = start_date_str.replace(tzinfo=None) if start_date_str.tzinfo else start_date_str

            if isinstance(end_date_str, str):
                # Handle ISO format with or without timezone
                if 'Z' in end_date_str:
                    end_date_str = end_date_str.replace('Z', '+00:00')
                # Parse and remove timezone info for comparison
                end_date = datetime.fromisoformat(end_date_str).replace(tzinfo=None)
            else:
                # Already a datetime object, just ensure no timezone
                end_date = end_date_str.replace(tzinfo=None) if end_date_str.tzinfo else end_date_str

            # Check if promotion is still valid
            if not (start_date <= now <= end_date):
                return {
                    "EC": 1,
                    "EM": "Promotion has expired or not started yet",
                    "final_price": original_price,
                    "discount_amount": 0
                }

            # Check if promotion is active
            if not promo.get('is_active', False):
                return {
                    "EC": 1,
                    "EM": "Promotion is not active",
                    "final_price": original_price,
                    "discount_amount": 0
                }

            # Check if promotion has available quantity
            if promo['used_count'] >= promo['usage_limit']:
                return {
                    "EC": 1,
                    "EM": "Promotion has reached its usage limit",
                    "final_price": original_price,
                    "discount_amount": 0
                }

            # Calculate discount
            discount_amount = 0
            if promo['discount_type'] == 'PERCENTAGE':
                discount_amount = original_price * (promo['discount_value'] / 100)
            elif promo['discount_type'] == 'FIXED_AMOUNT':
                discount_amount = promo['discount_value']

            # Ensure discount doesn't exceed original price
            discount_amount = min(discount_amount, original_price)
            final_price = original_price - discount_amount

            # Increment used_count
            new_used_count = promo['used_count'] + 1

            with self._get_conn() as conn:
                cursor = conn.cursor()

                query = """
                    UPDATE promotions
                    SET used_count = %s
                    WHERE promotion_id = %s
                    RETURNING promotion_id
                """

                cursor.execute(query, (new_used_count, promotion_id))
                result = cursor.fetchone()
                conn.commit()

                if not result:
                    logger.error(f"Failed to increment used_count for promotion {promotion_id}")

            logger.info(
                f"Applied promotion {promotion_id}: {original_price} -> {final_price} (discount: {discount_amount})")
            return {
                "EC": 0,
                "EM": "Promotion applied successfully",
                "final_price": final_price,
                "discount_amount": discount_amount
            }

        except Exception as e:
            logger.error(f"Error applying promotion: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error applying promotion: {str(e)}",
                "final_price": original_price,
                "discount_amount": 0
            }


# Dependency function
def get_promotion_service() -> PromotionService:
    """Dependency injection for PromotionService"""
    return PromotionService()
