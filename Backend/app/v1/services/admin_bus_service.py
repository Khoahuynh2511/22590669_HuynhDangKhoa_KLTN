"""
Admin Bus Service - CRUD cho quản lý chuyến xe khách
"""
from typing import Dict, Any, Optional
from supabase import Client
import uuid


class AdminBusService:
    def __init__(self, supabase: Client):
        self.supabase = supabase

    def get_all_buses(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        status: Optional[str] = None,
        company_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Lấy danh sách chuyến xe"""
        try:
            query = self.supabase.table("buses").select("*", count="exact")

            if status:
                query = query.eq("status", status)
            if company_id:
                query = query.eq("company_id", company_id)
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)

            result = query.execute()

            return {
                "EC": 0,
                "EM": "Success",
                "data": {
                    "buses": result.data,
                    "total": result.count
                }
            }
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi server: {str(e)}", "data": None}

    def get_bus_by_id(self, bus_id: str) -> Dict[str, Any]:
        """Lấy chi tiết 1 chuyến xe"""
        try:
            result = self.supabase.table("buses").select("*").eq("bus_id", bus_id).execute()
            if not result.data:
                return {"EC": 1, "EM": "Không tìm thấy chuyến xe", "data": None}
            return {"EC": 0, "EM": "Success", "data": result.data[0]}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi server: {str(e)}", "data": None}

    def create_bus(self, bus_data: Dict[str, Any]) -> Dict[str, Any]:
        """Tạo chuyến xe mới"""
        try:
            # Generate bus_id if not provided
            if "bus_id" not in bus_data:
                bus_data["bus_id"] = f"BS-{uuid.uuid4().hex[:8].upper()}"

            result = self.supabase.table("buses").insert(bus_data).execute()
            return {"EC": 0, "EM": "Tạo chuyến xe thành công", "data": result.data[0]}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi tạo chuyến xe: {str(e)}", "data": None}

    def update_bus(self, bus_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cập nhật chuyến xe"""
        try:
            # Check exists
            existing = self.supabase.table("buses").select("bus_id").eq("bus_id", bus_id).execute()
            if not existing.data:
                return {"EC": 1, "EM": "Không tìm thấy chuyến xe", "data": None}

            result = self.supabase.table("buses").update(update_data).eq("bus_id", bus_id).execute()
            return {"EC": 0, "EM": "Cập nhật thành công", "data": result.data[0]}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi cập nhật: {str(e)}", "data": None}

    def delete_bus(self, bus_id: str) -> Dict[str, Any]:
        """Xóa chuyến xe (soft delete)"""
        try:
            existing = self.supabase.table("buses").select("bus_id").eq("bus_id", bus_id).execute()
            if not existing.data:
                return {"EC": 1, "EM": "Không tìm thấy chuyến xe", "data": None}

            self.supabase.table("buses").update({"is_active": False}).eq("bus_id", bus_id).execute()
            return {"EC": 0, "EM": "Xóa chuyến xe thành công", "data": None}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi xóa: {str(e)}", "data": None}

    def update_bus_status(self, bus_id: str, status: str) -> Dict[str, Any]:
        """Cập nhật trạng thái chuyến xe"""
        valid_statuses = ["scheduled", "boarding", "departed", "arrived", "cancelled"]
        if status not in valid_statuses:
            return {"EC": 1, "EM": f"Trạng thái không hợp lệ. Hợp lệ: {', '.join(valid_statuses)}", "data": None}

        try:
            existing = self.supabase.table("buses").select("bus_id").eq("bus_id", bus_id).execute()
            if not existing.data:
                return {"EC": 1, "EM": "Không tìm thấy chuyến xe", "data": None}

            result = self.supabase.table("buses").update({"status": status}).eq("bus_id", bus_id).execute()
            return {"EC": 0, "EM": "Cập nhật trạng thái thành công", "data": result.data[0]}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi cập nhật: {str(e)}", "data": None}

    def get_bus_companies(self) -> Dict[str, Any]:
        """Lấy danh sách hãng xe"""
        try:
            result = self.supabase.table("bus_companies").select("*").eq("is_active", True).execute()
            return {"EC": 0, "EM": "Success", "data": result.data}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi server: {str(e)}", "data": None}

    def get_bus_stations(self) -> Dict[str, Any]:
        """Lấy danh sách bến xe"""
        try:
            result = self.supabase.table("bus_stations").select("*").eq("is_active", True).execute()
            return {"EC": 0, "EM": "Success", "data": result.data}
        except Exception as e:
            return {"EC": 2, "EM": f"Lỗi server: {str(e)}", "data": None}


def get_admin_bus_service() -> AdminBusService:
    """Dependency to get AdminBusService instance"""
    from ..core.supabase import get_supabase_client
    supabase = get_supabase_client()
    return AdminBusService(supabase)
