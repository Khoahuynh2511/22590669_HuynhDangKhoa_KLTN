"""
Admin Train Management Endpoints
"""
from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional, Dict, Any

from ...services.admin_train_service import get_admin_train_service, AdminTrainService
from ...core.dependencies import get_current_admin

router = APIRouter()


@router.get("")
async def get_all_trains(
    limit: Optional[int] = Query(None, ge=1),
    offset: Optional[int] = Query(None, ge=0),
    status: Optional[str] = Query(None),
    train_type_id: Optional[str] = Query(None),
    departure_station: Optional[str] = Query(None),
    arrival_station: Optional[str] = Query(None),
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminTrainService = Depends(get_admin_train_service)
):
    """Lấy danh sách chuyến tàu (admin)"""
    result = service.get_all_trains(
        limit=limit, offset=offset, status=status,
        train_type_id=train_type_id, departure_station=departure_station,
        arrival_station=arrival_station)
    if result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result


@router.post("")
async def create_train(
    train_data: Dict[str, Any],
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminTrainService = Depends(get_admin_train_service)
):
    """Tạo chuyến tàu mới"""
    result = service.create_train(train_data)
    if result["EC"] != 0:
        raise HTTPException(status_code=400, detail=result["EM"])
    return result


@router.post("/csv")
async def create_trains_from_csv(
    body: Dict[str, Any],
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminTrainService = Depends(get_admin_train_service)
):
    """Tạo nhiều chuyến tàu từ CSV"""
    csv_text = body.get("csv_text", "")
    if not csv_text:
        raise HTTPException(status_code=400, detail="Thiếu dữ liệu CSV")
    result = service.create_trains_from_csv(csv_text)
    return result


@router.get("/stations")
async def get_train_stations(
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminTrainService = Depends(get_admin_train_service)
):
    """Lấy danh sách ga tàu"""
    result = service.get_train_stations()
    if result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result


@router.get("/types")
async def get_train_types(
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminTrainService = Depends(get_admin_train_service)
):
    """Lấy danh sách loại tàu"""
    result = service.get_train_types()
    if result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result


@router.get("/{train_id}")
async def get_train_by_id(
    train_id: str,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminTrainService = Depends(get_admin_train_service)
):
    """Lấy chi tiết chuyến tàu"""
    result = service.get_train_by_id(train_id)
    if result["EC"] == 1:
        raise HTTPException(status_code=404, detail=result["EM"])
    elif result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result


@router.put("/{train_id}")
async def update_train(
    train_id: str,
    update_data: Dict[str, Any],
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminTrainService = Depends(get_admin_train_service)
):
    """Cập nhật chuyến tàu"""
    result = service.update_train(train_id, update_data)
    if result["EC"] == 1:
        raise HTTPException(status_code=404, detail=result["EM"])
    elif result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result


@router.delete("/{train_id}")
async def delete_train(
    train_id: str,
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminTrainService = Depends(get_admin_train_service)
):
    """Xóa chuyến tàu (soft delete)"""
    result = service.delete_train(train_id)
    if result["EC"] == 1:
        raise HTTPException(status_code=404, detail=result["EM"])
    elif result["EC"] != 0:
        raise HTTPException(status_code=500, detail=result["EM"])
    return result


@router.patch("/{train_id}/status")
async def update_train_status(
    train_id: str,
    status_data: Dict[str, Any],
    current_admin: Dict[str, Any] = Depends(get_current_admin),
    service: AdminTrainService = Depends(get_admin_train_service)
):
    """Cập nhật trạng thái chuyến tàu"""
    status = status_data.get("status")
    if not status:
        raise HTTPException(status_code=400, detail="Thiếu trạng thái")
    result = service.update_train_status(train_id, status)
    if result["EC"] != 0:
        raise HTTPException(status_code=400 if result["EC"] == 1 else 500, detail=result["EM"])
    return result
