"""
Admin Hotel Service - CRUD cho quan ly khach san
Su dung psycopg2 truc tiep
"""
from typing import Dict, Any, Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import UploadFile
from app.v1.core.config import settings
from app.v1.core.cloudinary_config import CloudinaryConfig
import json
import logging


logger = logging.getLogger(__name__)


class AdminHotelService:
    def __init__(self):
        self.db_url = settings.DATABASE_URL

    def _get_conn(self):
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)

    def _normalize(self, rows):
        return [dict(r) for r in rows]

    def _to_json(self, val):
        """Convert lists/dicts to JSON strings for PostgreSQL"""
        if isinstance(val, list):
            return val  # psycopg2 handles Python lists for TEXT[] columns
        return val

    def get_all_hotels(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        search: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Lay danh sach khach san (admin)"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    sql = "SELECT * FROM hotels WHERE 1=1"
                    params = []

                    if search:
                        sql += " AND (hotel_name ILIKE %s OR location ILIKE %s)"
                        params.extend([f"%{search}%", f"%{search}%"])
                    if is_active is not None:
                        sql += " AND is_active = %s"
                        params.append(is_active)

                    # Count
                    count_sql = sql.replace("SELECT *", "SELECT COUNT(*) as cnt")
                    cur.execute(count_sql, params)
                    total = cur.fetchone()["cnt"]

                    sql += " ORDER BY created_at DESC"
                    if limit:
                        sql += " LIMIT %s"
                        params.append(limit)
                    if offset:
                        sql += " OFFSET %s"
                        params.append(offset)

                    cur.execute(sql, params)
                    hotels = self._normalize(cur.fetchall())

            return {
                "EC": 0,
                "EM": "Success",
                "data": {
                    "hotels": hotels,
                    "total": total
                }
            }
        except Exception as e:
            return {"EC": 2, "EM": f"Loi server: {str(e)}", "data": None}

    def get_hotel_by_id(self, hotel_id: str) -> Dict[str, Any]:
        """Lay chi tiet 1 khach san"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM hotels WHERE hotel_id = %s", (hotel_id,))
                    row = cur.fetchone()
            if not row:
                return {"EC": 1, "EM": "Khong tim thay khach san", "data": None}
            return {"EC": 0, "EM": "Success", "data": dict(row)}
        except Exception as e:
            return {"EC": 2, "EM": f"Loi server: {str(e)}", "data": None}

    def create_hotel(self, hotel_data: Dict[str, Any]) -> Dict[str, Any]:
        """Tao khach san moi"""
        try:
            columns = []
            values = []
            placeholders = []
            for key, val in hotel_data.items():
                columns.append(key)
                values.append(val)
                placeholders.append("%s")

            sql = f"INSERT INTO hotels ({', '.join(columns)}) VALUES ({', '.join(placeholders)}) RETURNING *"

            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, values)
                    new_hotel = dict(cur.fetchone())
            return {"EC": 0, "EM": "Tao khach san thanh cong", "data": new_hotel}
        except Exception as e:
            return {"EC": 2, "EM": f"Loi tao khach san: {str(e)}", "data": None}

    def update_hotel(self, hotel_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cap nhat khach san"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT hotel_id FROM hotels WHERE hotel_id = %s", (hotel_id,))
                    if not cur.fetchone():
                        return {"EC": 1, "EM": "Khong tim thay khach san", "data": None}

                    set_clause = ", ".join([f"{k} = %s" for k in update_data.keys()])
                    values = list(update_data.values()) + [hotel_id]

                    cur.execute(f"UPDATE hotels SET {set_clause} WHERE hotel_id = %s RETURNING *", values)
                    updated = dict(cur.fetchone())
            return {"EC": 0, "EM": "Cap nhat thanh cong", "data": updated}
        except Exception as e:
            return {"EC": 2, "EM": f"Loi cap nhat: {str(e)}", "data": None}

    def delete_hotel(self, hotel_id: str) -> Dict[str, Any]:
        """Xoa khach san (soft delete)"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT hotel_id FROM hotels WHERE hotel_id = %s", (hotel_id,))
                    if not cur.fetchone():
                        return {"EC": 1, "EM": "Khong tim thay khach san", "data": None}

                    cur.execute("UPDATE hotels SET is_active = FALSE WHERE hotel_id = %s", (hotel_id,))
            return {"EC": 0, "EM": "Xoa khach san thanh cong", "data": None}
        except Exception as e:
            return {"EC": 2, "EM": f"Loi xoa: {str(e)}", "data": None}

    def toggle_hotel_status(self, hotel_id: str, is_active: bool) -> Dict[str, Any]:
        """Bat/tat trang thai khach san"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT hotel_id FROM hotels WHERE hotel_id = %s", (hotel_id,))
                    if not cur.fetchone():
                        return {"EC": 1, "EM": "Khong tim thay khach san", "data": None}

                    cur.execute("UPDATE hotels SET is_active = %s WHERE hotel_id = %s RETURNING *", (is_active, hotel_id))
                    updated = dict(cur.fetchone())
            status_text = "kich hoat" if is_active else "vo hieu hoa"
            return {"EC": 0, "EM": f"Da {status_text} khach san", "data": updated}
        except Exception as e:
            return {"EC": 2, "EM": f"Loi cap nhat: {str(e)}", "data": None}

    async def upload_images(self, images: List[UploadFile]) -> List[str]:
        """
        Upload multiple images to Cloudinary

        Args:
            images: List of UploadFile objects

        Returns:
            List of uploaded image URLs
        """
        try:
            files_data = []

            for image in images:
                # Read file content
                content = await image.read()
                # Reset file pointer
                await image.seek(0)

                files_data.append((content, image.filename))

            # Upload to Cloudinary
            urls = CloudinaryConfig.upload_multiple_images(files_data, folder="hotels")

            logger.info(f"✓ Uploaded {len(urls)} images to Cloudinary")
            return urls

        except Exception as e:
            logger.error(f"✗ Error uploading images: {str(e)}")
            return []

    async def delete_images_from_urls(self, image_urls: str) -> int:
        """
        Delete images from Cloudinary using URLs

        Args:
            image_urls: Pipe-separated image URLs

        Returns:
            Number of successfully deleted images
        """
        try:
            if not image_urls:
                return 0

            urls = image_urls.split("|")
            public_ids = []

            for url in urls:
                public_id = CloudinaryConfig.extract_public_id_from_url(url.strip())
                if public_id:
                    public_ids.append(public_id)

            deleted_count = CloudinaryConfig.delete_multiple_images(public_ids)
            logger.info(f"✓ Deleted {deleted_count}/{len(public_ids)} images from Cloudinary")

            return deleted_count

        except Exception as e:
            logger.error(f"✗ Error deleting images: {str(e)}")
            return 0


    async def manage_images(
        self,
        hotel_id: str,
        images: List[UploadFile],
        replace_existing: bool = False
    ) -> Dict[str, Any]:
        """
        Quản lý ảnh khách sạn: thêm mới hoặc thay thế

        Args:
            hotel_id: ID khách sạn
            images: Danh sách file ảnh upload
            replace_existing: True = thay thế tất cả, False = thêm vào

        Returns:
            Dict với danh sách image_urls mới
        """
        try:
            # Kiểm tra khách sạn tồn tại
            hotel = self.get_hotel_by_id(hotel_id)
            if hotel["EC"] != 0:
                return hotel

            existing_urls = []
            if hotel["data"].get("image_urls"):
                existing_urls = [
                    u.strip() for u in hotel["data"]["image_urls"].split("|") if u.strip()
                ]

            # Nếu thay thế: xóa ảnh cũ trên Cloudinary
            if replace_existing and existing_urls:
                self.delete_images_from_urls(hotel["data"]["image_urls"])

            # Upload ảnh mới lên Cloudinary
            new_urls = await self.upload_images(images)
            if not new_urls:
                if replace_existing:
                    # Không upload được ảnh mới, cập nhật DB thành rỗng
                    self.update_hotel(hotel_id, {"image_urls": ""})
                    return {"EC": 0, "EM": "Xóa ảnh cũ thành công nhưng không upload được ảnh mới", "image_urls": []}
                return {"EC": 2, "EM": "Không thể upload ảnh", "image_urls": existing_urls}

            # Gộp URL
            if replace_existing:
                final_urls = new_urls
            else:
                final_urls = existing_urls + new_urls

            # Cập nhật DB
            image_urls_str = "|".join(final_urls)
            self.update_hotel(hotel_id, {"image_urls": image_urls_str})

            logger.info(f"Updated images for hotel {hotel_id}: {len(final_urls)} images (replace={replace_existing})")
            return {"EC": 0, "EM": "Cập nhật ảnh thành công", "image_urls": final_urls}

        except Exception as e:
            logger.error(f"✗ Error managing images: {str(e)}")
            return {"EC": 2, "EM": f"Lỗi quản lý ảnh: {str(e)}", "image_urls": []}

    def create_hotels_bulk(self, hotels_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Tao nhieu khach san cung luc tu danh sach dict
        """
        successful = 0
        failed = 0
        created_hotels = []
        errors = []

        for i, hotel_data in enumerate(hotels_data):
            try:
                # Parse amenities
                if 'amenities' in hotel_data and isinstance(hotel_data['amenities'], str):
                    amenities_str = hotel_data['amenities'].strip()
                    if amenities_str:
                        hotel_data['amenities'] = '{' + ','.join(
                            f'"{a.strip()}"' for a in amenities_str.split('|') if a.strip()
                        ) + '}'
                    else:
                        hotel_data['amenities'] = '{}'

                # Parse is_active
                if 'is_active' in hotel_data and isinstance(hotel_data['is_active'], str):
                    hotel_data['is_active'] = hotel_data['is_active'].lower() in ('true', '1', 'yes')

                # Parse numeric fields
                for field in ['star_rating', 'review_score', 'price', 'original_price']:
                    if field in hotel_data and hotel_data[field] is not None:
                        hotel_data[field] = float(hotel_data[field])
                for field in ['review_count', 'discount', 'available_rooms']:
                    if field in hotel_data and hotel_data[field] is not None:
                        hotel_data[field] = int(float(hotel_data[field]))

                # Remove None values
                hotel_data = {k: v for k, v in hotel_data.items() if v is not None}

                result = self.create_hotel(hotel_data)
                if result["EC"] == 0:
                    successful += 1
                    created_hotels.append(result["data"])
                else:
                    failed += 1
                    errors.append(f"Dòng {i + 1}: {result['EM']}")
            except Exception as e:
                failed += 1
                errors.append(f"Dòng {i + 1}: {str(e)}")

        return {
            "EC": 0,
            "EM": f"Đã xử lý {len(hotels_data)} khách sạn: {successful} thành công, {failed} thất bại",
            "data": {
                "total_processed": len(hotels_data),
                "successful": successful,
                "failed": failed,
                "created_hotels": created_hotels,
                "errors": errors
            }
        }


def get_admin_hotel_service() -> AdminHotelService:
    """Dependency to get AdminHotelService instance"""
    return AdminHotelService()
