"""
Activity Packages API Endpoints
CRUD for activity packages (modular itinerary building blocks).
"""
import logging
from fastapi import APIRouter, HTTPException, Query, Depends, Request
from typing import Optional, Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor
from ...core.dependencies import get_current_user, get_current_admin
from app.v1.services.trip_planning.trip_checkout_service import trip_checkout_service
from app.v1.services.trip_planning.activity_service import activity_service
from app.v1.services.admin_activity_service import get_admin_activity_service, AdminActivityService
from app.v1.schema.activity_package_schema import ActivityPackageCreate, ActivityPackageUpdate


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
        db_url = activity_service.db_url
        with psycopg2.connect(db_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = "SELECT * FROM activity_packages WHERE is_active = TRUE"
                params = []
                
                if destination:
                    query += " AND destination ILIKE %s"
                    params.append(f"%{destination}%")
                if time_slot:
                    query += " AND time_slot = %s"
                    params.append(time_slot)
                if category:
                    query += " AND category = %s"
                    params.append(category)
                    
                query += " ORDER BY price ASC LIMIT %s"
                params.append(limit)
                
                cur.execute(query, tuple(params))
                rows = cur.fetchall()
                
                for row in rows:
                    if row.get("price") is not None:
                        row["price"] = float(row["price"])
                    if row.get("duration_hours") is not None:
                        row["duration_hours"] = float(row["duration_hours"])
                
                return {
                    "EC": 0,
                    "EM": "Success",
                    "data": rows
                }

    except Exception as e:
        logger.error(f"❌ Error searching activities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/destinations")
async def list_destinations():
    """List all available destinations that have activities."""
    try:
        db_url = activity_service.db_url
        with psycopg2.connect(db_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT DISTINCT destination 
                    FROM activity_packages 
                    WHERE is_active = TRUE
                    ORDER BY destination ASC
                    """
                )
                rows = cur.fetchall()
                destinations = [r["destination"] for r in rows if r["destination"]]
                
                return {
                    "EC": 0,
                    "EM": "Success",
                    "data": destinations
                }

    except Exception as e:
        logger.error(f"❌ Error listing destinations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin")
async def get_all_activities_admin(
    limit: Optional[int] = Query(None, ge=1),
    offset: Optional[int] = Query(None, ge=0),
    destination: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    searchTerm: Optional[str] = Query(None),
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminActivityService = Depends(get_admin_activity_service)
):
    """Lấy toàn bộ danh sách hoạt động (Admin)"""
    result = service.get_all_activities(
        limit=limit, offset=offset, destination=destination,
        category=category, searchTerm=searchTerm
    )
    if result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result


@router.get("/{activity_id}")
async def get_activity(activity_id: str):
    """Get a single activity by ID."""
    try:
        db_url = activity_service.db_url
        with psycopg2.connect(db_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT * FROM activity_packages 
                    WHERE activity_id = %s AND is_active = TRUE
                    """,
                    (activity_id,)
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Activity not found")
                
                if row.get("price") is not None:
                    row["price"] = float(row["price"])
                if row.get("duration_hours") is not None:
                    row["duration_hours"] = float(row["duration_hours"])
                
                return {
                    "EC": 0,
                    "EM": "Success",
                    "data": row
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/checkout")
async def checkout_custom_itinerary(
    payload: Dict[str, Any],
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Checkout a manually designed itinerary of activity packages.
    """
    try:
        user_id = str(current_user["user_id"])
        
        # Calculate total price of activities
        itinerary = payload.get("itinerary") or {}
        duration_days = int(payload.get("duration_days") or 1)
        group_size = int(payload.get("group_size") or 1)
        destination = payload.get("destination") or "Unknown"
        travel_date = payload.get("travel_date") or None
        
        # Compute subtotal for activities
        subtotal = 0.0
        for day_key, slots in itinerary.items():
            if isinstance(slots, dict):
                for slot_key, activity in slots.items():
                    if isinstance(activity, list):
                        for act in activity:
                            if isinstance(act, dict):
                                subtotal += float(act.get("price") or 0)
                    elif activity and isinstance(activity, dict):
                        subtotal += float(activity.get("price") or 0)
                        
        total_activities_price = subtotal * group_size
        
        # Construct planning state mirroring TripPlanningState
        state = {
            "user_id": user_id,
            "destination": destination,
            "duration_days": duration_days,
            "group_size": group_size,
            "travel_date": travel_date,
            "group_type": payload.get("group_type", "couple"),
            "budget_level": payload.get("budget_level", "medium"),
            "confirmed_itinerary": itinerary,
            "itinerary_total_price": total_activities_price,
            "selected_flight": payload.get("selected_flight"),
            "selected_train": payload.get("selected_train")
        }
        
        ip_addr = request.client.host if request.client else "127.0.0.1"
        return_url = payload.get("return_url")
        
        checkout_res = await trip_checkout_service.create_checkout(
            state=state,
            ip_addr=ip_addr,
            return_url=return_url
        )
        
        if not checkout_res.get("success"):
            raise HTTPException(status_code=400, detail=checkout_res.get("error") or "Checkout failed")
            
        return {
            "EC": 0,
            "EM": "Success",
            "data": checkout_res
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in custom itinerary checkout: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Admin Management Endpoints
# ============================================================================


@router.post("/")
async def create_activity_admin(
    activity_data: ActivityPackageCreate,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminActivityService = Depends(get_admin_activity_service)
):
    """Tạo hoạt động mới (Admin)"""
    result = service.create_activity(activity_data.model_dump())
    if result["EC"] != 0:
        raise HTTPException(status_code=400, detail=result["EM"])
    return result


@router.put("/{activity_id}")
async def update_activity_admin(
    activity_id: str,
    update_data: ActivityPackageUpdate,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminActivityService = Depends(get_admin_activity_service)
):
    """Cập nhật hoạt động (Admin)"""
    result = service.update_activity(activity_id, update_data.model_dump(exclude_unset=True))
    if result["EC"] == 1:
        raise HTTPException(status_code=404, detail=result["EM"])
    elif result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result


@router.delete("/{activity_id}")
async def delete_activity_admin(
    activity_id: str,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminActivityService = Depends(get_admin_activity_service)
):
    """Xóa hoạt động (Admin - soft delete)"""
    result = service.delete_activity(activity_id)
    if result["EC"] == 1:
        raise HTTPException(status_code=404, detail=result["EM"])
    elif result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result

