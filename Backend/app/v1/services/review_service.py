"""
Review Service
Handles review CRUD operations
"""
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from ..core.config import settings

logger = logging.getLogger(__name__)


class ReviewService:
    """Service for managing tour reviews"""

    def __init__(self):
        """Initialize ReviewService"""
        self.db_url = settings.DATABASE_URL

    def _get_conn(self):
        """Get a database connection with RealDictCursor"""
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    def _normalize(self, rows):
        """Convert psycopg2 RealDict rows to regular dicts"""
        return [dict(r) for r in rows]

    def get_all_reviews(
        self,
        package_id: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        rating: Optional[int] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get all reviews with optional filters

        Args:
            package_id: Filter by package ID
            user_id: Filter by user ID
            status: Filter by review status
            rating: Filter by rating
            limit: Maximum number of results
            offset: Number of records to skip

        Returns:
            Dict with EC, EM, data, and total
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Build base query with JOINs
                    query = """
                        SELECT
                            r.review_id, r.booking_id, r.user_id, r.package_id,
                            r.rating, r.comment, r.status, r.created_at, r.updated_at,
                            u.full_name as user_full_name, u.email as user_email,
                            u.profile_picture as user_profile_picture,
                            tp.package_name, tp.destination, tp.price,
                            ROW_NUMBER() OVER (ORDER BY r.created_at DESC) as row_num
                        FROM reviews r
                        LEFT JOIN users u ON r.user_id = u.user_id
                        LEFT JOIN tour_packages tp ON r.package_id = tp.package_id
                        WHERE 1=1
                    """

                    # Build filters
                    params = []
                    if package_id:
                        query += " AND r.package_id = %s"
                        params.append(package_id)
                    if user_id:
                        query += " AND r.user_id = %s"
                        params.append(user_id)
                    if status is not None:
                        query += " AND r.status = %s"
                        params.append(status)
                    if rating:
                        query += " AND r.rating = %s"
                        params.append(rating)

                    # Add ordering
                    query += " ORDER BY r.created_at DESC"

                    # Add total count query
                    count_query = f"SELECT COUNT(*) as total FROM ({query}) as subq"

                    # Get total count
                    cur.execute(count_query, params)
                    total = cur.fetchone()['total']

                    # Add pagination
                    if limit:
                        query += " LIMIT %s"
                        params.append(limit)
                    if offset:
                        query += " OFFSET %s"
                        params.append(offset)

                    # Execute main query
                    cur.execute(query, params)
                    rows = cur.fetchall()

                    # Flatten and format data
                    flattened_data = []
                    for row in rows:
                        flattened_review = {
                            "review_id": str(row['review_id']) if row['review_id'] else None,
                            "booking_id": str(row['booking_id']) if row['booking_id'] else None,
                            "user_id": str(row['user_id']) if row['user_id'] else None,
                            "package_id": str(row['package_id']) if row['package_id'] else None,
                            "rating": row['rating'],
                            "comment": row['comment'],
                            "status": row['status'],
                            "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                            "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
                            "user_full_name": row.get('user_full_name'),
                            "user_email": row.get('user_email'),
                            "user_profile_picture": row.get('user_profile_picture'),
                            "package_name": row.get('package_name'),
                            "package": {
                                "package_id": str(row['package_id']) if row['package_id'] else None,
                                "package_name": row.get('package_name'),
                                "destination": row.get('destination'),
                                "price": row.get('price')
                            } if row.get('package_name') else None
                        }
                        flattened_data.append(flattened_review)

                    return {
                        "EC": 0,
                        "EM": "Success",
                        "data": flattened_data,
                        "total": total
                    }

        except Exception as e:
            logger.error(f"Error getting reviews: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error retrieving reviews: {str(e)}",
                "data": None,
                "total": 0
            }

    def get_review_by_id(self, review_id: str) -> Dict[str, Any]:
        """
        Get review by ID

        Args:
            review_id: UUID of the review

        Returns:
            Dict with EC, EM, and data
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT review_id, booking_id, user_id, package_id,
                               rating, comment, status, created_at, updated_at
                        FROM reviews
                        WHERE review_id = %s
                    """
                    cur.execute(query, (review_id,))
                    row = cur.fetchone()

                    if not row:
                        return {
                            "EC": 1,
                            "EM": "Review not found",
                            "data": None
                        }

                    review = dict(row)
                    review['review_id'] = str(review['review_id'])
                    review['booking_id'] = str(review['booking_id']) if review['booking_id'] else None
                    review['user_id'] = str(review['user_id']) if review['user_id'] else None
                    review['package_id'] = str(review['package_id']) if review['package_id'] else None
                    review['created_at'] = review['created_at'].isoformat() if review['created_at'] else None
                    review['updated_at'] = review['updated_at'].isoformat() if review['updated_at'] else None

                    return {
                        "EC": 0,
                        "EM": "Success",
                        "data": review
                    }

        except Exception as e:
            logger.error(f"Error getting review {review_id}: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error retrieving review: {str(e)}",
                "data": None
            }

    def get_review_detail(self, review_id: str) -> Dict[str, Any]:
        """
        Get review detail with user and package information

        Args:
            review_id: UUID of the review

        Returns:
            Dict with EC, EM, and data (includes user and package info)
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    query = """
                        SELECT
                            r.review_id, r.booking_id, r.user_id, r.package_id,
                            r.rating, r.comment, r.status, r.created_at, r.updated_at,
                            u.full_name as user_full_name, u.email as user_email,
                            u.profile_picture as user_profile_picture,
                            tp.package_name, tp.destination
                        FROM reviews r
                        LEFT JOIN users u ON r.user_id = u.user_id
                        LEFT JOIN tour_packages tp ON r.package_id = tp.package_id
                        WHERE r.review_id = %s
                    """
                    cur.execute(query, (review_id,))
                    row = cur.fetchone()

                    if not row:
                        return {
                            "EC": 1,
                            "EM": "Review not found",
                            "data": None
                        }

                    review_detail = {
                        "review_id": str(row['review_id']) if row['review_id'] else None,
                        "booking_id": str(row['booking_id']) if row['booking_id'] else None,
                        "user_id": str(row['user_id']) if row['user_id'] else None,
                        "package_id": str(row['package_id']) if row['package_id'] else None,
                        "rating": row['rating'],
                        "comment": row['comment'],
                        "status": row['status'],
                        "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                        "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
                        "user_full_name": row.get('user_full_name'),
                        "user_email": row.get('user_email'),
                        "user_profile_picture": row.get('user_profile_picture'),
                        "package_name": row.get('package_name'),
                        "destination": row.get('destination')
                    }

                    return {
                        "EC": 0,
                        "EM": "Success",
                        "data": review_detail
                    }

        except Exception as e:
            logger.error(f"Error getting review detail {review_id}: {str(e)}")
            return {
                "EC": 2,
                "EM": f"Error retrieving review detail: {str(e)}",
                "data": None
            }

    def create_review(self, review_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        """
        Create a new review

        Args:
            review_data: Dictionary containing review information
                - booking_id: UUID
                - package_id: UUID
                - rating: int (1-5)
                - comment: Optional[str]
            user_id: UUID of the user creating the review

        Returns:
            Dict with EC, EM, and data
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Verify booking exists and belongs to user
                    booking_query = """
                        SELECT booking_id, user_id, package_id, status
                        FROM bookings
                        WHERE booking_id = %s
                    """
                    cur.execute(booking_query, (str(review_data['booking_id']),))
                    booking_row = cur.fetchone()

                    if not booking_row:
                        return {
                            "EC": 1,
                            "EM": "Booking not found",
                            "data": None
                        }

                    booking = dict(booking_row)

                    # Check if booking belongs to user
                    if str(booking['user_id']) != str(user_id):
                        return {
                            "EC": 2,
                            "EM": "You can only review your own bookings",
                            "data": None
                        }

                    # Check if booking is completed
                    if booking['status'] != 'completed':
                        return {
                            "EC": 3,
                            "EM": f"Only completed bookings can be reviewed. Current status: {booking['status']}",
                            "data": None
                        }

                    # Verify package_id matches booking's package_id
                    if str(booking['package_id']) != str(review_data['package_id']):
                        return {
                            "EC": 4,
                            "EM": "Package ID does not match the booking's package",
                            "data": None
                        }

                    # Check if review already exists for this booking
                    existing_review_query = """
                        SELECT review_id
                        FROM reviews
                        WHERE booking_id = %s
                    """
                    cur.execute(existing_review_query, (str(review_data['booking_id']),))
                    if cur.fetchone():
                        return {
                            "EC": 5,
                            "EM": "A review already exists for this booking",
                            "data": None
                        }

                    # Prepare review data
                    now = datetime.now(timezone.utc)

                    insert_query = """
                        INSERT INTO reviews (booking_id, user_id, package_id, rating, comment, status, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING review_id, booking_id, user_id, package_id, rating, comment, status, created_at, updated_at
                    """

                    cur.execute(insert_query, (
                        str(review_data['booking_id']),
                        str(user_id),
                        str(review_data['package_id']),
                        review_data['rating'],
                        review_data.get('comment'),
                        'pending',  # status
                        now,
                        now
                    ))

                    conn.commit()
                    result_row = cur.fetchone()
                    result = dict(result_row)

                    # Convert UUIDs and timestamps
                    result['review_id'] = str(result['review_id'])
                    result['booking_id'] = str(result['booking_id'])
                    result['user_id'] = str(result['user_id'])
                    result['package_id'] = str(result['package_id'])
                    result['created_at'] = result['created_at'].isoformat()
                    result['updated_at'] = result['updated_at'].isoformat()

                    logger.info(f"Created review {result['review_id']} for booking {review_data['booking_id']}")

                    return {
                        "EC": 0,
                        "EM": "Review created successfully",
                        "data": result
                    }

        except Exception as e:
            logger.error(f"Error creating review: {str(e)}")
            return {
                "EC": 7,
                "EM": f"Error creating review: {str(e)}",
                "data": None
            }

    def update_review(
        self,
        review_id: str,
        update_data: Dict[str, Any],
        user_id: Optional[str] = None,
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """
        Update review information

        Args:
            review_id: UUID of the review
            update_data: Dictionary containing fields to update
            user_id: UUID of the user (required if not admin)
            is_admin: Whether the user is an admin

        Returns:
            Dict with EC, EM, and data
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Check if review exists
                    existing = self.get_review_by_id(review_id)
                    if existing["EC"] != 0:
                        return existing

                    review = existing["data"]

                    # Check permissions: only owner or admin can update
                    if not is_admin:
                        if not user_id:
                            return {
                                "EC": 1,
                                "EM": "User ID is required",
                                "data": None
                            }

                        if str(review['user_id']) != str(user_id):
                            return {
                                "EC": 2,
                                "EM": "You can only update your own reviews",
                                "data": None
                            }

                    # Only admin can update status
                    if 'status' in update_data and not is_admin:
                        return {
                            "EC": 3,
                            "EM": "Only admins can change review status",
                            "data": None
                        }

                    # When user (not admin) updates review content, reset approval status
                    if not is_admin and ('rating' in update_data or 'comment' in update_data):
                        update_data['status'] = 'pending'
                        logger.info(f"Review {review_id} approval reset due to content change by user")

                    # Add updated_at timestamp
                    update_data['updated_at'] = datetime.now(timezone.utc)

                    # Build update query dynamically
                    update_fields = []
                    values = []
                    for key, value in update_data.items():
                        if key != 'review_id':  # Don't update the primary key
                            update_fields.append(f"{key} = %s")
                            values.append(value)

                    if not update_fields:
                        return {
                            "EC": 4,
                            "EM": "No valid fields to update",
                            "data": None
                        }

                    values.append(review_id)
                    query = f"""
                        UPDATE reviews
                        SET {', '.join(update_fields)}
                        WHERE review_id = %s
                        RETURNING review_id, booking_id, user_id, package_id, rating, comment, status, created_at, updated_at
                    """

                    cur.execute(query, values)
                    conn.commit()

                    result_row = cur.fetchone()
                    if not result_row:
                        return {
                            "EC": 4,
                            "EM": "Failed to update review",
                            "data": None
                        }

                    result = dict(result_row)
                    result['review_id'] = str(result['review_id'])
                    result['booking_id'] = str(result['booking_id']) if result['booking_id'] else None
                    result['user_id'] = str(result['user_id']) if result['user_id'] else None
                    result['package_id'] = str(result['package_id']) if result['package_id'] else None
                    result['created_at'] = result['created_at'].isoformat() if result['created_at'] else None
                    result['updated_at'] = result['updated_at'].isoformat() if result['updated_at'] else None

                    logger.info(f"Updated review {review_id}")

                    return {
                        "EC": 0,
                        "EM": "Review updated successfully",
                        "data": result
                    }

        except Exception as e:
            logger.error(f"Error updating review {review_id}: {str(e)}")
            return {
                "EC": 5,
                "EM": f"Error updating review: {str(e)}",
                "data": None
            }

    def delete_review(
        self,
        review_id: str,
        user_id: Optional[str] = None,
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """
        Delete a review

        Args:
            review_id: UUID of the review
            user_id: UUID of the user (required if not admin)
            is_admin: Whether the user is an admin

        Returns:
            Dict with EC and EM
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Check if review exists
                    existing = self.get_review_by_id(review_id)
                    if existing["EC"] != 0:
                        return existing

                    review = existing["data"]

                    # Check permissions: only owner or admin can delete
                    if not is_admin:
                        if not user_id:
                            return {
                                "EC": 1,
                                "EM": "User ID is required",
                                "data": None
                            }

                        if str(review['user_id']) != str(user_id):
                            return {
                                "EC": 2,
                                "EM": "You can only delete your own reviews",
                                "data": None
                            }

                    # Delete review
                    query = "DELETE FROM reviews WHERE review_id = %s RETURNING review_id"
                    cur.execute(query, (review_id,))
                    conn.commit()

                    if not cur.fetchone():
                        return {
                            "EC": 3,
                            "EM": "Failed to delete review"
                        }

                    logger.info(f"Deleted review {review_id}")

                    return {
                        "EC": 0,
                        "EM": "Review deleted successfully"
                    }

        except Exception as e:
            logger.error(f"Error deleting review {review_id}: {str(e)}")
            return {
                "EC": 4,
                "EM": f"Error deleting review: {str(e)}"
            }

    def get_reviews_by_package(
        self,
        package_id: str,
        status: str = 'approved',
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get all approved reviews for a package

        Args:
            package_id: UUID of the package
            status: Filter by status (default: True)
            limit: Maximum number of results
            offset: Number of records to skip

        Returns:
            Dict with EC, EM, data, and total
        """
        return self.get_all_reviews(
            package_id=package_id,
            status=status,
            limit=limit,
            offset=offset
        )

    def get_review_stats(self, package_id: str) -> Dict[str, Any]:
        """
        Get review statistics for a package

        Args:
            package_id: UUID of the package

        Returns:
            Dict with EC, EM, and data (stats)
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Get all approved reviews for the package
                    query = """
                        SELECT rating
                        FROM reviews
                        WHERE package_id = %s AND status = %s
                    """
                    cur.execute(query, (package_id, 'approved'))
                    rows = cur.fetchall()

                    if not rows:
                        return {
                            "EC": 0,
                            "EM": "Success",
                            "data": {
                                "total_reviews": 0,
                                "average_rating": 0.0,
                                "rating_distribution": {
                                    "1": 0,
                                    "2": 0,
                                    "3": 0,
                                    "4": 0,
                                    "5": 0
                                }
                            }
                        }

                    ratings = [row['rating'] for row in rows]
                    total_reviews = len(ratings)
                    average_rating = sum(ratings) / total_reviews if total_reviews > 0 else 0.0

                    # Calculate rating distribution
                    rating_distribution = {
                        "1": ratings.count(1),
                        "2": ratings.count(2),
                        "3": ratings.count(3),
                        "4": ratings.count(4),
                        "5": ratings.count(5)
                    }

                    return {
                        "EC": 0,
                        "EM": "Success",
                        "data": {
                            "total_reviews": total_reviews,
                            "average_rating": round(average_rating, 2),
                            "rating_distribution": rating_distribution
                        }
                    }

        except Exception as e:
            logger.error(f"Error getting review stats for package {package_id}: {str(e)}")
            return {
                "EC": 1,
                "EM": f"Error retrieving review stats: {str(e)}",
                "data": None
            }


# Dependency function
def get_review_service() -> ReviewService:
    """
    Dependency function to get ReviewService instance

    Returns:
        ReviewService instance
    """
    return ReviewService()
