"""
Trip Planning Graph
LangGraph StateGraph for the 6-step modular itinerary workflow.

Architecture:
  START → router → step_N → END

  No checkpointer. State is managed manually via in-memory dict.
  Each API call: load state → add message → run graph → save state → return result.
"""
import logging
import threading
from typing import Dict, Any, Optional

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage

from app.v1.services.trip_planning.state.trip_plan_state import TripPlanState
from app.v1.services.trip_planning.nodes import TripPlanningNodes

logger = logging.getLogger(__name__)

# Step node name mapping
STEP_NODES = {
    1: "step1_basic_info",
    2: "step2_budget_people",
    3: "step3_preferences",
    4: "step4_plan_generation",
    5: "step5_transportation",
    6: "step6_checkout",
}

# Default state for new conversations
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
}


class TripPlanningGraph:
    """
    Static workflow graph for modular trip planning.

    Manages state via in-memory dict keyed by conversation_id.
    Graph runs exactly 2 nodes per call: router + current_step_node.
    """

    def __init__(self):
        self.nodes = TripPlanningNodes()
        self.graph = self._build_graph()
        self._states: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        logger.info("TripPlanningGraph initialized (in-memory state)")

    def _get_state(self, conversation_id: str) -> Dict[str, Any]:
        """Load state for a conversation. Creates fresh state if not found."""
        with self._lock:
            if conversation_id not in self._states:
                state = dict(DEFAULT_STATE)
                state["conversation_id"] = conversation_id
                self._states[conversation_id] = state
            return dict(self._states[conversation_id])  # return copy

    def _save_state(self, conversation_id: str, state: Dict[str, Any]):
        """Save state for a conversation."""
        with self._lock:
            self._states[conversation_id] = state

    def _build_graph(self):
        """
        Build graph: router → step_N → END
        No loops. No checkpointer.
        """
        workflow = StateGraph(TripPlanState)

        # Router: pass-through, just for conditional dispatch
        workflow.add_node("router", self._router_node)

        # 6 step nodes
        workflow.add_node("step1_basic_info", self.nodes.step1_basic_info_node)
        workflow.add_node("step2_budget_people", self.nodes.step2_budget_people_node)
        workflow.add_node("step3_preferences", self.nodes.step3_preferences_node)
        workflow.add_node("step4_plan_generation", self.nodes.step4_plan_generation_node)
        workflow.add_node("step5_transportation", self.nodes.step5_transportation_node)
        workflow.add_node("step6_checkout", self.nodes.step6_checkout_node)

        # START → router
        workflow.add_edge(START, "router")

        # Router → conditional dispatch
        workflow.add_conditional_edges(
            "router",
            self._route_to_step,
            {name: name for name in STEP_NODES.values()}
        )

        # Every step → END (no loops!)
        for node_name in STEP_NODES.values():
            workflow.add_edge(node_name, END)

        return workflow.compile()

    async def _router_node(self, state: TripPlanState) -> TripPlanState:
        """Pass-through node. Conditional edge reads current_step to dispatch."""
        return state

    def _route_to_step(self, state: TripPlanState) -> str:
        """Route to the correct step node based on current_step."""
        step = state.get("current_step", 1)
        node_name = STEP_NODES.get(step, "step1_basic_info")
        logger.info(f"Router -> {node_name} (step {step})")
        return node_name

    async def process_step(
        self,
        user_message: str,
        conversation_id: str = "default_plan",
        user_id: str = "anonymous_user",
    ) -> Dict[str, Any]:
        """
        Process a single user message through the workflow.
        Loads saved state, appends message, runs graph, saves result.
        """
        # 1. Load existing state (or create fresh)
        state = self._get_state(conversation_id)
        state["user_id"] = user_id

        # 2. Append new user message
        state["messages"] = state.get("messages", []) + [HumanMessage(content=user_message)]

        # 3. Run graph
        try:
            logger.info(f"Processing trip plan for {conversation_id}, step={state.get('current_step', 1)}")
            result_state = await self.graph.ainvoke(state)

            # 4. Save result state
            self._save_state(conversation_id, result_state)

            logger.info(f"Done step={result_state.get('current_step', '?')}, waiting={result_state.get('waiting_for_input')}")
            return result_state

        except Exception as e:
            logger.error(f"Error in trip planning graph: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                **state,
                "step_message": f"Có lỗi xảy ra: {str(e)}",
                "waiting_for_input": True,
                "is_complete": False,
            }


# Singleton instance
trip_planning_graph = TripPlanningGraph()
