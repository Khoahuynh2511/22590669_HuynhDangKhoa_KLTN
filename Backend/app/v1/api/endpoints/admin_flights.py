"""
Admin Flight Management Endpoints
"""
from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional, Dict, Any

from ...services.admin_flight_service import get_admin_flight_service, AdminFlightService
from ...core.dependencies import get_current_admin

router = APIRouter()


@router.get("")
async def get_all_flights(
    limit: Optional[int] = Query(None, ge=1),
    offset: Optional[int] = Query(None, ge=0),
    status: Optional[str] = Query(None),
    airline_id: Optional[str] = Query(None),
    departure_airport: Optional[str] = Query(None),
    arrival_airport: Optional[str] = Query(None),
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminFlightService = Depends(get_admin_flight_service)
):
    """Lấy danh sách chuyến bay (admin)"""
    result = service.get_all_flights(
        limit=limit, offset=offset, status=status,
        airline_id=airline_id, departure_airport=departure_airport,
        arrival_airport=arrival_airport)
    if result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result


@router.post("")
async def create_flight(
    flight_data: Dict[str, Any],
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminFlightService = Depends(get_admin_flight_service)
):
    """Tạo chuyến bay mới"""
    result = service.create_flight(flight_data)
    if result["EC"] != 0:
        raise HTTPException(status_code=400, detail=result["EM"])
    return result


@router.post("/csv")
async def create_flights_from_csv(
    body: Dict[str, Any],
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminFlightService = Depends(get_admin_flight_service)
):
    """Tạo nhiều chuyến bay từ CSV"""
    csv_text = body.get("csv_text", "")
    if not csv_text:
        raise HTTPException(status_code=400, detail="Thiếu dữ liệu CSV")
    result = service.create_flights_from_csv(csv_text)
    return result


@router.get("/airlines")
async def get_airlines(
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminFlightService = Depends(get_admin_flight_service)
):
    """Lấy danh sách hãng bay"""
    result = service.get_airlines()
    if result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result


@router.get("/airports")
async def get_airports(
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminFlightService = Depends(get_admin_flight_service)
):
    """Lấy danh sách sân bay"""
    result = service.get_airports()
    if result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result


@router.get("/{flight_id}")
async def get_flight_by_id(
    flight_id: str,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminFlightService = Depends(get_admin_flight_service)
):
    """Lấy chi tiết chuyến bay"""
    result = service.get_flight_by_id(flight_id)
    if result["EC"] == 1:
        raise HTTPException(status_code=404, detail=result["EM"])
    elif result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result


@router.put("/{flight_id}")
async def update_flight(
    flight_id: str,
    update_data: Dict[str, Any],
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminFlightService = Depends(get_admin_flight_service)
):
    """Cập nhật chuyến bay"""
    result = service.update_flight(flight_id, update_data)
    if result["EC"] == 1:
        raise HTTPException(status_code=404, detail=result["EM"])
    elif result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result


@router.delete("/{flight_id}")
async def delete_flight(
    flight_id: str,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminFlightService = Depends(get_admin_flight_service)
):
    """Xóa chuyến bay (soft delete)"""
    result = service.delete_flight(flight_id)
    if result["EC"] == 1:
        raise HTTPException(status_code=404, detail=result["EM"])
    elif result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result


@router.patch("/{flight_id}/status")
async def update_flight_status(
    flight_id: str,
    status_data: Dict[str, Any],
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminFlightService = Depends(get_admin_flight_service)
):
    """Cập nhật trạng thái chuyến bay"""
    status = status_data.get("status")
    if not status:
        raise HTTPException(status_code=400, detail="Thiếu trạng thái")
    result = service.update_flight_status(flight_id, status)
    if result["EC"] != 0:
        raise HTTPException(status_code=400 if result["EC"] == 1 else 500, detail=result["EM"])
    return result
