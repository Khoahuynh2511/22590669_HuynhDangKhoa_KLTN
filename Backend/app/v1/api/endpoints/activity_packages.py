"""
Activity Packages API Endpoints
CRUD for activity packages (modular itinerary building blocks).
"""
import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List

from ...core.supabase import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def search_activities(
    destination: Optional[str] = Query(None, description="Filter by destination"),
    time_slot: Optional[str] = Query(None, description="Filter by time slot: morning, afternoon, evening"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(20, description="Max results"),
):
    """
    Search activity packages.
    Public endpoint - no auth required.
    """
    try:
        supabase = get_supabase_client()
        query = supabase.table("activity_packages").select("*").eq("is_active", True)

        if destination:
            query = query.ilike("destination", f"%{destination}%")
        if time_slot:
            query = query.eq("time_slot", time_slot)
        if category:
            query = query.eq("category", category)

        query = query.limit(limit).order("price", desc=False)
        result = query.execute()

        return {
            "EC": 0,
            "EM": "Success",
            "data": result.data if result.data else []
        }

    except Exception as e:
        logger.error(f"❌ Error searching activities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/destinations")
async def list_destinations():
    """List all available destinations that have activities."""
    try:
        supabase = get_supabase_client()
        result = supabase.table("activity_packages")\
            .select("destination")\
            .eq("is_active", True)\
            .execute()

        destinations = list(set(r["destination"] for r in (result.data or [])))
        destinations.sort()

        return {
            "EC": 0,
            "EM": "Success",
            "data": destinations
        }

    except Exception as e:
        logger.error(f"❌ Error listing destinations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{activity_id}")
async def get_activity(activity_id: str):
    """Get a single activity by ID."""
    try:
        supabase = get_supabase_client()
        result = supabase.table("activity_packages")\
            .select("*")\
            .eq("activity_id", activity_id)\
            .eq("is_active", True)\
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Activity not found")

        return {
            "EC": 0,
            "EM": "Success",
            "data": result.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))
