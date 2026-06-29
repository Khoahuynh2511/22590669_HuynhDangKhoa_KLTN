"""
MCP Tools
Tools that call MCP server directly - OOP Architecture
"""
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import asyncio
import concurrent.futures
import logging
import json
from fastmcp import Client
from app.v1.core.config import settings
from app.v1.services.agent_services.skills.skill_loader import get_skill_loader
from app.v1.schema.shema_tool_mcp import (
    SearchTourPackagesInput,
    CreateBookingInput,
    RequestRecommendationInput,
    SearchFlightsInput,
    SearchTrainsInput,
    BookFlightInput,
    BookTrainInput,
    SearchBusesInput,
    BookBusInput,
    SearchHotelsInput,
    GetHotelDetailsInput,
    BookHotelInput,
    CreateTransportPaymentInput,
    EmptyInput,
    RequestFlightSearchInput,
    RequestTrainSearchInput,
    RequestBusSearchInput,
    RequestHotelSearchInput,
    GetCurrentTemperatureInput,
    GetWeatherForecastInput,
    GetLocalFestivalsInput,
    SearchEpisodesInput
)
from app.v1.mcp.src.schema import (
    GetUserBookingsInput,
    UpdateBookingInput,
    DeleteBookingInput,
    VerifyOTPInput,
    ResendOTPInput,
    CreatePaymentInput,
    ApplyPromotionCodeInput
)

logger = logging.getLogger(__name__)


# ============================================================================
# MCP CLIENT - Core MCP Communication
# ============================================================================

