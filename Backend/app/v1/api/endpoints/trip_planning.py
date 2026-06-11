"""
Trip Planning API Endpoints
SSE streaming endpoint for the 6-step modular itinerary workflow.
"""
import logging
import json
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from ...schema.trip_planning_schema import TripPlanRequest, TripPlanStartRequest, TripPlanStateResponse
from ...services.trip_planning import trip_planning_graph
from ...core.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


def _content_to_text(value) -> str:
    """Normalize message content into plain text."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(_content_to_text(item) for item in value)
    if isinstance(value, dict):
        if value.get("type") in {"text", "output_text"} and "text" in value:
            return _content_to_text(value.get("text"))
        if "text" in value:
            return _content_to_text(value.get("text"))
        if "content" in value:
            return _content_to_text(value.get("content"))
        return ""
    return str(value)


@router.post("/stream")
async def trip_plan_stream(
    request: TripPlanRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Send a message in the trip planning workflow and get streaming response.

    SSE Event types:
    - start: {type: "start", conversation_id, current_step}
    - step: {type: "step", step: N, message: "..."}
    - token: {type: "token", content: "chunk"}
    - activities: {type: "activities", data: {available: [...], suggested_itinerary: {...}}}
    - itinerary_confirmed: {type: "itinerary_confirmed", data: {...}}
    - flights: {type: "flights", data: [...]}
    - trains: {type: "trains", data: [...]}
    - checkout: {type: "checkout", data: {plan_id, total_price}}
    - done: {type: "done"}
    - error: {type: "error", error: "..."}
    """
    try:
        user_id = str(current_user["user_id"])
        conversation_id = request.conversation_id or f"plan_{user_id}"

        async def event_generator():
            try:
                # Send start event
                start_event = {
                    "type": "start",
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                }
                yield f"data: {json.dumps(start_event, ensure_ascii=False)}\n\n"

                # Process through graph (non-streaming for reliability)
                state = await trip_planning_graph.process_step(
                    user_message=request.message,
                    conversation_id=conversation_id,
                    user_id=user_id,
                )

                # Extract state data
                current_step = state.get("current_step", 1)
                step_message = state.get("step_message", "")
                waiting = state.get("waiting_for_input", True)
                is_complete = state.get("is_complete", False)

                # Send step message as tokens
                if step_message:
                    token_event = {
                        "type": "token",
                        "content": step_message,
                    }
                    yield f"data: {json.dumps(token_event, ensure_ascii=False)}\n\n"

                # Send step info
                step_event = {
                    "type": "step",
                    "step": current_step,
                    "message": step_message,
                    "waiting_for_input": waiting,
                }
                yield f"data: {json.dumps(step_event, ensure_ascii=False)}\n\n"

                # Send activities if step 4
                if current_step == 4 and state.get("available_activities"):
                    activities_event = {
                        "type": "activities",
                        "data": {
                            "available": state.get("available_activities", []),
                            "suggested_itinerary": state.get("suggested_itinerary", {}),
                            "total_price": state.get("itinerary_total_price", 0),
                        }
                    }
                    yield f"data: {json.dumps(activities_event, ensure_ascii=False)}\n\n"

                # Send itinerary confirmation
                if state.get("confirmed_itinerary"):
                    confirm_event = {
                        "type": "itinerary_confirmed",
                        "data": {
                            "itinerary": state.get("confirmed_itinerary"),
                            "total_price": state.get("itinerary_total_price", 0),
                        }
                    }
                    yield f"data: {json.dumps(confirm_event, ensure_ascii=False)}\n\n"

                # Send flights if step 5
                if state.get("flight_search_results"):
                    flights_event = {
                        "type": "flights",
                        "data": state.get("flight_search_results", []),
                    }
                    yield f"data: {json.dumps(flights_event, ensure_ascii=False)}\n\n"

                # Send trains if step 5
                if state.get("train_search_results"):
                    trains_event = {
                        "type": "trains",
                        "data": state.get("train_search_results", []),
                    }
                    yield f"data: {json.dumps(trains_event, ensure_ascii=False)}\n\n"

                # Send checkout if step 6
                if current_step == 6 and state.get("custom_plan_id"):
                    checkout_event = {
                        "type": "checkout",
                        "data": {
                            "plan_id": state.get("custom_plan_id"),
                            "total_price": state.get("itinerary_total_price", 0),
                            "booking_completed": state.get("booking_completed", False),
                        }
                    }
                    yield f"data: {json.dumps(checkout_event, ensure_ascii=False)}\n\n"

                # Send done
                done_event = {"type": "done", "is_complete": is_complete}
                yield f"data: {json.dumps(done_event, ensure_ascii=False)}\n\n"

            except Exception as e:
                logger.error(f"❌ Error in trip plan stream: {str(e)}")
                error_event = {"type": "error", "error": str(e)}
                yield f"data: {json.dumps(error_event)}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    except Exception as e:
        logger.error(f"❌ Error in trip_plan_stream endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_trip_plan(
    request: TripPlanStartRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Start a new trip planning session.
    Optionally pre-fill destination and duration.
    """
    try:
        user_id = str(current_user["user_id"])
        conversation_id = f"plan_{user_id}_{hash(str(request.destination))}"

        # Build initial message
        parts = []
        if request.destination:
            parts.append(f"Điểm đến: {request.destination}")
        if request.duration_days:
            parts.append(f"Thời gian: {request.duration_days} ngày")

        initial_message = ". ".join(parts) if parts else "Xin chào! Tôi muốn lên kế hoạch du lịch."

        # Process through graph
        state = await trip_planning_graph.process_step(
            user_message=initial_message,
            conversation_id=conversation_id,
            user_id=user_id,
        )

        return {
            "EC": 0,
            "EM": "Trip planning session started",
            "data": {
                "conversation_id": conversation_id,
                "current_step": state.get("current_step", 1),
                "step_message": state.get("step_message", ""),
                "waiting_for_input": state.get("waiting_for_input", True),
                "destination": state.get("destination"),
                "duration_days": state.get("duration_days"),
            }
        }

    except Exception as e:
        logger.error(f"❌ Error starting trip plan: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/state/{conversation_id}")
async def get_trip_plan_state(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Get current state of a trip planning session."""
    # For now, return a simple status
    return {
        "EC": 0,
        "data": {
            "conversation_id": conversation_id,
            "message": "Use POST /trip-planning/stream to continue the workflow",
        }
    }
