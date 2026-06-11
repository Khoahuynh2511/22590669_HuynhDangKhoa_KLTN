"""
Trip Planning API Endpoints
SSE streaming endpoint for the 6-step modular itinerary workflow.
Integrated with chat_rooms/chat_history for message persistence.
"""
import logging
import json
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from ...schema.trip_planning_schema import TripPlanRequest, TripPlanStartRequest
from ...services.trip_planning import trip_planning_graph
from ...services.trip_planning.nodes import get_step_suggestions
from ...services.chat_room_service import ChatRoomService
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


def _get_chat_room_service() -> ChatRoomService:
    return ChatRoomService()


@router.post("/stream")
async def trip_plan_stream(
    request: TripPlanRequest,
    current_user: dict = Depends(get_current_user),
    chat_room_svc: ChatRoomService = Depends(_get_chat_room_service),
):
    """
    Send a message in the trip planning workflow and get streaming response.
    Saves messages to chat_history for persistence.

    SSE Event types:
    - start: {type: "start", conversation_id, room_id, current_step}
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
        room_id = request.room_id

        async def event_generator():
            try:
                # --- Ensure room exists for persistence ---
                if not room_id:
                    room_result = chat_room_svc.create_room(
                        user_id=user_id,
                        title="Lập kế hoạch du lịch"
                    )
                    actual_room_id = room_result.get("data", {}).get("room_id") if room_result.get("EC") == 0 else None
                else:
                    actual_room_id = room_id

                state_key = actual_room_id or request.conversation_id or f"plan_{user_id}"
                conversation_id = state_key

                # Send start event
                start_event = {
                    "type": "start",
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "room_id": actual_room_id,
                }
                yield f"data: {json.dumps(start_event, ensure_ascii=False)}\n\n"

                # --- Save user message to chat_history ---
                if actual_room_id:
                    try:
                        chat_room_svc.save_message(
                            room_id=actual_room_id,
                            user_id=user_id,
                            role="user",
                            content=request.message,
                            entities={"trip_planning": True, "step": None}
                        )
                        # Auto-update room title if first message
                        msg_count = chat_room_svc.count_messages(actual_room_id)
                        if msg_count <= 1:
                            title = chat_room_svc.auto_generate_title(request.message)
                            chat_room_svc.update_room(
                                room_id=actual_room_id,
                                user_id=user_id,
                                title=f"🗺️ {title}"
                            )
                    except Exception as e:
                        logger.warning(f"Failed to save user message to chat_history: {e}")

                # --- Handle updated itinerary from drag-and-drop ---
                if request.updated_itinerary:
                    trip_planning_graph.update_itinerary(
                        conversation_id=conversation_id,
                        updated_itinerary=request.updated_itinerary,
                        room_id=actual_room_id,
                    )

                state = await trip_planning_graph.process_step(
                    user_message=request.message,
                    conversation_id=conversation_id,
                    user_id=user_id,
                    room_id=actual_room_id,
                    client_ip=request.client.host if request.client else "127.0.0.1",
                )

                # Extract state data
                current_step = state.get("current_step", 1)
                step_message = state.get("step_message", "")
                waiting = state.get("waiting_for_input", True)
                is_complete = state.get("is_complete", False)
                suggestions = state.get("quick_suggestions", []) if waiting else []
                if waiting and not suggestions:
                    suggestions = get_step_suggestions(current_step, state)

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
                    "suggestions": suggestions,
                }
                yield f"data: {json.dumps(step_event, ensure_ascii=False)}\n\n"

                # Build entities metadata for assistant message
                assistant_entities = {
                    "trip_planning": True,
                    "step": current_step,
                    "suggestions": suggestions,
                }

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
                    assistant_entities["itinerary_data"] = state.get("suggested_itinerary", {})
                    assistant_entities["available_activities"] = state.get("available_activities", [])
                    assistant_entities["total_price"] = state.get("itinerary_total_price", 0)

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
                    assistant_entities["flights"] = state.get("flight_search_results", [])

                # Send trains if step 5
                if state.get("train_search_results"):
                    trains_event = {
                        "type": "trains",
                        "data": state.get("train_search_results", []),
                    }
                    yield f"data: {json.dumps(trains_event, ensure_ascii=False)}\n\n"
                    assistant_entities["trains"] = state.get("train_search_results", [])

                # Send checkout summary / payment for step 6
                if current_step == 6:
                    from app.v1.services.trip_planning.trip_checkout_service import calculate_grand_total
                    checkout_event = {
                        "type": "checkout",
                        "data": {
                            "plan_id": state.get("custom_plan_id"),
                            "booking_id": state.get("booking_id"),
                            "payment_id": state.get("payment_id"),
                            "payment_url": state.get("payment_url"),
                            "total_price": calculate_grand_total(state),
                            "booking_completed": state.get("booking_completed", False),
                            "awaiting_payment": bool(
                                state.get("payment_url") and not state.get("booking_completed")
                            ),
                        },
                    }
                    yield f"data: {json.dumps(checkout_event, ensure_ascii=False)}\n\n"
                    assistant_entities["checkout_data"] = checkout_event["data"]

                # Send done
                done_event = {"type": "done", "is_complete": is_complete}
                yield f"data: {json.dumps(done_event, ensure_ascii=False)}\n\n"

                # --- Save assistant message to chat_history ---
                if actual_room_id and step_message:
                    try:
                        chat_room_svc.save_message(
                            room_id=actual_room_id,
                            user_id=user_id,
                            role="assistant",
                            content=step_message,
                            entities=assistant_entities
                        )
                    except Exception as e:
                        logger.warning(f"Failed to save assistant message to chat_history: {e}")

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
    state = trip_planning_graph.get_state(conversation_id)
    if state:
        return {
            "EC": 0,
            "data": {
                "conversation_id": conversation_id,
                "current_step": state.get("current_step", 1),
                "destination": state.get("destination"),
                "duration_days": state.get("duration_days"),
                "suggested_itinerary": state.get("suggested_itinerary"),
                "confirmed_itinerary": state.get("confirmed_itinerary"),
            }
        }
    return {
        "EC": 0,
        "data": {
            "conversation_id": conversation_id,
            "message": "Session not found or expired",
        }
    }
