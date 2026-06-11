"""
Trip Planning Graph
LangGraph StateGraph for the 6-step modular itinerary workflow.

Architecture:
  START -> router -> step_N -> END

State is cached in-memory and persisted to trip_plan_states table (PostgreSQL).
Each API call: load state -> add message -> run graph -> save state -> return result.
"""
import json
import logging
import threading
from typing import Dict, Any, Optional, List

import psycopg2
from psycopg2.extras import RealDictCursor
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from app.v1.core.config import settings
from app.v1.services.trip_planning.state.trip_plan_state import TripPlanState
from app.v1.services.trip_planning.nodes import TripPlanningNodes

logger = logging.getLogger(__name__)

STEP_NODES = {
    1: "step1_basic_info",
    2: "step2_budget_people",
    3: "step3_preferences",
    4: "step4_plan_generation",
    5: "step5_transportation",
    6: "step6_checkout",
}

DEFAULT_STATE = {
    "messages": [],
    "conversation_id": "",
    "user_id": "",
    "current_step": 1,
    "destination": None,
    "travel_date": None,
    "duration_days": None,
    "group_size": None,
    "group_type": None,
    "budget_level": None,
    "preferences": None,
    "constraints": None,
    "available_activities": [],
    "suggested_itinerary": {},
    "confirmed_itinerary": {},
    "itinerary_total_price": None,
    "needs_flight": None,
    "needs_train": None,
    "selected_flight": None,
    "selected_train": None,
    "flight_search_results": [],
    "train_search_results": [],
    "custom_plan_id": None,
    "booking_id": None,
    "payment_url": None,
    "booking_completed": False,
    "step_message": "",
    "waiting_for_input": False,
    "is_complete": False,
    "quick_suggestions": [],
    "preferences_asked": False,
}

PERSIST_FIELDS = [
    "conversation_id", "user_id", "current_step", "destination", "travel_date",
    "duration_days", "group_size", "group_type", "budget_level", "preferences",
    "constraints", "available_activities", "suggested_itinerary", "confirmed_itinerary",
    "itinerary_total_price", "needs_flight", "needs_train", "selected_flight",
    "selected_train", "flight_search_results", "train_search_results",
    "custom_plan_id", "booking_id", "payment_url", "booking_completed",
    "step_message", "waiting_for_input", "is_complete",
    "quick_suggestions", "preferences_asked",
]


