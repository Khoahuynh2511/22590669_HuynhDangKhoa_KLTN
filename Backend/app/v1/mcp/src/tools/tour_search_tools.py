"""
MCP Tools - Tour Package Search
Search tour packages using semantic vector search with embeddings
"""
from pydantic import ValidationError
from fastmcp import FastMCP
from typing import Optional, Dict, Any, List
import logging
import numpy as np
import os
import unicodedata
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from langchain_openai import OpenAIEmbeddings
from supabase import create_client
from ..core.config import settings
from ..schema import SearchTourPackagesInput
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _remove_diacritics(text: str) -> str:
    """Remove Vietnamese diacritics for search matching.
    E.g. 'Đà Lạt' -> 'Da Lat', 'Bến Tre' -> 'Ben Tre'
    """
    if not text:
        return ""
    # Normalize to NFD, then remove combining characters (diacritics)
    normalized = unicodedata.normalize('NFD', text)
    stripped = re.sub(r'[̀-ͯˀ-˟]', '', normalized)
    # Also handle đ/Đ -> d/D specifically (not covered by NFD)
    stripped = stripped.replace('đ', 'd').replace('Đ', 'D')
    return stripped.strip()


def _is_supabase_connection_error(error: Exception) -> bool:
    message = str(error).lower()
    return any(
        token in message
        for token in (
            'getaddrinfo failed',
            'connecterror',
            'connection refused',
            'name or service not known',
        )
    )


# Supabase connection - use settings or env vars
SUPABASE_URL = os.getenv("SUPABASE_URL") or settings.SUPABASE_URL
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or settings.SUPABASE_KEY
DATABASE_URL = os.getenv("DATABASE_URL", "")

KNOWN_DESTINATIONS = [
    "Đà Lạt", "Hội An", "Nha Trang", "Đà Nẵng", "Phú Quốc", "Sapa", "Huế", "Vũng Tàu",
]


def _to_float(value, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return default


def _normalize_destination_for_search(text: str) -> str:
    if not text:
        return text
    cleaned = re.sub(r"\s+\d+\s*ngày\s*$", "", text.strip(), flags=re.IGNORECASE)
    cleaned = _remove_diacritics(cleaned.lower())
    for known in KNOWN_DESTINATIONS:
        known_clean = _remove_diacritics(known.lower())
        if known_clean in cleaned or cleaned in known_clean:
            return known
    return text.strip()


def _destination_matches_tour(query: str, destination: str) -> bool:
    if not query or not destination:
        return False
    query_norm = _normalize_destination_for_search(query)
    query_lower = query_norm.lower().strip()
    dest_lower = (destination or "").lower().strip()
    query_clean = _remove_diacritics(query_lower)
    dest_clean = _remove_diacritics(dest_lower)
    return (
        query_lower in dest_lower
        or dest_lower in query_lower
        or query_clean in dest_clean
        or dest_clean in query_clean
    )


def _postgres_db_url() -> str:
    return DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgres+asyncpg://", "postgresql://"
    )


