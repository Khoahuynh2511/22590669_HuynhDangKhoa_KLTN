"""
Admin Bus Management Endpoints
"""
from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional, Dict, Any

from ...services.admin_bus_service import get_admin_bus_service, AdminBusService
from ...core.dependencies import get_current_admin

router = APIRouter()


@router.get("")
async def get_all_buses(
    limit: Optional[int] = Query(None, ge=1),
    offset: Optional[int] = Query(None, ge=0),
    status: Optional[str] = Query(None),
    company_id: Optional[str] = Query(None),
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminBusService = Depends(get_admin_bus_service)
):
    """Lấy danh sách chuyến xe (admin)"""
    result = service.get_all_buses(limit=limit, offset=offset, status=status, company_id=company_id)
    if result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result


@router.post("")
async def create_bus(
    bus_data: Dict[str, Any],
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminBusService = Depends(get_admin_bus_service)
):
    """Tạo chuyến xe mới"""
    result = service.create_bus(bus_data)
    if result["EC"] != 0:
        raise HTTPException(status_code=400, detail=result["EM"])
    return result


@router.get("/companies")
async def get_bus_companies(
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminBusService = Depends(get_admin_bus_service)
):
    """Lấy danh sách hãng xe"""
    result = service.get_bus_companies()
    if result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result


@router.get("/stations")
async def get_bus_stations(
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminBusService = Depends(get_admin_bus_service)
):
    """Lấy danh sách bến xe"""
    result = service.get_bus_stations()
    if result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result


@router.get("/{bus_id}")
async def get_bus_by_id(
    bus_id: str,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminBusService = Depends(get_admin_bus_service)
):
    """Lấy chi tiết chuyến xe"""
    result = service.get_bus_by_id(bus_id)
    if result["EC"] == 1:
        raise HTTPException(status_code=404, detail=result["EM"])
    elif result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result


@router.put("/{bus_id}")
async def update_bus(
    bus_id: str,
    update_data: Dict[str, Any],
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminBusService = Depends(get_admin_bus_service)
):
    """Cập nhật chuyến xe"""
    result = service.update_bus(bus_id, update_data)
    if result["EC"] == 1:
        raise HTTPException(status_code=404, detail=result["EM"])
    elif result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result


@router.delete("/{bus_id}")
async def delete_bus(
    bus_id: str,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminBusService = Depends(get_admin_bus_service)
):
    """Xóa chuyến xe (soft delete)"""
    result = service.delete_bus(bus_id)
    if result["EC"] == 1:
        raise HTTPException(status_code=404, detail=result["EM"])
    elif result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result


@router.patch("/{bus_id}/status")
async def update_bus_status(
    bus_id: str,
    status_data: Dict[str, Any],
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminBusService = Depends(get_admin_bus_service)
):
    """Cập nhật trạng thái chuyến xe"""
    status = status_data.get("status")
    if not status:
        raise HTTPException(status_code=400, detail="Thiếu trạng thái")
    result = service.update_bus_status(bus_id, status)
    if result["EC"] != 0:
        raise HTTPException(status_code=400 if result["EC"] == 1 else 500, detail=result["EM"])
    return result