class TripPlanningGraph:
    """Static workflow graph for modular trip planning with DB persistence."""

    def __init__(self):
        self.nodes = TripPlanningNodes()
        self.graph = self._build_graph()
        self._states: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._table_ready = False
        logger.info("TripPlanningGraph initialized (memory + DB persistence)")

    def _conn(self):
        return psycopg2.connect(settings.DATABASE_URL, cursor_factory=RealDictCursor)

    def _ensure_state_table(self):
        if self._table_ready:
            return
        with self._lock:
            if self._table_ready:
                return
            try:
                with self._conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            CREATE TABLE IF NOT EXISTS trip_plan_states (
                                state_key VARCHAR(255) PRIMARY KEY,
                                room_id VARCHAR(255),
                                user_id VARCHAR(255),
                                state_data JSONB NOT NULL DEFAULT '{}',
                                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                            )
                        """)
                        conn.commit()
                self._table_ready = True
            except Exception as e:
                logger.warning(f"Could not ensure trip_plan_states table: {e}")

    @staticmethod
    def _serialize_messages(messages: List[BaseMessage]) -> List[Dict[str, str]]:
        serialized = []
        for msg in messages or []:
            if isinstance(msg, HumanMessage):
                serialized.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                serialized.append({"role": "assistant", "content": msg.content})
            elif hasattr(msg, "content"):
                serialized.append({"role": "unknown", "content": str(msg.content)})
        return serialized

    @staticmethod
    def _deserialize_messages(data: List[Dict[str, str]]) -> List[BaseMessage]:
        messages: List[BaseMessage] = []
        for item in data or []:
            role = item.get("role")
            content = item.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
        return messages

    def _state_to_payload(self, state: Dict[str, Any]) -> Dict[str, Any]:
        payload = {field: state.get(field) for field in PERSIST_FIELDS}
        payload["messages"] = self._serialize_messages(state.get("messages", []))
        return payload

    def _payload_to_state(self, payload: Dict[str, Any], state_key: str) -> Dict[str, Any]:
        state = dict(DEFAULT_STATE)
        for field in PERSIST_FIELDS:
            if field in payload:
                state[field] = payload[field]
        state["messages"] = self._deserialize_messages(payload.get("messages", []))
        state["conversation_id"] = state.get("conversation_id") or state_key
        return state

    def _load_state_from_db(self, state_key: str) -> Optional[Dict[str, Any]]:
        self._ensure_state_table()
        try:
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT state_data FROM trip_plan_states WHERE state_key = %s",
                        (state_key,),
                    )
                    row = cur.fetchone()
            if row and row.get("state_data"):
                data = row["state_data"]
                if isinstance(data, str):
                    data = json.loads(data)
                return self._payload_to_state(data, state_key)
        except Exception as e:
            logger.warning(f"Failed to load trip plan state from DB ({state_key}): {e}")
        return None

    def _save_state_to_db(self, state_key: str, state: Dict[str, Any], room_id: Optional[str] = None):
        self._ensure_state_table()
        try:
            payload = self._state_to_payload(state)
            with self._conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO trip_plan_states (state_key, room_id, user_id, state_data, updated_at)
                        VALUES (%s, %s, %s, %s, NOW())
                        ON CONFLICT (state_key)
                        DO UPDATE SET
                            room_id = EXCLUDED.room_id,
                            user_id = EXCLUDED.user_id,
                            state_data = EXCLUDED.state_data,
                            updated_at = NOW()
                        """,
                        (
                            state_key,
                            room_id or state_key,
                            state.get("user_id"),
                            json.dumps(payload, ensure_ascii=False, default=str),
                        ),
                    )
                    conn.commit()
        except Exception as e:
            logger.warning(f"Failed to save trip plan state to DB ({state_key}): {e}")

    def _resolve_state_key(self, conversation_id: str, room_id: Optional[str] = None) -> str:
        return room_id or conversation_id

    def _get_state(self, state_key: str) -> Dict[str, Any]:
        with self._lock:
            if state_key in self._states:
                return dict(self._states[state_key])

        db_state = self._load_state_from_db(state_key)
        if db_state:
            with self._lock:
                self._states[state_key] = db_state
            return dict(db_state)

        with self._lock:
            state = dict(DEFAULT_STATE)
            state["conversation_id"] = state_key
            self._states[state_key] = state
            return dict(state)

    def _save_state(self, state_key: str, state: Dict[str, Any], room_id: Optional[str] = None):
        with self._lock:
            self._states[state_key] = state
        self._save_state_to_db(state_key, state, room_id=room_id)

    def _build_graph(self):
        workflow = StateGraph(TripPlanState)

        workflow.add_node("router", self._router_node)
        workflow.add_node("step1_basic_info", self.nodes.step1_basic_info_node)
        workflow.add_node("step2_budget_people", self.nodes.step2_budget_people_node)
        workflow.add_node("step3_preferences", self.nodes.step3_preferences_node)
        workflow.add_node("step4_plan_generation", self.nodes.step4_plan_generation_node)
        workflow.add_node("step5_transportation", self.nodes.step5_transportation_node)
        workflow.add_node("step6_checkout", self.nodes.step6_checkout_node)

        workflow.add_edge(START, "router")
        workflow.add_conditional_edges(
            "router",
            self._route_to_step,
            {name: name for name in STEP_NODES.values()},
        )

        for node_name in STEP_NODES.values():
            workflow.add_edge(node_name, END)

        return workflow.compile()

    async def _router_node(self, state: TripPlanState) -> TripPlanState:
        return state

    def _route_to_step(self, state: TripPlanState) -> str:
        step = state.get("current_step", 1)
        node_name = STEP_NODES.get(step, "step1_basic_info")
        logger.info(f"Router -> {node_name} (step {step})")
        return node_name

    async def process_step(
        self,
        user_message: str,
        conversation_id: str = "default_plan",
        user_id: str = "anonymous_user",
        room_id: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> Dict[str, Any]:
        state_key = self._resolve_state_key(conversation_id, room_id)
        state = self._get_state(state_key)
        state["user_id"] = user_id
        state["conversation_id"] = state_key
        state["_client_ip"] = client_ip or "127.0.0.1"
        state["messages"] = state.get("messages", []) + [HumanMessage(content=user_message)]

        try:
            logger.info(
                f"Processing trip plan for {state_key}, step={state.get('current_step', 1)}"
            )
            result_state = await self.graph.ainvoke(state)
            self._save_state(state_key, result_state, room_id=room_id)
            logger.info(
                f"Done step={result_state.get('current_step', '?')}, "
                f"waiting={result_state.get('waiting_for_input')}"
            )
            return result_state
        except Exception as e:
            logger.error(f"Error in trip planning graph: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                **state,
                "step_message": f"Co loi xay ra: {str(e)}",
                "waiting_for_input": True,
                "is_complete": False,
            }

    def update_itinerary(
        self,
        conversation_id: str,
        updated_itinerary: Dict[str, Any],
        room_id: Optional[str] = None,
    ) -> None:
        state_key = self._resolve_state_key(conversation_id, room_id)
        state = self._get_state(state_key)
        if updated_itinerary:
            state["suggested_itinerary"] = updated_itinerary
            group_size = state.get("group_size", 1)
            total = 0.0
            for _, slots in updated_itinerary.items():
                if isinstance(slots, dict):
                    for _, activity in slots.items():
                        if activity and isinstance(activity, dict):
                            total += float(activity.get("price", 0) or 0) * group_size
            state["itinerary_total_price"] = total
            self._save_state(state_key, state, room_id=room_id)
            logger.info(f"Itinerary updated for {state_key}, new price: {total}")

    def get_state(self, conversation_id: str, room_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        state_key = self._resolve_state_key(conversation_id, room_id)
        with self._lock:
            if state_key in self._states:
                return dict(self._states[state_key])
        db_state = self._load_state_from_db(state_key)
        if db_state:
            with self._lock:
                self._states[state_key] = db_state
            return dict(db_state)
        return None


trip_planning_graph = TripPlanningGraph()