class TourPackageSearchService:
    """
    Service for hybrid search of tour packages.

    Data source priority:
    1. Render PostgreSQL (DATABASE_URL) - primary
    2. Supabase - fallback when Render is unavailable or returns no results
    """

    def __init__(self):
        """Initialize tour package search service"""
        try:
            self.embeddings = OpenAIEmbeddings(
                api_key=settings.OPENAI_API_KEY,
                model="text-embedding-3-small"
            )
            logger.info("OpenAI embeddings initialized")
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            self.embeddings = None

        if SUPABASE_URL and SUPABASE_KEY:
            try:
                self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
                logger.info("Supabase client initialized (fallback)")
            except Exception as e:
                logger.warning(f"Supabase fallback unavailable: {e}")
                self.supabase = None
        else:
            self.supabase = None

        db_url = _postgres_db_url()
        if db_url:
            logger.info("Render PostgreSQL configured as primary data source")
        else:
            logger.warning("DATABASE_URL not configured; will rely on Supabase if available")

        logger.info("TourPackageSearchService initialized")

    def _search_tours_postgres(
        self,
        query: str,
        filters: Optional[Dict] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """Primary keyword search via Render PostgreSQL (DATABASE_URL)."""
        db_url = _postgres_db_url()
        if not db_url:
            logger.warning("DATABASE_URL not configured for Render PostgreSQL tour search")
            return []

        filters = filters or {}
        query = (query or "").strip()
        destination_filter = filters.get("destination")
        if destination_filter:
            query = _normalize_destination_for_search(destination_filter)
        elif query:
            query = _normalize_destination_for_search(query)

        try:
            conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute(
                """
                SELECT package_id, package_name, description, destination, duration_days,
                       price, available_slots, start_date, end_date, image_urls,
                       is_active
                FROM tour_packages
                WHERE is_active = TRUE AND available_slots > 0
                ORDER BY price ASC
                """
            )
            rows = cur.fetchall()
            cur.close()
            conn.close()
        except Exception as exc:
            logger.error(f"Postgres tour search failed: {exc}")
            return []

        results: List[Dict] = []
        query_lower = query.lower()
        query_clean = _remove_diacritics(query_lower)

        for row in rows:
            pkg = dict(row)
            pkg["price"] = _to_float(pkg.get("price"))
            name = (pkg.get("package_name") or "").lower()
            desc = (pkg.get("description") or "").lower()
            name_clean = _remove_diacritics(name)
            desc_clean = _remove_diacritics(desc)

            matched = False
            score = 0.0
            if query:
                if query_lower in name or query_clean in name_clean:
                    matched = True
                    score = max(score, 0.9)
                if _destination_matches_tour(query, pkg.get("destination") or ""):
                    matched = True
                    score = max(score, 1.0)
                if query_lower in desc or query_clean in desc_clean:
                    matched = True
                    score = max(score, 0.5)
            else:
                matched = True
                score = 0.3

            if not matched:
                continue

            if filters.get("max_price") is not None:
                if pkg["price"] > _to_float(filters["max_price"]):
                    continue
            if filters.get("min_price") is not None:
                if pkg["price"] < _to_float(filters["min_price"]):
                    continue
            if filters.get("duration") is not None:
                if int(pkg.get("duration_days") or 0) != int(filters["duration"]):
                    continue
            if destination_filter and not _destination_matches_tour(
                destination_filter, pkg.get("destination") or ""
            ):
                continue

            pkg["keyword_score"] = score
            results.append(pkg)

        results.sort(key=lambda item: item.get("keyword_score", 0), reverse=True)
        logger.info(f"Render PostgreSQL found {len(results[:limit])} tour packages for '{query}'")
        return results[:limit]

    def _search_tours_by_vector_postgres(
        self,
        query_embedding: List[float],
        filters: Optional[Dict] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """Primary vector search via Render PostgreSQL (package_embeddings)."""
        db_url = _postgres_db_url()
        if not db_url:
            return []

        filters = filters or {}
        try:
            conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute(
                """
                SELECT tp.*, pe.embedding
                FROM tour_packages tp
                INNER JOIN package_embeddings pe ON pe.package_id = tp.package_id
                WHERE tp.is_active = TRUE AND tp.available_slots > 0
                """
            )
            rows = cur.fetchall()
            cur.close()
            conn.close()
        except Exception as exc:
            logger.warning(f"Render PostgreSQL vector search unavailable: {exc}")
            return []

        query_vec = np.array(query_embedding)
        results: List[Dict] = []

        for row in rows:
            pkg = dict(row)
            embedding_raw = pkg.pop("embedding", None)
            if embedding_raw is None:
                continue
            try:
                if isinstance(embedding_raw, str):
                    pkg_emb = [float(x) for x in embedding_raw.strip("[]").split(",")]
                else:
                    pkg_emb = embedding_raw
                pkg_vec = np.array(pkg_emb)
            except Exception:
                continue

            similarity = float(
                np.dot(query_vec, pkg_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(pkg_vec))
            )
            if similarity <= 0.3:
                continue

            pkg["price"] = _to_float(pkg.get("price"))
            pkg["similarity_score"] = similarity
            results.append(pkg)

        if filters:
            results = self._apply_filters(results, filters)

        results.sort(key=lambda item: item.get("similarity_score", 0), reverse=True)
        logger.info(f"Render PostgreSQL vector search found {len(results[:limit])} packages")
        return results[:limit]

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector from text"""
        if not self.embeddings:
            raise ValueError("Embeddings not initialized")

        try:
            embedding = self.embeddings.embed_query(text)
            logger.debug(f"Generated embedding for query: {text[:50]}...")
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise

    def _search_tours_by_vector_supabase(
        self,
        query_embedding: List[float],
        filters: Optional[Dict] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Fallback vector search via Supabase pgvector.
        """
        if not self.supabase:
            return []

        try:
            logger.info(f"Supabase vector search fallback (limit: {limit})")

            # Build base query with filters applied at database level
            base_query = self.supabase.table("tour_packages").select("*")

            # Apply filters at database level
            if filters:
                base_query = self._apply_database_filters(base_query, filters)

            # Use RPC call to match_packages function (uses pgvector <=> operator)
            # This is much faster than loading all embeddings into Python
            try:
                # Convert embedding to PostgreSQL vector format: '[1,2,3]' as string
                embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'

                # Call the match_packages function via RPC
                # Note: Supabase RPC expects vector as string representation
                rpc_result = self.supabase.rpc(
                    'match_packages',
                    {
                        'query_embedding': embedding_str,
                        'match_threshold': 0.3,
                        'match_count': limit * 3  # Get more to account for filters
                    }
                ).execute()

                if rpc_result.data:
                    # Get package_ids from RPC result
                    matched_package_ids = [item['package_id'] for item in rpc_result.data]

                    # Fetch full package details for matched IDs
                    # Apply filters again if needed (some filters might not be in RPC)
                    query = base_query.in_('package_id', matched_package_ids)
                    result = query.execute()

                    if result.data:
                        # Map similarity scores from RPC result
                        similarity_map = {item['package_id']: item.get('similarity', 0.0)
                                          for item in rpc_result.data}

                        packages = []
                        for pkg in result.data:
                            pkg_id = pkg.get('package_id')
                            if pkg_id in similarity_map:
                                pkg['similarity_score'] = similarity_map[pkg_id]
                                packages.append(pkg)

                        # Sort by similarity and limit
                        packages.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
                        packages = packages[:limit]

                        logger.info(f"✅ Native vector search found {len(packages)} packages")
                        return packages
            except Exception as rpc_error:
                logger.warning(f"⚠️ RPC match_packages failed, falling back to direct query: {rpc_error}")
                # Fallback: Use direct SQL query if RPC not available
                # This requires raw SQL execution which Supabase Python client doesn't support well
                # So we'll use a workaround: get filtered packages first, then calculate similarity
                pass

            # Fallback: Get filtered packages and calculate similarity in Python (slower but works)
            logger.info("⚠️ Using fallback vector search (slower)")
            filtered_result = base_query.execute()

            if not filtered_result.data:
                logger.info("No packages match filters")
                return []

            # Get embeddings for filtered packages
            package_ids = [pkg['package_id'] for pkg in filtered_result.data]
            embeddings_result = self.supabase.table("package_embeddings").select(
                "package_id, embedding").in_("package_id", package_ids).execute()

            if not embeddings_result.data:
                logger.warning("No embeddings found for filtered packages")
                return []

            # Calculate similarity for filtered packages
            results = []
            query_vec = np.array(query_embedding)

            embedding_map = {}
            for emb_data in embeddings_result.data:
                pkg_id = emb_data['package_id']
                pkg_emb_raw = emb_data['embedding']
                try:
                    if isinstance(pkg_emb_raw, str):
                        pkg_emb = [float(x) for x in pkg_emb_raw.strip('[]').split(',')]
                    else:
                        pkg_emb = pkg_emb_raw
                    embedding_map[pkg_id] = np.array(pkg_emb)
                except Exception as e:
                    logger.warning(f"⚠️ Error parsing embedding for {pkg_id}: {e}")
                    continue

            # Calculate similarity and combine with package data
            for pkg in filtered_result.data:
                pkg_id = pkg.get('package_id')
                if pkg_id in embedding_map:
                    pkg_vec = embedding_map[pkg_id]
                    similarity = np.dot(query_vec, pkg_vec) / (
                        np.linalg.norm(query_vec) * np.linalg.norm(pkg_vec)
                    )
                    if similarity > 0.3:
                        pkg_copy = pkg.copy()
                        pkg_copy['similarity_score'] = float(similarity)
                        results.append(pkg_copy)

            # Sort by similarity
            results.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
            results = results[:limit]

            logger.info(f"✅ Fallback vector search found {len(results)} packages")
            return results

        except Exception as e:
            if _is_supabase_connection_error(e):
                logger.warning(f"Supabase unavailable for vector search: {e}")
            else:
                logger.error(f"Vector search error: {e}")
                import traceback
                logger.error(traceback.format_exc())
            return []

    def _search_tours_by_vector(
        self,
        query_embedding: List[float],
        filters: Optional[Dict] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """Primary: Render PostgreSQL vector. Fallback: Supabase."""
        results = self._search_tours_by_vector_postgres(query_embedding, filters, limit)
        if results:
            return results
        if self.supabase:
            logger.info("Render vector search empty, falling back to Supabase")
            return self._search_tours_by_vector_supabase(query_embedding, filters, limit)
        return []

    def _search_tours_by_keyword_supabase(
        self,
        query: str,
        filters: Optional[Dict] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Fallback keyword search via Supabase."""
        if not self.supabase:
            return []

        try:
            logger.info(f"Supabase keyword search fallback: '{query[:50]}...' (limit: {limit})")

            # Helper function to build base query with filters (need fresh query for each field)
            def build_base_query():
                query_builder = self.supabase.table("tour_packages").select("*")

                # Apply filters at database level
                if filters:
                    query_builder = self._apply_database_filters(query_builder, filters)

                # Add active filter
                query_builder = query_builder.eq("is_active", True)

                return query_builder

            # Try to use full-text search if search_vector column exists
            # Otherwise, use LIKE queries as fallback
            try:
                query_lower = query.lower()

                # Search in package_name, destination, description using multiple queries
                # Supabase doesn't support complex OR in single query, so we'll search each field
                results_by_field = []
                supabase_unreachable = False

                # Search package_name (highest priority) - BUILD FRESH QUERY
                try:
                    name_query = build_base_query()
                    name_results = name_query.ilike('package_name', f'%{query}%').limit(limit * 2).execute()
                    if name_results.data:
                        results_by_field.extend(name_results.data)
                        logger.debug(f"Found {len(name_results.data)} packages in package_name")
                except Exception as e:
                    if _is_supabase_connection_error(e):
                        supabase_unreachable = True
                    else:
                        logger.warning(f"Search package_name failed: {e}")

                # Search destination - BUILD FRESH QUERY
                try:
                    dest_query = build_base_query()
                    dest_results = dest_query.ilike('destination', f'%{query}%').limit(limit * 2).execute()
                    if dest_results.data:
                        results_by_field.extend(dest_results.data)
                        logger.debug(f"Found {len(dest_results.data)} packages in destination")
                except Exception as e:
                    if _is_supabase_connection_error(e):
                        supabase_unreachable = True
                    else:
                        logger.warning(f"Search destination failed: {e}")

                # Search description - BUILD FRESH QUERY
                try:
                    desc_query = build_base_query()
                    desc_results = desc_query.ilike('description', f'%{query}%').limit(limit * 2).execute()
                    if desc_results.data:
                        results_by_field.extend(desc_results.data)
                        logger.debug(f"Found {len(desc_results.data)} packages in description")
                except Exception as e:
                    if _is_supabase_connection_error(e):
                        supabase_unreachable = True
                    else:
                        logger.warning(f"Search description failed: {e}")

                if supabase_unreachable and not results_by_field:
                    logger.warning("Supabase keyword search unreachable")
                    return []

                # Deduplicate by package_id
                seen_ids = set()
                unique_results = []
                for pkg in results_by_field:
                    pkg_id = pkg.get('package_id')
                    if pkg_id and pkg_id not in seen_ids:
                        seen_ids.add(pkg_id)
                        unique_results.append(pkg)

                if unique_results:
                    # Calculate keyword scores based on match position and field
                    scored_packages = []
                    for pkg in unique_results:
                        score = 0.0
                        pkg_name = (pkg.get('package_name') or '').lower()
                        destination = (pkg.get('destination') or '').lower()
                        description = (pkg.get('description') or '').lower()

                        # Higher weight for exact matches and name matches
                        if query_lower in pkg_name:
                            if pkg_name.startswith(query_lower):
                                score += 1.0  # Starts with query
                            else:
                                score += 0.8  # Contains query

                        if query_lower in destination:
                            if destination.startswith(query_lower):
                                score += 0.6
                            else:
                                score += 0.4

                        if query_lower in description:
                            score += 0.2

                        if score > 0:
                            pkg_copy = pkg.copy()
                            pkg_copy['keyword_score'] = score
                            scored_packages.append(pkg_copy)

                    # Sort by keyword score
                    scored_packages.sort(key=lambda x: x.get('keyword_score', 0), reverse=True)
                    scored_packages = scored_packages[:limit]

                    logger.info(f"Supabase keyword search found {len(scored_packages)} packages")
                    return scored_packages

                logger.info("Supabase keyword search returned no packages")
                return []

            except Exception as e:
                logger.warning(f"Supabase keyword search error: {e}")
                return []

        except Exception as e:
            logger.error(f"Supabase keyword search error: {str(e)}")
            return []

    def _search_tours_by_keyword(
        self,
        query: str,
        filters: Optional[Dict] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """Primary: Render PostgreSQL keyword. Fallback: Supabase."""
        logger.info(f"Keyword search: '{query[:50]}...' (limit: {limit})")
        results = self._search_tours_postgres(query, filters, limit)
        if results:
            return results
        if self.supabase:
            logger.info("Render PostgreSQL keyword empty, falling back to Supabase")
            return self._search_tours_by_keyword_supabase(query, filters, limit)
        return []

    def _apply_database_filters(self, query, filters: Dict):
        """
        Apply filters at database level for better performance

        Returns modified query builder
        """
        if not filters:
            return query

        if filters.get("max_price"):
            max_price = float(filters["max_price"])
            query = query.lte("price", max_price)

        if filters.get("min_price"):
            min_price = float(filters["min_price"])
            query = query.gte("price", min_price)

        if filters.get("duration"):
            duration = int(filters["duration"])
            query = query.eq("duration_days", duration)

        if filters.get("destination"):
            destination = filters["destination"]
            # Normalize diacritics: match both 'Da Lat' and 'u0110u00e0 Lu1ea1t'
            destination_ascii = _remove_diacritics(destination)
            if destination_ascii.lower() != destination.lower():
                # Input has no diacritics or differs from stripped form - search both
                query = query.or_(f"destination.ilike.%{destination}%,destination.ilike.%{destination_ascii}%")
            else:
                query = query.ilike("destination", f"%{destination}%")

        # Always filter active packages
        query = query.eq("is_active", True)

        # Filter available slots > 0
        query = query.gt("available_slots", 0)

        return query

    def _combine_search_results(
        self,
        semantic_results: List[Dict],
        keyword_results: List[Dict],
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        limit: int = 10
    ) -> List[Dict]:
        """
        Combine semantic and keyword search results with weighted scoring

        Args:
            semantic_results: Results from vector search with similarity_score
            keyword_results: Results from keyword search with keyword_score
            semantic_weight: Weight for semantic score (default 0.7)
            keyword_weight: Weight for keyword score (default 0.3)
            limit: Maximum number of results to return

        Returns:
            Combined and deduplicated results sorted by final_score
        """
        # Normalize scores to 0-1 range if needed
        def normalize_score(score: float, max_score: float) -> float:
            if max_score == 0:
                return 0.0
            return min(1.0, score / max_score)

        # Find max scores for normalization
        max_semantic = max([r.get('similarity_score', 0) for r in semantic_results], default=1.0)
        max_keyword = max([r.get('keyword_score', 0) for r in keyword_results], default=1.0)

        # Create a map of package_id -> best result
        combined_map = {}

        # Add semantic results
        for pkg in semantic_results:
            pkg_id = pkg.get('package_id')
            if not pkg_id:
                continue

            normalized_semantic = normalize_score(pkg.get('similarity_score', 0), max_semantic)
            final_score = normalized_semantic * semantic_weight

            if pkg_id not in combined_map:
                pkg_copy = pkg.copy()
                pkg_copy['final_score'] = final_score
                pkg_copy['semantic_score'] = normalized_semantic
                pkg_copy['keyword_score'] = 0.0
                combined_map[pkg_id] = pkg_copy
            else:
                # Update if this semantic score is better
                existing = combined_map[pkg_id]
                if normalized_semantic > existing.get('semantic_score', 0):
                    existing['semantic_score'] = normalized_semantic
                    existing['final_score'] = normalized_semantic * semantic_weight + \
                        existing.get('keyword_score', 0) * keyword_weight

        # Add keyword results
        for pkg in keyword_results:
            pkg_id = pkg.get('package_id')
            if not pkg_id:
                continue

            normalized_keyword = normalize_score(pkg.get('keyword_score', 0), max_keyword)

            if pkg_id not in combined_map:
                pkg_copy = pkg.copy()
                pkg_copy['final_score'] = normalized_keyword * keyword_weight
                pkg_copy['semantic_score'] = 0.0
                pkg_copy['keyword_score'] = normalized_keyword
                combined_map[pkg_id] = pkg_copy
            else:
                # Add keyword score to existing result
                existing = combined_map[pkg_id]
                existing['keyword_score'] = normalized_keyword
                existing['final_score'] = (
                    existing.get('semantic_score', 0) * semantic_weight +
                    normalized_keyword * keyword_weight
                )

        # Convert to list and sort by final_score
        combined_results = list(combined_map.values())
        combined_results.sort(key=lambda x: x.get('final_score', 0), reverse=True)

        # Limit results
        combined_results = combined_results[:limit]

        logger.info(
            f"✅ Combined {
                len(semantic_results)} semantic + {
                len(keyword_results)} keyword = {
                len(combined_results)} unique results")

        return combined_results

    def _apply_filters(self, tours: List[Dict], filters: Dict) -> List[Dict]:
        """
        Apply additional filters to search results (fallback for post-processing)

        Note: Prefer _apply_database_filters() for better performance
        """
        filtered = tours.copy()

        if filters.get("max_price"):
            max_price = _to_float(filters["max_price"])
            before = len(filtered)
            filtered = [t for t in filtered if _to_float(t.get("price")) <= max_price]
            logger.debug(f"Price filter ({max_price}): {before} -> {len(filtered)}")

        if filters.get("duration"):
            duration = int(filters["duration"])
            before = len(filtered)
            filtered = [t for t in filtered if int(t.get("duration_days") or 0) == duration]
            logger.debug(f"Duration filter ({duration}): {before} -> {len(filtered)}")

        if filters.get("destination"):
            destination = filters["destination"]
            before = len(filtered)
            filtered = [
                t for t in filtered
                if _destination_matches_tour(destination, t.get("destination", ""))
            ]
            logger.debug(f"Destination filter ({destination}): {before} -> {len(filtered)}")

        return filtered

    async def search_tour_packages(
        self,
        user_message: str,
        filters: Optional[Dict] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Hybrid search: Combines semantic vector search + keyword search + filters

        Args:
            user_message: User query (e.g., "Tôi muốn đi Đà Lạt")
            filters: Optional filters (price, duration, destination) - applied at DB level
            limit: Number of results

        Returns:
            List of tour packages with final_score (weighted combination of semantic + keyword)
        """
        try:
            logger.info(f"🔍 Hybrid search request: '{user_message[:100]}...' (limit: {limit})")

            # Step 1: Generate embedding for semantic search
            embedding = self._generate_embedding(user_message)

            # Step 2: Semantic search (Render PostgreSQL first, Supabase fallback)
            semantic_results = self._search_tours_by_vector(
                query_embedding=embedding,
                filters=filters,
                limit=limit * 2
            )

            # Step 3: Keyword search (Render PostgreSQL first, Supabase fallback)
            if filters and filters.get("destination"):
                keyword_query = _normalize_destination_for_search(filters["destination"])
            else:
                keyword_query = _normalize_destination_for_search(user_message)
            keyword_results = self._search_tours_by_keyword(
                query=keyword_query,
                filters=filters,
                limit=limit * 2  # Get more for combination
            )

            # Step 4: Combine results with weighted scoring
            # Weight: 0.7 semantic + 0.3 keyword
            combined_results = self._combine_search_results(
                semantic_results=semantic_results,
                keyword_results=keyword_results,
                semantic_weight=0.7,
                keyword_weight=0.3,
                limit=limit
            )

            # Step 5: Ensure filters are applied (double-check, though they should be applied at DB level)
            if filters and combined_results:
                # This is a safety check - filters should already be applied at DB level
                filtered_results = self._apply_filters(combined_results, filters)
                if len(filtered_results) < len(combined_results):
                    logger.debug(f"Post-filtering: {len(combined_results)} -> {len(filtered_results)}")
                combined_results = filtered_results

            logger.info(f"Hybrid search completed: {len(combined_results)} packages found")
            logger.info(
                f"   - Semantic: {len(semantic_results)}, Keyword: {len(keyword_results)}, Combined: {len(combined_results)}"
            )

            return combined_results

        except Exception as e:
            logger.error(f"Hybrid search failed: {str(e)}")
            keyword_query = _normalize_destination_for_search(
                filters.get("destination") if filters and filters.get("destination") else user_message
            )
            results = self._search_tours_postgres(keyword_query, filters, limit)
            if results:
                return results
            if self.supabase:
                return self._search_tours_by_keyword_supabase(keyword_query, filters, limit)
            return []


# Singleton instance
tour_package_search_service = TourPackageSearchService()


def register_tour_search_tools(mcp: FastMCP):
    """Register tour package search tools for multi-agent system"""

    @mcp.tool()
    async def search_tour_packages(
        user_message: str,
        max_price: Optional[float] = None,
        duration: Optional[int] = None,
        destination: Optional[str] = None,
        limit: int = 2
    ) -> Dict[str, Any]:
        """
        Search for tour packages using hybrid search (semantic + keyword + filters).

        Data source priority:
        - Primary: Render PostgreSQL (DATABASE_URL)
        - Fallback: Supabase

        Uses:
        - Semantic search: pgvector on Render PostgreSQL, Supabase fallback
        - Keyword search: Render PostgreSQL, Supabase fallback
        - Filters: price, duration, destination
        - Scoring: Weighted combination (0.7 semantic + 0.3 keyword)

        Returns:
            Dict with found count and list of tour packages with:
            - found (int): Number of packages found
            - packages (list): Tour dictionaries with package_id, package_name, destination,
              price, duration_days, final_score, semantic_score, keyword_score,
              available_slots, start_date, image_urls
        """
        try:
            # Validate inputs
            validated = SearchTourPackagesInput(
                user_message=user_message,
                max_price=max_price,
                duration=duration,
                destination=destination,
                limit=limit
            )

            logger.info("📞 MCP Tool Call: search_tour_packages")
            logger.info(f"   Query: {validated.user_message[:100]}")

            # Build filters dict
            search_filters = {}
            if validated.max_price:
                search_filters["max_price"] = validated.max_price
            if validated.duration:
                search_filters["duration"] = validated.duration
            if validated.destination:
                search_filters["destination"] = validated.destination

            logger.info(f"   Filters: {search_filters if search_filters else 'None'}")
            logger.info(f"   Limit: {validated.limit}")

            # Hybrid search: semantic + keyword + filters
            packages = await tour_package_search_service.search_tour_packages(
                user_message=validated.user_message,
                filters=search_filters if search_filters else None,
                limit=validated.limit
            )

            result = {
                "found": len(packages),
                "packages": packages
            }

            logger.info(f"✅ search_tour_packages completed: {len(packages)} packages found")
            return result

        except ValidationError as e:
            return {
                "found": 0,
                "packages": [],
                "error": f"Input Validation Error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"❌ Error in search_tour_packages tool: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "found": 0,
                "packages": [],
                "error": str(e),
                "message": f"Error searching tour packages: {str(e)}"
            }

    logger.info("✅ Tour search tools registered")
