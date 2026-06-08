"""
Travel News Service
Tim kiem va luu tru tin tuc/cam nang du lich bang Perplexity hoac Tavily Search API
"""
import logging
import asyncio
import concurrent.futures
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import math

from supabase import Client
from perplexity import Perplexity
from tavily import TavilyClient

from app.v1.core.config import settings
from app.v1.core.supabase import supabase_client

logger = logging.getLogger(__name__)


class TravelNewsService:
    """Service de tim kiem va luu tru tin tuc / cam nang du lich"""

    def __init__(self, supabase: Client):
        self.supabase = supabase
        self.perplexity_api_key = settings.PERPLEXITY_API_KEY
        self.tavily_api_key = settings.TAVILY_API_KEY
        self.search_provider = getattr(settings, "SEARCH_PROVIDER", "perplexity")  # perplexity | tavily
        self.search_queries = getattr(
            settings,
            "TRAVEL_NEWS_SEARCH_QUERIES",
            ["tin tuc du lich", "cam nang du lich"],
        )
        # Detailed prompt for Perplexity with preference for trending/new content
        self.detailed_search_prompt = """
        Tim kiem tin tuc va cam nang du lich LATEST va HOT nhat trong 2-4 tuan gan day.

        YEU CAU:
        1. UU TIEN TIN TUC MOI: Tim thong tin da xuat ban trong 7-30 ngay gan day (avoid tin cu)
        2. TRENDING TOPICS: Cac diem den HOT hien nay, promotions, seasonal events
        3. RELEVANT FOR VIETNAM: Du lich trong Viet Nam + cac diem den nuoc ngoai popular voi du khach Viet
        4. PRACTICAL INFO:
           - Huong dan du lich (visa, budget, best time to visit)
           - Updates ve dieu kien du lich (an toan, weather, restrictions)
           - Kham pha diem moi la
           - Festival/su kien du lich sap toi
           - Flight deals, tour promotions
        5. SOURCE QUALITY: Uu tien tu cac trang uy tin (tour operators, travel guides, news sites)
        6. RECENCY: Sap xep theo moi nhat truoc

        TRA VE TOP RESULTS: Ket qua moi nhat, most relevant, duoc verify tu cac nguon tin tuc
        """

    def _pg_conn(self):
        """Get PostgreSQL connection"""
        return psycopg2.connect(settings.DATABASE_URL, cursor_factory=RealDictCursor)

    def _run_perplexity_search_sync(self, query: str, use_detailed_prompt: bool = False):
        """Chay Perplexity Search (sync)"""
        client = Perplexity(api_key=self.perplexity_api_key)

        if use_detailed_prompt:
            enhanced_query = f"{self.detailed_search_prompt}\n\nSearch for: {query}"
        else:
            enhanced_query = query

        return client.search.create(
            query=enhanced_query,
            country="VN",
            max_results=20,
        )

    def _run_tavily_search_sync(self, query: str, use_detailed_prompt: bool = False) -> List[Dict[str, Any]]:
        """Chay Tavily Search (sync)"""
        client = TavilyClient(api_key=self.tavily_api_key)

        if use_detailed_prompt:
            enhanced_query = f"{query} - tin tuc du lich moi nhat Viet Nam trending"
        else:
            enhanced_query = query

        response = client.search(
            query=enhanced_query,
            search_depth="advanced",
            max_results=20,
            include_domains=None,
            exclude_domains=None,
        )

        return response.get("results", [])

    def _run_search_sync(self, query: str, use_detailed_prompt: bool = False):
        """Chay search voi provider duoc cau hinh (Perplexity hoac Tavily)"""
        if self.search_provider == "tavily" and self.tavily_api_key:
            return self._run_tavily_search_sync(query, use_detailed_prompt)
        elif self.perplexity_api_key:
            return self._run_perplexity_search_sync(query, use_detailed_prompt)
        else:
            logger.error("No search provider configured (need PERPLEXITY_API_KEY or TAVILY_API_KEY)")
            return None

    async def search_and_save_travel_news(self, use_detailed_prompt: bool = True) -> Dict[str, Any]:
        """
        Chay search cho cac query cau hinh va luu ket qua vao DB.
        Ho tro ca Perplexity va Tavily search providers.
        """
        # Check if any search provider is configured
        if self.search_provider == "tavily":
            if not self.tavily_api_key:
                error_msg = "TAVILY_API_KEY not configured"
                logger.error(error_msg)
                return {"success": False, "error": error_msg, "saved": 0}
        else:
            if not self.perplexity_api_key:
                error_msg = "PERPLEXITY_API_KEY not configured"
                logger.error(error_msg)
                return {"success": False, "error": error_msg, "saved": 0}

        saved_count = 0
        results_collected: List[Dict[str, Any]] = []

        try:
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                for query in self.search_queries:
                    try:
                        search_results = await loop.run_in_executor(
                            executor, self._run_search_sync, query, use_detailed_prompt
                        )

                        if not search_results:
                            logger.warning(f"No results returned for query: {query}")
                            continue

                        source_type = "guide" if "cam nang" in query.lower() else "news"

                        # Handle different response formats
                        if self.search_provider == "tavily" and self.tavily_api_key:
                            for item in search_results:
                                results_collected.append(
                                    {
                                        "title": item.get("title", ""),
                                        "url": item.get("url", ""),
                                        "snippet": item.get("content", ""),
                                        "date": item.get("published_date"),
                                        "last_updated": None,
                                        "source_type": source_type,
                                        "destination": None,
                                        "created_at": datetime.utcnow().isoformat(),
                                        "updated_at": datetime.utcnow().isoformat(),
                                    }
                                )
                        else:
                            if not getattr(search_results, "results", None):
                                logger.warning(f"No results in Perplexity response for query: {query}")
                                continue
                            for item in search_results.results:
                                results_collected.append(
                                    {
                                        "title": item.title,
                                        "url": item.url,
                                        "snippet": item.snippet,
                                        "date": getattr(item, "date", None),
                                        "last_updated": getattr(item, "last_updated", None),
                                        "source_type": source_type,
                                        "destination": None,
                                        "created_at": datetime.utcnow().isoformat(),
                                        "updated_at": datetime.utcnow().isoformat(),
                                    }
                                )
                    except Exception as e:
                        logger.error(f"Error searching query '{query}': {str(e)}")

            if results_collected:
                saved_count = self.save_news_urls(results_collected)

            return {"success": True, "saved": saved_count, "provider": self.search_provider}

        except Exception as e:
            logger.error(f"Error in search_and_save_travel_news: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e), "saved": saved_count}

    def save_news_urls(self, items: List[Dict[str, Any]]) -> int:
        """
        Luu batch URLs vao database, skip duplicates bang upsert theo URL.
        """
        if not items:
            return 0

        try:
            # Deduplicate items by URL - keep first occurrence
            seen_urls = set()
            deduplicated_items = []
            for item in items:
                url = item.get("url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    deduplicated_items.append(item)

            if not deduplicated_items:
                logger.warning("No unique URLs to save after deduplication")
                return 0

            logger.info(f"Saving {len(deduplicated_items)} unique URLs (deduplicated from {len(items)})")

            saved_count = 0
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    for item in deduplicated_items:
                        cur.execute(
                            """
                            INSERT INTO travel_news_urls (title, url, snippet, date, last_updated, source_type, destination, created_at, updated_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (url) DO UPDATE SET
                                title = EXCLUDED.title,
                                snippet = EXCLUDED.snippet,
                                date = EXCLUDED.date,
                                last_updated = EXCLUDED.last_updated,
                                source_type = EXCLUDED.source_type,
                                updated_at = EXCLUDED.updated_at
                            """,
                            (
                                item.get("title"),
                                item.get("url"),
                                item.get("snippet"),
                                item.get("date"),
                                item.get("last_updated"),
                                item.get("source_type"),
                                item.get("destination"),
                                item.get("created_at"),
                                item.get("updated_at"),
                            )
                        )
                        saved_count += 1
                    conn.commit()
            return saved_count
        except Exception as e:
            logger.error(f"Error saving travel news URLs: {str(e)}", exc_info=True)
            return 0

    def get_travel_news(
        self,
        page: int = 1,
        limit: int = 20,
        source_type: Optional[str] = None,
        destination: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Lay danh sach URLs da luu voi pagination (direct PostgreSQL).
        """
        offset = max(page - 1, 0) * limit

        try:
            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    # Build WHERE clauses
                    conditions = []
                    params = []

                    if source_type:
                        conditions.append("source_type = %s")
                        params.append(source_type)
                    if destination:
                        conditions.append("destination ILIKE %s")
                        params.append(f"%{destination}%")

                    where_clause = ""
                    if conditions:
                        where_clause = "WHERE " + " AND ".join(conditions)

                    # Get total count
                    cur.execute(
                        f"SELECT COUNT(*) as total FROM travel_news_urls {where_clause}",
                        params
                    )
                    total = cur.fetchone()["total"]

                    # Get paginated data
                    cur.execute(
                        f"""SELECT * FROM travel_news_urls {where_clause}
                            ORDER BY date DESC NULLS LAST, created_at DESC
                            LIMIT %s OFFSET %s""",
                        params + [limit, offset]
                    )
                    data = [dict(row) for row in cur.fetchall()]

            # Convert datetime objects to ISO strings for JSON serialization
            for row in data:
                for key, value in row.items():
                    if isinstance(value, datetime):
                        row[key] = value.isoformat()

            total_pages = math.ceil(total / limit) if limit > 0 else 0

            return {
                "success": True,
                "data": data,
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages,
            }

        except Exception as e:
            logger.error(f"Error fetching travel news: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "page": page,
                "limit": limit,
                "total": 0,
            }

    def search_travel_news(
        self,
        keywords: str,
        source_type: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Search travel news theo keywords trong title voi pagination.
        """
        offset = max(page - 1, 0) * limit

        try:
            keyword_list = [kw.strip() for kw in keywords.split() if kw.strip()]

            if not keyword_list:
                return {
                    "success": False,
                    "error": "Keywords cannot be empty",
                    "data": [],
                    "page": page,
                    "limit": limit,
                    "total": 0,
                    "total_pages": 0,
                }

            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    # Build WHERE clauses
                    conditions = []
                    params = []

                    # OR conditions for keyword matching in title
                    keyword_conditions = []
                    for kw in keyword_list:
                        keyword_conditions.append("title ILIKE %s")
                        params.append(f"%{kw}%")

                    conditions.append("(" + " OR ".join(keyword_conditions) + ")")

                    if source_type:
                        conditions.append("source_type = %s")
                        params.append(source_type)

                    where_clause = "WHERE " + " AND ".join(conditions)

                    # Get total count
                    cur.execute(
                        f"SELECT COUNT(*) as total FROM travel_news_urls {where_clause}",
                        params
                    )
                    total = cur.fetchone()["total"]
                    total_pages = math.ceil(total / limit) if limit > 0 else 0

                    # Get paginated data
                    cur.execute(
                        f"""SELECT * FROM travel_news_urls {where_clause}
                            ORDER BY created_at DESC
                            LIMIT %s OFFSET %s""",
                        params + [limit, offset]
                    )
                    data = [dict(row) for row in cur.fetchall()]

            # Convert datetime objects to ISO strings
            for row in data:
                for key, value in row.items():
                    if isinstance(value, datetime):
                        row[key] = value.isoformat()

            return {
                "success": True,
                "data": data,
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages,
            }

        except Exception as e:
            logger.error(f"Error searching travel news: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "page": page,
                "limit": limit,
                "total": 0,
                "total_pages": 0,
            }

    def get_today_travel_news(
        self,
        limit: int = 20,
        source_type: Optional[str] = None,
        destination: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Lay danh sach URLs cua ngay hom nay (created_at trong ngay hom nay).
        Neu ngay hom nay khong co du lieu, lay cua ngay hom qua.
        """
        try:
            today = datetime.now(timezone.utc).date()
            start_of_day = f"{today}T00:00:00+00:00"
            end_of_day = f"{today}T23:59:59+00:00"

            logger.info(f"Fetching travel news for today: {today}")

            with self._pg_conn() as conn:
                with conn.cursor() as cur:
                    # Build base conditions for today
                    conditions = ["created_at >= %s", "created_at <= %s"]
                    params: list = [start_of_day, end_of_day]

                    if source_type:
                        conditions.append("source_type = %s")
                        params.append(source_type)
                    if destination:
                        conditions.append("destination ILIKE %s")
                        params.append(f"%{destination}%")

                    where_clause = "WHERE " + " AND ".join(conditions)

                    # Check count for today
                    cur.execute(
                        f"SELECT COUNT(*) as total FROM travel_news_urls {where_clause}",
                        params
                    )
                    total = cur.fetchone()["total"]

                    if total > 0:
                        cur.execute(
                            f"""SELECT * FROM travel_news_urls {where_clause}
                                ORDER BY created_at DESC
                                LIMIT %s""",
                            params + [limit]
                        )
                        data = [dict(row) for row in cur.fetchall()]

                        for row in data:
                            for key, value in row.items():
                                if isinstance(value, datetime):
                                    row[key] = value.isoformat()

                        logger.info(f"Found {len(data)} travel news items for today (limited to {limit})")
                        return {
                            "success": True,
                            "data": data,
                            "limit": limit,
                            "total": total,
                            "date": str(today),
                            "source": "today",
                        }

                    # If today is empty, fetch yesterday's data
                    logger.info(f"No data for today ({today}), fetching yesterday's data...")
                    yesterday = today - timedelta(days=1)
                    yesterday_start = f"{yesterday}T00:00:00+00:00"
                    yesterday_end = f"{yesterday}T23:59:59+00:00"

                    conditions_y = ["created_at >= %s", "created_at <= %s"]
                    params_y: list = [yesterday_start, yesterday_end]

                    if source_type:
                        conditions_y.append("source_type = %s")
                        params_y.append(source_type)
                    if destination:
                        conditions_y.append("destination ILIKE %s")
                        params_y.append(f"%{destination}%")

                    where_clause_y = "WHERE " + " AND ".join(conditions_y)

                    cur.execute(
                        f"""SELECT * FROM travel_news_urls {where_clause_y}
                            ORDER BY created_at DESC
                            LIMIT %s""",
                        params_y + [limit]
                    )
                    data = [dict(row) for row in cur.fetchall()]

                    for row in data:
                        for key, value in row.items():
                            if isinstance(value, datetime):
                                row[key] = value.isoformat()

                    logger.info(f"Found {len(data)} travel news items for yesterday ({yesterday}) (limited to {limit})")
                    return {
                        "success": True,
                        "data": data,
                        "limit": limit,
                        "total": len(data),
                        "date": str(yesterday),
                        "source": "yesterday",
                    }

        except Exception as e:
            logger.error(f"Error fetching today's travel news: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "limit": limit,
                "total": 0,
            }


# Singleton instance
_travel_news_service: Optional[TravelNewsService] = None


def get_travel_news_service() -> TravelNewsService:
    """Get singleton TravelNewsService"""
    global _travel_news_service
    if _travel_news_service is None:
        _travel_news_service = TravelNewsService(supabase_client)
    return _travel_news_service