class MCPClient:
    """Core MCP client for calling MCP server tools"""

    def __init__(self):
        """Initialize MCP client"""
        self._base_url = None

    def _get_base_url(self) -> str:
        """Get MCP server base URL"""
        if self._base_url is None:
            from app.v1.core.prompts import PromptManager
            mcp_config = PromptManager().get_mcp_config()
            self._base_url = settings.MCP_SERVER_URL or mcp_config.get(
                'server_url',
                'http://localhost:8000/mcp/mcp'
            )
        return self._base_url

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """
        Generic method to call any MCP tool

        Args:
            tool_name: Name of the MCP tool
            params: Tool parameters

        Returns:
            Tool result (parsed from JSON if possible)
        """
        base_url = self._get_base_url()

        async with Client(base_url) as client:
            result = await client.call_tool(tool_name, params)

            # Handle CallToolResult object from FastMCP
            if hasattr(result, 'content'):
                content_list = result.content
                text_content = ""
                for item in content_list:
                    if hasattr(item, 'text'):
                        text_content += item.text
                    elif isinstance(item, dict) and item.get("type") == "text":
                        text_content += item.get("text", "")

                try:
                    return json.loads(text_content)
                except json.JSONDecodeError:
                    return text_content

            # Handle string result
            if isinstance(result, str):
                try:
                    return json.loads(result)
                except json.JSONDecodeError:
                    return result

            return result

    def call_tool_sync(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """
        Synchronous wrapper for calling MCP tool

        Args:
            tool_name: Name of the MCP tool
            params: Tool parameters

        Returns:
            Tool result
        """
        return self._run_async_in_thread(self.call_tool(tool_name, params))

    @staticmethod
    def _run_async_in_thread(coro):
        """
        Run async coroutine in a new thread with its own event loop

        Args:
            coro: Async coroutine to run

        Returns:
            Result from coroutine
        """
        def run_in_thread():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(coro)
            finally:
                try:
                    new_loop.run_until_complete(asyncio.sleep(0.1))
                except BaseException:
                    pass
                new_loop.close()

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(run_in_thread)
            return future.result(timeout=30)


# ============================================================================
# MCP TOOL HANDLERS - Business Logic for Each Tool Category
# ============================================================================

class BookingToolHandler:
    """Handler for booking-related MCP tools"""

    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client

    async def create_booking(
        self,
        user_phone: str,
        user_email: str,
        package_id: str,
        number_of_people: int,
        special_requests: str = "",
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new booking"""
        try:
            params = {
                "user_phone": user_phone,
                "user_email": user_email,
                "package_id": package_id,
                "number_of_people": number_of_people
            }
            if special_requests:
                params["special_requests"] = special_requests
            if user_id:
                params["user_id"] = user_id

            result = await self.mcp_client.call_tool("create_booking", params)
        except asyncio.TimeoutError:
            logger.error("create_booking timeout")
            return {"error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error in create_booking: {e}")
            return {"error": f"Failed to create booking: {str(e)}"}

        if result is None:
            return {"error": "Failed to create booking: No response from MCP server"}

        if isinstance(result, dict):
            if "success" in result:
                return result
            elif len(result) > 0:
                return result
            else:
                return {"error": "Failed to create booking: Empty response from MCP server"}

        return {"error": f"Failed to create booking: Unexpected response type: {type(result)}"}

    async def get_user_bookings(self, user_id: str) -> Dict[str, Any]:
        """Get all bookings for a user"""
        try:
            params = {"user_id": user_id}
            result = await self.mcp_client.call_tool("get_user_bookings", params)
        except asyncio.TimeoutError:
            logger.error("get_user_bookings timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error in get_user_bookings: {e}")
            return {"success": False, "error": f"Failed to get bookings: {str(e)}"}

        if result is None:
            return {"success": False, "error": "No response from MCP server"}

        return result if isinstance(result, dict) else {"success": False, "error": "Unexpected response type"}

    async def update_booking(
        self,
        booking_id: str,
        number_of_people: Optional[int] = None,
        special_requests: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update an existing booking"""
        try:
            params = {"booking_id": booking_id}
            if number_of_people is not None:
                params["number_of_people"] = number_of_people
            if special_requests is not None:
                params["special_requests"] = special_requests

            result = await self.mcp_client.call_tool("update_booking", params)
        except asyncio.TimeoutError:
            logger.error("update_booking timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error in update_booking: {e}")
            return {"success": False, "error": f"Failed to update booking: {str(e)}"}

        if result is None:
            return {"success": False, "error": "No response from MCP server"}

        return result if isinstance(result, dict) else {"success": False, "error": "Unexpected response type"}

    async def delete_booking(self, booking_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Delete (cancel) a booking"""
        try:
            params = {"booking_id": booking_id}
            if reason:
                params["reason"] = reason

            result = await self.mcp_client.call_tool("delete_booking", params)
        except asyncio.TimeoutError:
            logger.error("delete_booking timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error in delete_booking: {e}")
            return {"success": False, "error": f"Failed to delete booking: {str(e)}"}

        if result is None:
            return {"success": False, "error": "No response from MCP server"}

        return result if isinstance(result, dict) else {"success": False, "error": "Unexpected response type"}

    async def verify_otp_and_confirm_booking(self, booking_id: str, otp_code: str) -> Dict[str, Any]:
        """Verify OTP code and confirm booking"""
        try:
            params = {
                "booking_id": booking_id,
                "otp_code": otp_code
            }

            result = await self.mcp_client.call_tool("verify_otp_and_confirm_booking", params)
        except asyncio.TimeoutError:
            logger.error("verify_otp_and_confirm_booking timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error in verify_otp_and_confirm_booking: {e}")
            return {"success": False, "error": f"Failed to verify OTP: {str(e)}"}

        if result is None:
            return {"success": False, "error": "No response from MCP server"}

        return result if isinstance(result, dict) else {"success": False, "error": "Unexpected response type"}

    async def create_payment(
        self,
        booking_id: str,
        payment_method: str = "vnpay",
        return_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create payment và generate VNPay URL"""
        try:
            params = {
                "booking_id": booking_id,
                "payment_method": payment_method
            }
            if return_url:
                params["return_url"] = return_url

            result = await self.mcp_client.call_tool("create_payment", params)
        except asyncio.TimeoutError:
            logger.error("create_payment timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error in create_payment: {e}")
            return {"success": False, "error": f"Failed to create payment: {str(e)}"}

        if result is None:
            return {"success": False, "error": "No response from MCP server"}

        return result if isinstance(result, dict) else {"success": False, "error": "Unexpected response type"}

    async def resend_otp(self, booking_id: str) -> Dict[str, Any]:
        """Resend OTP code for a pending booking"""
        try:
            params = {"booking_id": booking_id}
            result = await self.mcp_client.call_tool("resend_otp", params)
        except asyncio.TimeoutError:
            logger.error("resend_otp timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error in resend_otp: {e}")
            return {"success": False, "error": f"Failed to resend OTP: {str(e)}"}

        if result is None:
            return {"success": False, "error": "No response from MCP server"}

        return result if isinstance(result, dict) else {"success": False, "error": "Unexpected response type"}

    async def create_transport_payment(
        self,
        booking_type: str,
        booking_id: str,
        payment_method: str = "vnpay"
    ) -> Dict[str, Any]:
        """Create payment for a flight or train booking"""
        try:
            params = {
                "booking_type": booking_type,
                "booking_id": booking_id,
                "payment_method": payment_method
            }
            result = await self.mcp_client.call_tool("create_transport_payment", params)
        except asyncio.TimeoutError:
            logger.error("create_transport_payment timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error in create_transport_payment: {e}")
            return {"success": False, "error": f"Failed to create transport payment: {str(e)}"}

        if result is None:
            return {"success": False, "error": "No response from MCP server"}

        return result if isinstance(result, dict) else {"success": False, "error": "Unexpected response type"}

    async def apply_promotion_code(
        self,
        booking_id: str,
        promotion_code: str
    ) -> Dict[str, Any]:
        """Apply promotion code to existing booking"""
        try:
            params = {
                "booking_id": booking_id,
                "promotion_code": promotion_code
            }

            result = await self.mcp_client.call_tool("apply_promotion_code", params)
        except asyncio.TimeoutError:
            logger.error("apply_promotion_code timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error in apply_promotion_code: {e}")
            return {"success": False, "error": f"Failed to apply promotion code: {str(e)}"}

        if result is None:
            return {"success": False, "error": "No response from MCP server"}

        return result if isinstance(result, dict) else {"success": False, "error": "Unexpected response type"}


class SearchToolHandler:
    """Handler for search-related MCP tools"""

    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client

    async def search_tour_packages(
        self,
        user_message: str,
        max_price: Optional[float] = None,
        duration: Optional[int] = None,
        destination: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Search tour packages using semantic vector search"""
        try:
            params = {"user_message": user_message, "limit": limit}
            if max_price is not None:
                params["max_price"] = max_price
            if duration is not None:
                params["duration"] = duration
            if destination:
                params["destination"] = destination

            result = await self.mcp_client.call_tool("search_tour_packages", params)
        except asyncio.TimeoutError:
            logger.error("search_tour_packages timeout")
            return {"found": 0, "packages": [], "error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error in search_tour_packages: {e}")
            return {"found": 0, "packages": [], "error": f"Failed to search: {str(e)}"}

        return result if result else {"found": 0, "packages": []}

    async def search_mem0_episodes(
        self,
        search_query: str,
        user_id: Optional[str] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """Search conversation memories stored in Mem0"""
        try:
            params = {"query_text": search_query, "limit": limit}
            if user_id:
                params["user_id"] = user_id

            result = await self.mcp_client.call_tool("search_episodes", params)
        except asyncio.TimeoutError:
            logger.error("search_mem0_episodes timeout")
            return {"found": 0, "episodes": [], "error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error in search_mem0_episodes: {e}")
            return {"found": 0, "episodes": [], "error": f"Failed to search: {str(e)}"}

        return result if result else {"found": 0, "episodes": []}


class FlightToolHandler:
    """Handler for flight-related MCP tools"""

    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client

    async def search_flights(self, departure_iata: str, arrival_iata: str, date: str = "", limit: int = 5) -> str:
        """Search for flights between two airports"""
        try:
            params = {
                "departure_iata": departure_iata,
                "arrival_iata": arrival_iata,
                "limit": limit
            }
            if date:
                params["date"] = date
            result = await self.mcp_client.call_tool("search_flights", params)
        except asyncio.TimeoutError:
            logger.error("search_flights timeout")
            return "Error: Request timeout"
        except Exception as e:
            logger.error(f"Error in search_flights: {e}")
            return f"Error: Failed to search flights: {str(e)}"

        return result if result else "Error: No response from MCP server"

    async def book_flight(
        self,
        flight_id: str,
        passenger_name: str,
        passenger_phone: str,
        passenger_email: str,
        seat_class: str = "economy",
        num_passengers: int = 1
    ) -> str:
        """Book a flight"""
        try:
            params = {
                "flight_id": flight_id,
                "passenger_name": passenger_name,
                "passenger_phone": passenger_phone,
                "passenger_email": passenger_email,
                "seat_class": seat_class,
                "num_passengers": num_passengers
            }
            result = await self.mcp_client.call_tool("book_flight", params)
        except asyncio.TimeoutError:
            logger.error("book_flight timeout")
            return "Error: Request timeout"
        except Exception as e:
            logger.error(f"Error in book_flight: {e}")
            return f"Error: Failed to book flight: {str(e)}"

        return result if result else "Error: No response from MCP server"

    async def get_airports(self) -> str:
        """Get list of supported airports"""
        try:
            result = await self.mcp_client.call_tool("get_airports", {})
        except Exception as e:
            logger.error(f"Error in get_airports: {e}")
            return f"Error: {str(e)}"
        return result if result else "Error: No response"

    @staticmethod
    def request_flight_search(
        user_query: str,
        departure_city: Optional[str] = None,
        arrival_city: Optional[str] = None,
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Trigger Flight Agent to handle flight search/booking"""
        return {
            "status": "requested",
            "message": "Flight Agent will handle this request",
            "user_query": user_query,
            "departure_city": departure_city,
            "arrival_city": arrival_city,
            "date": date
        }


class TrainToolHandler:
    """Handler for train-related MCP tools"""

    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client

    async def search_trains(self, departure_station: str, arrival_station: str, date: str = "", limit: int = 5) -> str:
        """Search for trains between two stations"""
        try:
            params = {
                "departure_station": departure_station,
                "arrival_station": arrival_station,
                "limit": limit
            }
            if date:
                params["date"] = date
            result = await self.mcp_client.call_tool("search_trains", params)
        except asyncio.TimeoutError:
            logger.error("search_trains timeout")
            return "Error: Request timeout"
        except Exception as e:
            logger.error(f"Error in search_trains: {e}")
            return f"Error: Failed to search trains: {str(e)}"

        return result if result else "Error: No response from MCP server"

    async def book_train(
        self,
        train_id: str,
        passenger_name: str,
        passenger_phone: str,
        passenger_email: str,
        seat_type: str = "soft_seat",
        num_passengers: int = 1
    ) -> str:
        """Book a train ticket"""
        try:
            params = {
                "train_id": train_id,
                "passenger_name": passenger_name,
                "passenger_phone": passenger_phone,
                "passenger_email": passenger_email,
                "seat_type": seat_type,
                "num_passengers": num_passengers
            }
            result = await self.mcp_client.call_tool("book_train", params)
        except asyncio.TimeoutError:
            logger.error("book_train timeout")
            return "Error: Request timeout"
        except Exception as e:
            logger.error(f"Error in book_train: {e}")
            return f"Error: Failed to book train: {str(e)}"

        return result if result else "Error: No response from MCP server"

    async def get_train_stations(self) -> str:
        """Get list of supported train stations"""
        try:
            result = await self.mcp_client.call_tool("get_train_stations", {})
        except Exception as e:
            logger.error(f"Error in get_train_stations: {e}")
            return f"Error: {str(e)}"
        return result if result else "Error: No response"

    async def get_seat_types(self) -> str:
        """Get list of seat types"""
        try:
            result = await self.mcp_client.call_tool("get_seat_types", {})
        except Exception as e:
            logger.error(f"Error in get_seat_types: {e}")
            return f"Error: {str(e)}"
        return result if result else "Error: No response"

    @staticmethod
    def request_train_search(
        user_query: str,
        departure_city: Optional[str] = None,
        arrival_city: Optional[str] = None,
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Trigger Train Agent to handle train search/booking"""
        return {
            "status": "requested",
            "message": "Train Agent will handle this request",
            "user_query": user_query,
            "departure_city": departure_city,
            "arrival_city": arrival_city,
            "date": date
        }


class BusToolHandler:
    """Handler for bus-related MCP tools"""

    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client

    async def search_buses(self, departure_station: str, arrival_station: str, date: str = "", limit: int = 5) -> str:
        """Search for buses between two bus stations"""
        try:
            params = {
                "departure_station": departure_station,
                "arrival_station": arrival_station,
                "limit": limit
            }
            if date:
                params["date"] = date
            result = await self.mcp_client.call_tool("search_buses", params)
        except asyncio.TimeoutError:
            logger.error("search_buses timeout")
            return "Error: Request timeout"
        except Exception as e:
            logger.error(f"Error in search_buses: {e}")
            return f"Error: Failed to search buses: {str(e)}"

        return result if result else "Error: No response from MCP server"

    async def book_bus(
        self,
        bus_id: str,
        passenger_name: str,
        passenger_phone: str,
        passenger_email: str,
        seat_type: str = "standard",
        num_passengers: int = 1,
        user_id: Optional[str] = None
    ) -> str:
        """Book a bus ticket"""
        try:
            params = {
                "bus_id": bus_id,
                "passenger_name": passenger_name,
                "passenger_phone": passenger_phone,
                "passenger_email": passenger_email,
                "seat_type": seat_type,
                "num_passengers": num_passengers
            }
            if user_id:
                params["user_id"] = user_id
            result = await self.mcp_client.call_tool("book_bus", params)
        except asyncio.TimeoutError:
            logger.error("book_bus timeout")
            return "Error: Request timeout"
        except Exception as e:
            logger.error(f"Error in book_bus: {e}")
            return f"Error: Failed to book bus: {str(e)}"

        return result if result else "Error: No response from MCP server"

    async def get_bus_stations(self) -> str:
        """Get list of supported bus stations"""
        try:
            result = await self.mcp_client.call_tool("get_bus_stations", {})
        except Exception as e:
            logger.error(f"Error in get_bus_stations: {e}")
            return f"Error: {str(e)}"
        return result if result else "Error: No response"

    @staticmethod
    def request_bus_search(
        user_query: str,
        departure_city: Optional[str] = None,
        arrival_city: Optional[str] = None,
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Trigger Bus Agent to handle bus search/booking"""
        return {
            "status": "requested",
            "message": "Bus Agent will handle this request",
            "user_query": user_query,
            "departure_city": departure_city,
            "arrival_city": arrival_city,
            "date": date
        }


class HotelToolHandler:
    """Handler for hotel-related MCP tools"""

    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client

    async def search_hotels(
        self,
        location: str = "",
        min_price: float = 0,
        max_price: float = 0,
        limit: int = 5
    ) -> str:
        """Search for hotels by location and price range"""
        try:
            params: Dict[str, Any] = {
                "location": location or "",
                "min_price": min_price,
                "max_price": max_price,
                "limit": limit,
            }
            result = await self.mcp_client.call_tool("search_hotels", params)
        except asyncio.TimeoutError:
            logger.error("search_hotels timeout")
            return "Error: Request timeout"
        except Exception as e:
            logger.error(f"Error in search_hotels: {e}")
            return f"Error: Failed to search hotels: {str(e)}"
        return result if result else "Error: No response from MCP server"

    async def get_hotel_details(self, hotel_id: str) -> str:
        """Get details of a single hotel by ID"""
        try:
            result = await self.mcp_client.call_tool("get_hotel_details", {"hotel_id": hotel_id})
        except Exception as e:
            logger.error(f"Error in get_hotel_details: {e}")
            return f"Error: {str(e)}"
        return result if result else "Error: No response from MCP server"

    async def book_hotel(
        self,
        hotel_id: str,
        guest_name: str,
        guest_phone: str,
        guest_email: str,
        check_in: str,
        check_out: str,
        num_rooms: int = 1,
        num_guests: int = 1,
        user_id: Optional[str] = None
    ) -> str:
        """Book a hotel room"""
        try:
            params: Dict[str, Any] = {
                "hotel_id": hotel_id,
                "guest_name": guest_name,
                "guest_phone": guest_phone,
                "guest_email": guest_email,
                "check_in": check_in,
                "check_out": check_out,
                "num_rooms": num_rooms,
                "num_guests": num_guests,
            }
            if user_id:
                params["user_id"] = user_id
            result = await self.mcp_client.call_tool("book_hotel", params)
        except asyncio.TimeoutError:
            logger.error("book_hotel timeout")
            return "Error: Request timeout"
        except Exception as e:
            logger.error(f"Error in book_hotel: {e}")
            return f"Error: Failed to book hotel: {str(e)}"
        return result if result else "Error: No response from MCP server"

    async def get_hotel_locations(self) -> str:
        """Get list of locations that have hotels"""
        try:
            result = await self.mcp_client.call_tool("get_hotel_locations", {})
        except Exception as e:
            logger.error(f"Error in get_hotel_locations: {e}")
            return f"Error: {str(e)}"
        return result if result else "Error: No response from MCP server"

    @staticmethod
    def request_hotel_search(
        user_query: str,
        location: Optional[str] = None,
        check_in: Optional[str] = None,
        check_out: Optional[str] = None
    ) -> Dict[str, Any]:
        """Trigger Hotel Agent to handle hotel search/booking"""
        return {
            "status": "requested",
            "message": "Hotel Agent will handle this request",
            "user_query": user_query,
            "location": location,
            "check_in": check_in,
            "check_out": check_out
        }


class WeatherToolHandler:
    """Handler for weather-related MCP tools"""

    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client

    async def get_current_temperature(self, city_name: str) -> str:
        """Get current temperature and weather conditions"""
        try:
            params = {"city_name": city_name}
            result = await self.mcp_client.call_tool("get_current_temperature_by_city", params)
        except asyncio.TimeoutError:
            logger.error("get_current_temperature timeout")
            return "Error: Request timeout"
        except Exception as e:
            logger.error(f"Error in get_current_temperature: {e}")
            return f"Error: Failed to get weather: {str(e)}"

        return result if result else "Error: No response from MCP server"

    async def get_weather_forecast(self, city_name: str, days: int = 5) -> str:
        """Get weather forecast for a city"""
        try:
            params = {"city_name": city_name, "days": days}
            result = await self.mcp_client.call_tool("get_weather_forecast_by_city", params)
        except asyncio.TimeoutError:
            logger.error("get_weather_forecast timeout")
            return "Error: Request timeout"
        except Exception as e:
            logger.error(f"Error in get_weather_forecast: {e}")
            return f"Error: Failed to get forecast: {str(e)}"

        return result if result else "Error: No response from MCP server"


class FestivalToolHandler:
    """Handler for festival-related MCP tools (Wikidata SPARQL)"""

    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client

    async def get_local_festivals(self, province: str = "", month: Optional[int] = None) -> str:
        """Get local festivals / events in Vietnam by province and/or month"""
        try:
            params = {"province": province or "", "month": month}
            result = await self.mcp_client.call_tool("get_local_festivals_by_province", params)
        except asyncio.TimeoutError:
            logger.error("get_local_festivals timeout")
            return "Error: Request timeout"
        except Exception as e:
            logger.error(f"Error in get_local_festivals: {e}")
            return f"Error: Failed to get festivals: {str(e)}"

        return result if result else "Error: No response from MCP server"


class UIToolHandler:
    """Handler for UI-related MCP tools"""

    def __init__(self, mcp_client: MCPClient):
        self.mcp_client = mcp_client

    async def generate_tour_ui(self, packages: list) -> Dict[str, Any]:
        """Generate interactive UI for tour packages"""
        try:
            params = {"packages": packages}
            result = await self.mcp_client.call_tool("generate_tour_ui", params)
        except asyncio.TimeoutError:
            logger.error("generate_tour_ui timeout")
            return {"error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error in generate_tour_ui: {e}")
            return {"error": f"Failed to generate UI: {str(e)}"}

        return result if result else {"error": "No response from MCP server"}

    async def generate_payment_ui(
        self,
        payment_url: str,
        booking_id: str,
        total_amount: float,
        tour_name: str,
        payment_method: str = "vnpay"
    ) -> Dict[str, Any]:
        """Generate payment button UI component"""
        try:
            params = {
                "payment_url": payment_url,
                "booking_id": booking_id,
                "total_amount": total_amount,
                "tour_name": tour_name,
                "payment_method": payment_method
            }
            result = await self.mcp_client.call_tool("generate_payment_ui", params)
        except asyncio.TimeoutError:
            logger.error("generate_payment_ui timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.error(f"Error in generate_payment_ui: {e}")
            return {"success": False, "error": f"Failed to generate payment UI: {str(e)}"}

        return result if result else {"success": False, "error": "No response from MCP server"}


class RecommendationToolHandler:
    """Handler for recommendation-related tools (internal, not MCP)"""

    @staticmethod
    def request_recommendation(
        user_query: str,
        destination: Optional[str] = None,
        budget: Optional[float] = None,
        duration: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Chat Agent calls Recommendation Agent to get tour recommendations

        This is how Chat Agent communicates with Recommendation Agent.
        When Chat Agent determines user needs tour recommendations, it calls this tool.
        """
        return {
            "status": "requested",
            "message": "Recommendation Agent will provide tour recommendations",
            "user_query": user_query,
            "destination": destination,
            "budget": budget,
            "duration": duration
        }


class PerplexityToolHandler:
    """Handler for Perplexity API tools (Tour Information Skill)"""

    def __init__(self):
        """Initialize Perplexity Tool Handler (lazy load)"""
        self._perplexity_service = None
        self.skill_loader = get_skill_loader()
        self.skill_guidelines = self._get_skill_guidelines()

    @property
    def perplexity_service(self):
        if self._perplexity_service is None:
            from app.v1.services.agent_services.skills.tour_information.perplexity_service import get_perplexity_service
            self._perplexity_service = get_perplexity_service()
        return self._perplexity_service

    def _get_skill_guidelines(self) -> Optional[str]:
        """
        Load full SKILL.md content for progressive disclosure (Level 2)
        """
        try:
            content = self.skill_loader.load_skill_content("Tour Information Collector")
            return content
        except Exception as e:
            logger.warning(f"Could not load skill guidelines: {e}")
            return None

    async def search_latest_tour_info(self, destination: str) -> Dict[str, Any]:
        """
        Tìm thông tin tour mới nhất cho một địa điểm bằng Perplexity API

        Args:
            destination: Tên địa điểm (ví dụ: "Đà Lạt", "Phú Quốc", "Hà Nội")

        Returns:
            Dict với thông tin tour: destination, highlights, typical_prices, best_time, tips, sources
        """
        result = await self.perplexity_service.search_tour_info(destination)
        if self.skill_guidelines:
            result["skill_guidelines"] = self.skill_guidelines
        return result

    def search_latest_tour_info_sync(self, destination: str) -> Dict[str, Any]:
        """Synchronous wrapper for search_latest_tour_info"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, use run_until_complete in a new thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(self.perplexity_service.search_tour_info(destination))
                    )
                    result = future.result(timeout=30)
            else:
                result = loop.run_until_complete(self.perplexity_service.search_tour_info(destination))
        except RuntimeError:
            # No event loop, create one
            result = asyncio.run(self.perplexity_service.search_tour_info(destination))

        if self.skill_guidelines:
            result["skill_guidelines"] = self.skill_guidelines
        return result


# ============================================================================
# MCP TOOL FACTORY - Creates LangChain StructuredTools
# ============================================================================

class MCPToolFactory:
    """Factory for creating LangChain StructuredTools from MCP handlers"""

    def __init__(self):
        """Initialize factory with MCP client and handlers"""
        self.mcp_client = MCPClient()
        self.booking_handler = BookingToolHandler(self.mcp_client)
        self.search_handler = SearchToolHandler(self.mcp_client)
        self.flight_handler = FlightToolHandler(self.mcp_client)
        self.train_handler = TrainToolHandler(self.mcp_client)
        self.bus_handler = BusToolHandler(self.mcp_client)
        self.hotel_handler = HotelToolHandler(self.mcp_client)
        self.weather_handler = WeatherToolHandler(self.mcp_client)
        self.ui_handler = UIToolHandler(self.mcp_client)
        self.festival_handler = FestivalToolHandler(self.mcp_client)
        self.recommendation_handler = RecommendationToolHandler()
        self.perplexity_handler = PerplexityToolHandler()

    # Booking Tools
    def create_booking_tool(self) -> StructuredTool:
        """Create StructuredTool for create_booking"""
        return StructuredTool.from_function(
            func=create_booking_sync,
            coroutine=self.booking_handler.create_booking,
            name="create_booking",
            description="Tạo booking mới cho user - YÊU CẦU THU THẬP ĐẦY ĐỦ THÔNG TIN TRƯỚC KHI GỌI (user_phone, user_email, package_id, number_of_people). Hệ thống sẽ gửi mã OTP về email để xác nhận.",
            args_schema=CreateBookingInput)

    def get_user_bookings_tool(self) -> StructuredTool:
        """Create StructuredTool for get_user_bookings"""
        return StructuredTool.from_function(
            func=get_user_bookings_sync,
            coroutine=self.booking_handler.get_user_bookings,
            name="get_user_bookings",
            description="Lấy danh sách tất cả các booking của user. Trả về chi tiết tour, ngày khởi hành, số người, tổng tiền và trạng thái booking.",
            args_schema=GetUserBookingsInput)

    def update_booking_tool(self) -> StructuredTool:
        """Create StructuredTool for update_booking"""
        return StructuredTool.from_function(
            func=update_booking_sync,
            coroutine=self.booking_handler.update_booking,
            name="update_booking",
            description="Cập nhật booking hiện tại - có thể thay đổi số người hoặc ghi chú đặc biệt. Nếu tăng số người, hệ thống tự động kiểm tra còn slot và cập nhật giá.",
            args_schema=UpdateBookingInput)

    def delete_booking_tool(self) -> StructuredTool:
        """Create StructuredTool for delete_booking"""
        return StructuredTool.from_function(
            func=delete_booking_sync,
            coroutine=self.booking_handler.delete_booking,
            name="delete_booking",
            description="Hủy (cancel) booking và trả lại slot cho tour. Dữ liệu booking được giữ lại với trạng thái 'cancelled' (soft delete).",
            args_schema=DeleteBookingInput)

    def verify_otp_and_confirm_booking_tool(self) -> StructuredTool:
        """Create StructuredTool for verify_otp_and_confirm_booking"""
        # Define internal sync wrapper
        def verify_otp_sync(*args, **kwargs):
            return _run_async_safe(self.booking_handler.verify_otp_and_confirm_booking(*args, **kwargs))

        return StructuredTool.from_function(
            func=verify_otp_sync,
            coroutine=self.booking_handler.verify_otp_and_confirm_booking,
            name="verify_otp_and_confirm_booking",
            description="Xác thực mã OTP và xác nhận booking. Gọi tool này khi user cung cấp mã OTP 6 số từ email. Sau khi verify thành công, booking sẽ được chuyển sang trạng thái 'confirmed'.",
            args_schema=VerifyOTPInput)

    def resend_otp_tool(self) -> StructuredTool:
        """Create StructuredTool for resend_otp"""
        # Define internal sync wrapper
        def resend_otp_sync(*args, **kwargs):
            return _run_async_safe(self.booking_handler.resend_otp(*args, **kwargs))

        return StructuredTool.from_function(
            func=resend_otp_sync,
            coroutine=self.booking_handler.resend_otp,
            name="resend_otp",
            description="Resend OTP code to user's email. Use when user says 'gửi lại OTP', 'resend OTP', 'không nhận được OTP'.",
            args_schema=ResendOTPInput)

    def create_payment_tool(self) -> StructuredTool:
        """Create StructuredTool for create_payment"""
        # Define internal sync wrapper
        def create_payment_sync(*args, **kwargs):
            return _run_async_safe(self.booking_handler.create_payment(*args, **kwargs))

        return StructuredTool.from_function(
            func=create_payment_sync,
            coroutine=self.booking_handler.create_payment,
            name="create_payment",
            description="Tạo payment request và generate VNPay URL cho booking đã được xác nhận. Gọi tool này sau khi verify OTP thành công để tạo link thanh toán. Tool sẽ trả về payment_url để user có thể thanh toán.",
            args_schema=CreatePaymentInput)

    def create_transport_payment_tool(self) -> StructuredTool:
        """Create StructuredTool for create_transport_payment"""
        def create_transport_payment_sync(*args, **kwargs):
            return _run_async_safe(self.booking_handler.create_transport_payment(*args, **kwargs))

        return StructuredTool.from_function(
            func=create_transport_payment_sync,
            coroutine=self.booking_handler.create_transport_payment,
            name="create_transport_payment",
            description="Tao payment request va generate VNPay URL cho booking ve may bay hoac ve tau. booking_type chi ho tro flight hoac train.",
            args_schema=CreateTransportPaymentInput)

    def apply_promotion_code_tool(self) -> StructuredTool:
        """Create StructuredTool for apply_promotion_code"""
        return StructuredTool.from_function(
            func=apply_promotion_code_sync,
            coroutine=self.booking_handler.apply_promotion_code,
            name="apply_promotion_code",
            description=(
                "Áp dụng mã khuyến mãi (promotion code) vào booking đã tạo. "
                "Gọi tool này khi user cung cấp mã giảm giá sau khi booking đã được tạo (status='pending', sau khi verify OTP). "
                "Tool sẽ validate mã khuyến mãi, tính discount, và cập nhật total_amount của booking. "
                "Sau khi áp dụng thành công, booking sẽ có giá mới (đã giảm) và có thể thanh toán với giá đã giảm. "
                "LƯU Ý: Chỉ áp dụng được cho booking có status='pending' (chưa thanh toán)."),
            args_schema=ApplyPromotionCodeInput)

    # Search Tools
    def search_tour_packages_tool(self) -> StructuredTool:
        """Create StructuredTool for search_tour_packages"""
        return StructuredTool.from_function(
            func=search_tour_packages_sync,
            coroutine=self.search_handler.search_tour_packages,
            name="search_tour_packages",
            description="Search tour packages using semantic vector search. This tool uses AI embeddings to find tours that semantically match the user's query.",
            args_schema=SearchTourPackagesInput)

    def search_mem0_episodes_tool(self) -> StructuredTool:
        """Create StructuredTool for search_mem0_episodes"""
        return StructuredTool.from_function(
            func=search_mem0_episodes_sync,
            coroutine=self.search_handler.search_mem0_episodes,
            name="search_episodes",
            description="Search through conversation history and user interactions stored in Mem0 memory system to find relevant episodes. Use this to find past conversations or user preferences related to the query.",
            args_schema=SearchEpisodesInput)

    # Flight Tools
    def search_flights_tool(self) -> StructuredTool:
        """Create StructuredTool for search_flights"""
        return StructuredTool.from_function(
            func=search_flights_sync,
            coroutine=self.flight_handler.search_flights,
            name="search_flights",
            description="Search for flights between two airports. Returns future flights only (not yet departed). Use IATA codes (e.g., HAN=Hanoi, SGN=Ho Chi Minh, DAD=Da Nang). Supports date parameter.",
            args_schema=SearchFlightsInput)

    def book_flight_tool(self) -> StructuredTool:
        """Create StructuredTool for book_flight"""
        return StructuredTool.from_function(
            func=book_flight_sync,
            coroutine=self.flight_handler.book_flight,
            name="book_flight",
            description="Đặt vé máy bay. Cần flight_id từ kết quả search, tên hành khách, SĐT, email, hạng ghế (economy/business/first_class), số người.",
            args_schema=BookFlightInput)

    def get_airports_tool(self) -> StructuredTool:
        """Create StructuredTool for get_airports"""
        def get_airports_sync():
            return _run_async_safe(self.flight_handler.get_airports())

        return StructuredTool.from_function(
            func=get_airports_sync,
            coroutine=self.flight_handler.get_airports,
            name="get_airports",
            description="Lay danh sach san bay Viet Nam duoc ho tro va ma IATA.",
            args_schema=EmptyInput
        )

    def request_flight_search_tool(self) -> StructuredTool:
        """Create StructuredTool for request_flight_search - triggers Flight Agent"""
        return StructuredTool.from_function(
            func=self.flight_handler.request_flight_search,
            name="request_flight_search",
            description="Gọi Flight Agent để tìm kiếm và xử lý yêu cầu vé máy bay. Sử dụng khi user muốn tìm chuyến bay, hỏi về vé máy bay, hoặc đặt vé máy bay.",
            args_schema=RequestFlightSearchInput)

    # Train Tools
    def search_trains_tool(self) -> StructuredTool:
        """Create StructuredTool for search_trains"""
        return StructuredTool.from_function(
            func=search_trains_sync,
            coroutine=self.train_handler.search_trains,
            name="search_trains",
            description="Tìm kiếm chuyến tàu hỏa Việt Nam. Dùng mã ga (HNO=Hà Nội, SGO=Sài Gòn, DNA=Đà Nẵng, HUE=Huế, NTR=Nha Trang, LCA=Lào Cai). Hỗ trợ tham số ngày.",
            args_schema=SearchTrainsInput)

    def book_train_tool(self) -> StructuredTool:
        """Create StructuredTool for book_train"""
        return StructuredTool.from_function(
            func=book_train_sync,
            coroutine=self.train_handler.book_train,
            name="book_train",
            description="Đặt vé tàu hỏa. Cần train_id từ kết quả search, tên hành khách, SĐT, email, loại ghế (hard_seat/soft_seat/hard_sleeper_6/soft_sleeper_6/soft_sleeper_4/vip_cabin), số người.",
            args_schema=BookTrainInput)

    def get_train_stations_tool(self) -> StructuredTool:
        """Create StructuredTool for get_train_stations"""
        def get_train_stations_sync():
            return _run_async_safe(self.train_handler.get_train_stations())

        return StructuredTool.from_function(
            func=get_train_stations_sync,
            coroutine=self.train_handler.get_train_stations,
            name="get_train_stations",
            description="Lay danh sach ga tau Viet Nam duoc ho tro va ma ga.",
            args_schema=EmptyInput
        )

    def get_seat_types_tool(self) -> StructuredTool:
        """Create StructuredTool for get_seat_types"""
        def get_seat_types_sync():
            return _run_async_safe(self.train_handler.get_seat_types())

        return StructuredTool.from_function(
            func=get_seat_types_sync,
            coroutine=self.train_handler.get_seat_types,
            name="get_seat_types",
            description="Lay danh sach loai ghe/giuong tau duoc ho tro.",
            args_schema=EmptyInput
        )

    def request_train_search_tool(self) -> StructuredTool:
        """Create StructuredTool for request_train_search - triggers Train Agent"""
        return StructuredTool.from_function(
            func=self.train_handler.request_train_search,
            name="request_train_search",
            description="Gọi Train Agent để tìm kiếm và xử lý yêu cầu vé tàu hỏa. Sử dụng khi user muốn tìm chuyến tàu, hỏi về vé tàu, hoặc đặt vé tàu.",
            args_schema=RequestTrainSearchInput)

    # Bus Tools
    def search_buses_tool(self) -> StructuredTool:
        """Create StructuredTool for search_buses"""
        return StructuredTool.from_function(
            func=search_buses_sync,
            coroutine=self.bus_handler.search_buses,
            name="search_buses",
            description="Tim kiem chuyen xe khach Viet Nam. Dung ma ben xe (BXSG=Ho Chi Minh, BXHN=Ha Noi, BXDN=Da Nang, BXNT=Nha Trang, BXDL=Da Lat).",
            args_schema=SearchBusesInput)

    def book_bus_tool(self) -> StructuredTool:
        """Create StructuredTool for book_bus"""
        return StructuredTool.from_function(
            func=book_bus_sync,
            coroutine=self.bus_handler.book_bus,
            name="book_bus",
            description="Dat ve xe khach. Can bus_id tu ket qua search, ten hanh khach, SDT, email, loai ghe va so nguoi.",
            args_schema=BookBusInput)

    def get_bus_stations_tool(self) -> StructuredTool:
        """Create StructuredTool for get_bus_stations"""
        def get_bus_stations_sync():
            return _run_async_safe(self.bus_handler.get_bus_stations())

        return StructuredTool.from_function(
            func=get_bus_stations_sync,
            coroutine=self.bus_handler.get_bus_stations,
            name="get_bus_stations",
            description="Lay danh sach ben xe Viet Nam duoc ho tro va ma ben xe.",
            args_schema=EmptyInput
        )

    def request_bus_search_tool(self) -> StructuredTool:
        """Create StructuredTool for request_bus_search - triggers Bus Agent"""
        return StructuredTool.from_function(
            func=self.bus_handler.request_bus_search,
            name="request_bus_search",
            description="Gọi Bus Agent để tìm kiếm và xử lý yêu cầu vé xe khách. Sử dụng khi user muốn tìm chuyến xe, hỏi về vé xe, hoặc đặt vé xe.",
            args_schema=RequestBusSearchInput)

    # Hotel Tools
    def search_hotels_tool(self) -> StructuredTool:
        """Create StructuredTool for search_hotels"""
        return StructuredTool.from_function(
            func=search_hotels_sync,
            coroutine=self.hotel_handler.search_hotels,
            name="search_hotels",
            description="Tìm kiếm khách sạn tại Việt Nam theo địa điểm và khoảng giá. Dùng tên tỉnh/thành (vd: 'Đà Lạt', 'Hà Nội', 'Đà Nẵng', 'Phú Quốc'). Trả về tên, sao, điểm đánh giá, giá/phòng/đêm, tiện ích, số phòng trống và hotel_id.",
            args_schema=SearchHotelsInput)

    def get_hotel_details_tool(self) -> StructuredTool:
        """Create StructuredTool for get_hotel_details"""
        return StructuredTool.from_function(
            func=get_hotel_details_sync,
            coroutine=self.hotel_handler.get_hotel_details,
            name="get_hotel_details",
            description="Lấy thông tin chi tiết của 1 khách sạn theo hotel_id (từ kết quả search_hotels).",
            args_schema=GetHotelDetailsInput)

    def book_hotel_tool(self) -> StructuredTool:
        """Create StructuredTool for book_hotel"""
        return StructuredTool.from_function(
            func=book_hotel_sync,
            coroutine=self.hotel_handler.book_hotel,
            name="book_hotel",
            description="Đặt phòng khách sạn. Cần hotel_id (từ search), tên khách, SĐT, email, ngày nhận/trả phòng (YYYY-MM-DD), số phòng và số khách. YÊU CẦU THU THẬP ĐẦY ĐỦ THÔNG TIN TRƯỚC KHI GỌI.",
            args_schema=BookHotelInput)

    def get_hotel_locations_tool(self) -> StructuredTool:
        """Create StructuredTool for get_hotel_locations"""
        def get_hotel_locations_sync():
            return _run_async_safe(self.hotel_handler.get_hotel_locations())

        return StructuredTool.from_function(
            func=get_hotel_locations_sync,
            coroutine=self.hotel_handler.get_hotel_locations,
            name="get_hotel_locations",
            description="Lấy danh sách các địa điểm (tỉnh/thành) hiện có khách sạn.",
            args_schema=EmptyInput)

    def request_hotel_search_tool(self) -> StructuredTool:
        """Create StructuredTool for request_hotel_search - triggers Hotel Agent"""
        return StructuredTool.from_function(
            func=self.hotel_handler.request_hotel_search,
            name="request_hotel_search",
            description="Gọi Hotel Agent để tìm kiếm và xử lý yêu cầu đặt phòng khách sạn. Sử dụng khi user muốn tìm khách sạn, hỏi về phòng, hoặc đặt phòng.",
            args_schema=RequestHotelSearchInput)

    # Weather Tools
    def get_current_temperature_tool(self) -> StructuredTool:
        """Create StructuredTool for get_current_temperature"""
        return StructuredTool.from_function(
            func=get_current_temperature_sync,
            coroutine=self.weather_handler.get_current_temperature,
            name="get_current_temperature",
            description="Get current temperature and weather conditions for a city. Use this when user asks about current weather.",
            args_schema=GetCurrentTemperatureInput)

    def get_weather_forecast_tool(self) -> StructuredTool:
        """Create StructuredTool for get_weather_forecast"""
        return StructuredTool.from_function(
            func=get_weather_forecast_sync,
            coroutine=self.weather_handler.get_weather_forecast,
            name="get_weather_forecast",
            description="Get weather forecast for a city for the next few days (1-5 days). Use this when user asks about weather forecast or future weather.",
            args_schema=GetWeatherForecastInput)

    # Festival Tools
    def get_local_festivals_tool(self) -> StructuredTool:
        """Create StructuredTool for get_local_festivals (lễ hội/sự kiện từ Wikidata SPARQL)"""
        return StructuredTool.from_function(
            func=get_local_festivals_sync,
            coroutine=self.festival_handler.get_local_festivals,
            name="get_local_festivals",
            description=(
                "Tìm lễ hội / sự kiện địa phương tại Việt Nam theo tỉnh và/hoặc tháng (nguồn Wikidata, open-source). "
                "Dùng khi user hỏi về lễ hội, sự kiện, dịp đi chơi (vd: 'Huế có lễ hội gì tháng 3?', "
                "'đi Đà Lạt mùa nào có festival'). Giúp gợi ý đi đúng dịp lễ hội."
            ),
            args_schema=GetLocalFestivalsInput)

    # UI Tools
    def generate_tour_ui_tool(self) -> StructuredTool:
        """Create StructuredTool for generate_tour_ui"""
        class GenerateTourUIInput(BaseModel):
            packages: list = Field(..., description="List of tour package dictionaries to display in UI grid")

        return StructuredTool.from_function(
            func=generate_tour_ui_sync,
            coroutine=self.ui_handler.generate_tour_ui,
            name="generate_tour_ui",
            description="Generate beautiful interactive UI component displaying tour packages in a responsive grid. Use this after getting tour recommendations to show them visually with images, prices, and booking buttons.",
            args_schema=GenerateTourUIInput)

    def generate_payment_ui_tool(self) -> StructuredTool:
        """Create StructuredTool for generate_payment_ui"""
        class GeneratePaymentUIInput(BaseModel):
            payment_url: str = Field(..., description="VNPay payment URL to redirect user")
            booking_id: str = Field(..., description="Booking ID for this payment")
            total_amount: float = Field(..., ge=0, description="Total amount to pay in VND")
            tour_name: str = Field(..., description="Tour package name")
            payment_method: str = Field(default="vnpay", description="Payment method")

        # Define internal sync wrapper
        def generate_payment_ui_sync(*args, **kwargs):
            return _run_async_safe(self.ui_handler.generate_payment_ui(*args, **kwargs))

        return StructuredTool.from_function(
            func=generate_payment_ui_sync,
            coroutine=self.ui_handler.generate_payment_ui,
            name="generate_payment_ui",
            description="Generate payment button UI component for user to click and pay. Call this tool after create_payment succeeds to show payment button to user. The button will redirect user to VNPay payment page.",
            args_schema=GeneratePaymentUIInput)

    # Recommendation Tools
    def request_recommendation_tool(self) -> StructuredTool:
        """Create StructuredTool for request_recommendation"""
        return StructuredTool.from_function(
            func=self.recommendation_handler.request_recommendation,
            name="request_recommendation",
            description="Gọi Recommendation Agent để lấy tour recommendations. Sử dụng tool này khi user hỏi về tour, du lịch, địa điểm, hoặc muốn tìm tour packages. Chat Agent tự quyết định khi nào cần gọi tool này.",
            args_schema=RequestRecommendationInput)

    # Perplexity Tools (Tour Information Skill)
    def search_latest_tour_info_tool(self) -> StructuredTool:
        """Create StructuredTool for search_latest_tour_info"""
        class SearchLatestTourInfoInput(BaseModel):
            destination: str = Field(...,
                                     description="Tên địa điểm cần tìm thông tin tour (ví dụ: 'Đà Lạt', 'Phú Quốc', 'Hà Nội')")

        return StructuredTool.from_function(
            func=self.perplexity_handler.search_latest_tour_info, name="search_latest_tour_info", description=(
                "Tìm thông tin tour mới nhất và cập nhật cho một địa điểm cụ thể bằng Perplexity API. "
                "Sử dụng khi user hỏi về: thông tin tour mới nhất, xu hướng du lịch, điểm tham quan, giá cả, lưu ý du lịch cho địa điểm. "
                "Output format (tuân theo SKILL.md): destination, highlights (list), typical_prices (string), best_time (string), tips (list), sources (list URLs). "
                "Tool này trả về thông tin real-time từ internet, khác với request_recommendation (tìm trong database)."), args_schema=SearchLatestTourInfoInput)


# ============================================================================
# SINGLETON INSTANCE & BACKWARD COMPATIBILITY
# ============================================================================

# Create singleton factory instance
_tool_factory = MCPToolFactory()

# Backward compatibility: Export functions that match old API
# These wrap async functions for sync contexts (use ThreadPoolExecutor if event loop exists)


def _run_async_safe(coro):
    """Run async coroutine safely, handling existing event loops"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Event loop is running, use ThreadPoolExecutor
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(lambda: asyncio.run(coro))
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(coro)


def create_booking_sync(*args, **kwargs):
    return _run_async_safe(_tool_factory.booking_handler.create_booking(*args, **kwargs))


def get_user_bookings_sync(*args, **kwargs):
    return _run_async_safe(_tool_factory.booking_handler.get_user_bookings(*args, **kwargs))


def update_booking_sync(*args, **kwargs):
    return _run_async_safe(_tool_factory.booking_handler.update_booking(*args, **kwargs))


def delete_booking_sync(*args, **kwargs):
    return _run_async_safe(_tool_factory.booking_handler.delete_booking(*args, **kwargs))


def resend_otp_sync(*args, **kwargs):
    return _run_async_safe(_tool_factory.booking_handler.resend_otp(*args, **kwargs))


def create_transport_payment_sync(*args, **kwargs):
    return _run_async_safe(_tool_factory.booking_handler.create_transport_payment(*args, **kwargs))


def search_tour_packages_sync(*args, **kwargs):
    return _run_async_safe(_tool_factory.search_handler.search_tour_packages(*args, **kwargs))


def search_mem0_episodes_sync(*args, **kwargs):
    return _run_async_safe(_tool_factory.search_handler.search_mem0_episodes(*args, **kwargs))


def search_flights_sync(*args, **kwargs):
    return _run_async_safe(_tool_factory.flight_handler.search_flights(*args, **kwargs))


def book_flight_sync(*args, **kwargs):
    return _run_async_safe(_tool_factory.flight_handler.book_flight(*args, **kwargs))


def search_trains_sync(*args, **kwargs):
    return _run_async_safe(_tool_factory.train_handler.search_trains(*args, **kwargs))


def book_train_sync(*args, **kwargs):
    return _run_async_safe(_tool_factory.train_handler.book_train(*args, **kwargs))


def search_buses_sync(*args, **kwargs):
    return _run_async_safe(_tool_factory.bus_handler.search_buses(*args, **kwargs))


def book_bus_sync(*args, **kwargs):
    return _run_async_safe(_tool_factory.bus_handler.book_bus(*args, **kwargs))


def search_hotels_sync(*args, **kwargs):
    return _run_async_safe(_tool_factory.hotel_handler.search_hotels(*args, **kwargs))


def get_hotel_details_sync(*args, **kwargs):
    return _run_async_safe(_tool_factory.hotel_handler.get_hotel_details(*args, **kwargs))


def book_hotel_sync(*args, **kwargs):
    return _run_async_safe(_tool_factory.hotel_handler.book_hotel(*args, **kwargs))


def get_hotel_locations_sync():
    return _run_async_safe(_tool_factory.hotel_handler.get_hotel_locations())


def get_current_temperature_sync(*args, **kwargs):
    return _run_async_safe(_tool_factory.weather_handler.get_current_temperature(*args, **kwargs))


def get_weather_forecast_sync(*args, **kwargs):
    return _run_async_safe(_tool_factory.weather_handler.get_weather_forecast(*args, **kwargs))


def get_local_festivals_sync(*args, **kwargs):
    return _run_async_safe(_tool_factory.festival_handler.get_local_festivals(*args, **kwargs))


def generate_tour_ui_sync(*args, **kwargs):
    return _run_async_safe(_tool_factory.ui_handler.generate_tour_ui(*args, **kwargs))


def request_recommendation_sync(*args, **kwargs):
    return _tool_factory.recommendation_handler.request_recommendation(*args, **kwargs)

# Backward compatibility: Export tool creators


def create_booking_tool() -> StructuredTool:
    return _tool_factory.create_booking_tool()


def get_user_bookings_tool() -> StructuredTool:
    return _tool_factory.get_user_bookings_tool()


def update_booking_tool() -> StructuredTool:
    return _tool_factory.update_booking_tool()


def delete_booking_tool() -> StructuredTool:
    return _tool_factory.delete_booking_tool()


def verify_otp_and_confirm_booking_tool() -> StructuredTool:
    return _tool_factory.verify_otp_and_confirm_booking_tool()


def resend_otp_tool() -> StructuredTool:
    return _tool_factory.resend_otp_tool()


def create_payment_tool() -> StructuredTool:
    return _tool_factory.create_payment_tool()


def create_transport_payment_tool() -> StructuredTool:
    return _tool_factory.create_transport_payment_tool()


def apply_promotion_code_sync(*args, **kwargs):
    return _run_async_safe(_tool_factory.booking_handler.apply_promotion_code(*args, **kwargs))


def apply_promotion_code_tool() -> StructuredTool:
    return _tool_factory.apply_promotion_code_tool()


def search_tour_packages_tool() -> StructuredTool:
    return _tool_factory.search_tour_packages_tool()


def search_mem0_episodes_tool() -> StructuredTool:
    return _tool_factory.search_mem0_episodes_tool()


def search_flights_tool() -> StructuredTool:
    return _tool_factory.search_flights_tool()


def book_flight_tool() -> StructuredTool:
    return _tool_factory.book_flight_tool()


def get_airports_tool() -> StructuredTool:
    return _tool_factory.get_airports_tool()


def request_flight_search_tool() -> StructuredTool:
    return _tool_factory.request_flight_search_tool()


def search_trains_tool() -> StructuredTool:
    return _tool_factory.search_trains_tool()


def book_train_tool() -> StructuredTool:
    return _tool_factory.book_train_tool()


def get_train_stations_tool() -> StructuredTool:
    return _tool_factory.get_train_stations_tool()


def get_seat_types_tool() -> StructuredTool:
    return _tool_factory.get_seat_types_tool()


def request_train_search_tool() -> StructuredTool:
    return _tool_factory.request_train_search_tool()


def search_buses_tool() -> StructuredTool:
    return _tool_factory.search_buses_tool()


def book_bus_tool() -> StructuredTool:
    return _tool_factory.book_bus_tool()


def get_bus_stations_tool() -> StructuredTool:
    return _tool_factory.get_bus_stations_tool()


def request_bus_search_tool() -> StructuredTool:
    return _tool_factory.request_bus_search_tool()


def search_hotels_tool() -> StructuredTool:
    return _tool_factory.search_hotels_tool()


def get_hotel_details_tool() -> StructuredTool:
    return _tool_factory.get_hotel_details_tool()


def book_hotel_tool() -> StructuredTool:
    return _tool_factory.book_hotel_tool()


def get_hotel_locations_tool() -> StructuredTool:
    return _tool_factory.get_hotel_locations_tool()


def request_hotel_search_tool() -> StructuredTool:
    return _tool_factory.request_hotel_search_tool()


def get_current_temperature_tool() -> StructuredTool:
    return _tool_factory.get_current_temperature_tool()


def get_weather_forecast_tool() -> StructuredTool:
    return _tool_factory.get_weather_forecast_tool()


def get_local_festivals_tool() -> StructuredTool:
    return _tool_factory.get_local_festivals_tool()


def generate_tour_ui_tool() -> StructuredTool:
    return _tool_factory.generate_tour_ui_tool()


def generate_payment_ui_tool() -> StructuredTool:
    return _tool_factory.generate_payment_ui_tool()


def request_recommendation_tool() -> StructuredTool:
    return _tool_factory.request_recommendation_tool()


def search_latest_tour_info_tool() -> StructuredTool:
    return _tool_factory.search_latest_tour_info_tool()

# Legacy compatibility: Keep old call_mcp_tool function


async def call_mcp_tool(tool_name: str, params: Dict[str, Any]) -> Any:
    """Legacy function for backward compatibility"""
    client = MCPClient()
    return await client.call_tool(tool_name, params)

# Export tool factory for direct async handler access


def get_tool_factory() -> MCPToolFactory:
    """Get the tool factory instance for direct async handler access"""
    return _tool_factory
