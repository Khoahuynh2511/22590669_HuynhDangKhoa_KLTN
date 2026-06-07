"""
Chat Room Service - psycopg2 version
"""
import re
import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor

from app.v1.core.config import settings

logger = logging.getLogger(__name__)


class ChatRoomService:

    def __init__(self, supabase_client=None):
        pass

    def _conn(self):
        return psycopg2.connect(settings.DATABASE_URL, cursor_factory=RealDictCursor)

    def create_room(self, user_id, title=None):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO chat_rooms (user_id, title) VALUES (%s, %s) RETURNING room_id, user_id, title, created_at, updated_at",
                        (user_id, title or "New conversation"),
                    )
                    room = dict(cur.fetchone())
                    conn.commit()
            room = self._serialize_row(room)
            return {"EC": 0, "EM": "Chat room created successfully", "data": room}
        except Exception as e:
            logger.error(f"Error creating chat room: {e}")
            return {"EC": 1, "EM": f"Error creating chat room: {e}", "data": None}

    def get_user_rooms(self, user_id, archived=False, limit=50, offset=0):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT *, (SELECT COUNT(*) FROM chat_history ch WHERE ch.room_id = cr.room_id) as message_count FROM chat_rooms cr WHERE cr.user_id = %s ORDER BY cr.updated_at DESC LIMIT %s OFFSET %s",
                        (user_id, limit, offset),
                    )
                    rooms = [self._serialize_row(dict(r)) for r in cur.fetchall()]
                    cur.execute("SELECT COUNT(*) as cnt FROM chat_rooms WHERE user_id = %s", (user_id,))
                    total = cur.fetchone()["cnt"]
            return {"EC": 0, "EM": "Success", "data": rooms, "total": total}
        except Exception as e:
            logger.error(f"Error getting user rooms: {e}")
            return {"EC": 1, "EM": f"Error getting rooms: {e}", "data": [], "total": 0}

    def get_room_by_id(self, room_id, user_id):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT *, (SELECT COUNT(*) FROM chat_history ch WHERE ch.room_id = cr.room_id) as message_count FROM chat_rooms cr WHERE cr.room_id = %s AND cr.user_id = %s",
                        (room_id, user_id),
                    )
                    row = cur.fetchone()
            if not row:
                return {"EC": 404, "EM": "Chat room not found or access denied", "data": None}
            return {"EC": 0, "EM": "Success", "data": self._serialize_row(dict(row))}
        except Exception as e:
            logger.error(f"Error getting room: {e}")
            return {"EC": 1, "EM": f"Error getting room: {e}", "data": None}

    def update_room(self, room_id, user_id, title=None, is_archived=None):
        try:
            check = self.get_room_by_id(room_id, user_id)
            if check["EC"] != 0:
                return check
            sets = []
            params = []
            if title is not None:
                sets.append("title = %s")
                params.append(title)
            sets.append("updated_at = NOW()")
            params.extend([room_id, user_id])
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"UPDATE chat_rooms SET {', '.join(sets)} WHERE room_id = %s AND user_id = %s RETURNING *", params)
                    row = cur.fetchone()
                    conn.commit()
            if not row:
                return {"EC": 1, "EM": "Failed to update room", "data": None}
            return {"EC": 0, "EM": "Room updated successfully", "data": self._serialize_row(dict(row))}
        except Exception as e:
            logger.error(f"Error updating room: {e}")
            return {"EC": 1, "EM": f"Error updating room: {e}", "data": None}

    def delete_room(self, room_id, user_id):
        try:
            check = self.get_room_by_id(room_id, user_id)
            if check["EC"] != 0:
                return check
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM chat_history WHERE room_id = %s", (room_id,))
                    cur.execute("DELETE FROM chat_rooms WHERE room_id = %s AND user_id = %s", (room_id, user_id))
                    conn.commit()
            return {"EC": 0, "EM": "Room deleted successfully", "data": {"room_id": room_id}}
        except Exception as e:
            logger.error(f"Error deleting room: {e}")
            return {"EC": 1, "EM": f"Error deleting room: {e}", "data": None}

    def get_room_messages(self, room_id, user_id, limit=50, offset=0):
        try:
            check = self.get_room_by_id(room_id, user_id)
            if check["EC"] != 0:
                return {"EC": check["EC"], "EM": check["EM"], "data": [], "total": 0, "limit": limit, "offset": offset}
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) as cnt FROM chat_history WHERE room_id = %s", (room_id,))
                    total = cur.fetchone()["cnt"]
                    cur.execute(
                        """
                        SELECT
                            message_id,
                            room_id,
                            role,
                            content,
                            created_at,
                            ROW_NUMBER() OVER (ORDER BY created_at ASC, message_id ASC)::integer AS message_order,
                            metadata
                        FROM chat_history
                        WHERE room_id = %s
                        ORDER BY created_at ASC, message_id ASC
                        LIMIT %s OFFSET %s
                        """,
                        (room_id, limit, offset),
                    )
                    messages = [self._serialize_message_row(dict(r)) for r in cur.fetchall()]
            return {"EC": 0, "EM": "Success", "data": messages, "total": total, "limit": limit, "offset": offset}
        except Exception as e:
            logger.error(f"Error getting room messages: {e}")
            return {"EC": 1, "EM": f"Error getting messages: {e}", "data": [], "total": 0, "limit": limit, "offset": offset}

    def count_messages(self, room_id):
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) as cnt FROM chat_history WHERE room_id = %s", (room_id,))
                    return cur.fetchone()["cnt"]
        except Exception as e:
            logger.error(f"Error counting room messages: {e}")
            return 0

    def save_message(self, room_id, user_id, role, content, intent=None, entities=None, message_order=None):
        try:
            metadata = {}
            if intent:
                metadata["intent"] = intent
            if entities:
                metadata["entities"] = entities
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO chat_history (room_id, user_id, role, content, metadata) VALUES (%s, %s, %s, %s, %s) RETURNING *",
                        (room_id, user_id, role, content, json.dumps(metadata) if metadata else None),
                    )
                    msg = dict(cur.fetchone())
                    cur.execute("UPDATE chat_rooms SET updated_at = NOW() WHERE room_id = %s", (room_id,))
                    conn.commit()
            return {"EC": 0, "EM": "Message saved successfully", "data": self._serialize_row(msg)}
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return {"EC": 1, "EM": f"Error saving message: {e}", "data": None}

    def auto_generate_title(self, first_message):
        cleaned = first_message.strip()
        cleaned = re.sub(r"<[^>]+>", "", cleaned)
        if len(cleaned) > 50:
            cleaned = cleaned[:47] + "..."
        return cleaned or "New conversation"

    @staticmethod
    def _serialize_row(row):
        for k, v in row.items():
            if isinstance(v, datetime):
                row[k] = v.isoformat()
            elif hasattr(v, "hex"):
                row[k] = str(v)
        return row

    @classmethod
    def _serialize_message_row(cls, row):
        metadata = row.pop("metadata", None) or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}

        row["intent"] = metadata.get("intent")
        row["entities"] = metadata.get("entities")
        row["message_order"] = int(row.get("message_order") or 0)
        return cls._serialize_row(row)
