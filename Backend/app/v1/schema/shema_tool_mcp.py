from pydantic import BaseModel, Field
from typing import Optional


class SearchTourPackagesInput(BaseModel):
    """Input schema for search_tour_packages tool"""
    user_message: str = Field(description="User's search query in Vietnamese or English")
    max_price: Optional[float] = Field(default=None, description="Maximum price filter in VND")
    duration: Optional[int] = Field(default=None, description="Duration filter in days")
    destination: Optional[str] = Field(default=None, description="Destination filter")
    limit: int = Field(default=10, description="Maximum number of results")


class CreateBookingInput(BaseModel):
    """Input schema for create_booking tool"""
    user_phone: str = Field(description="User phone number")
    user_email: str = Field(description="User email address - REQUIRED for OTP verification")
    package_id: str = Field(description="Tour package ID from recommendation results")
    number_of_people: int = Field(description="Number of people traveling")
    special_requests: str = Field(default="", description="Special requests or requirements")
    user_id: Optional[str] = Field(default=None, description="User ID if available (for authenticated users)")


class RequestRecommendationInput(BaseModel):
    """Input schema for request_recommendation tool"""
    user_query: str = Field(description="User's query or request for tour recommendations")
    destination: Optional[str] = Field(default=None, description="Destination if mentioned")
    budget: Optional[float] = Field(default=None, description="Budget if mentioned")
    duration: Optional[int] = Field(default=None, description="Duration in days if mentioned")


class SearchFlightsInput(BaseModel):
    """Input schema for search_flights tool"""
    departure_iata: str = Field(description="Departure airport IATA code (e.g., HAN for Hanoi, SGN for Ho Chi Minh)")
    arrival_iata: str = Field(description="Arrival airport IATA code (e.g., SGN for Ho Chi Minh, HAN for Hanoi)")
    date: str = Field(default="", description="Travel date (YYYY-MM-DD), empty = today")
    limit: int = Field(default=5, description="Maximum number of flights to return (1-100)")


class GetCurrentTemperatureInput(BaseModel):
    """Input schema for get_current_temperature tool"""
    city_name: str = Field(description="City name to get current weather for")


class GetWeatherForecastInput(BaseModel):
    """Input schema for get_weather_forecast tool"""
    city_name: str = Field(description="City name to get weather forecast for")
    days: int = Field(default=5, description="Number of days to forecast (1-5)")


class SearchEpisodesInput(BaseModel):
    """Input schema for search_mem0_episodes tool"""
    query_text: str = Field(description="Search query text to find relevant episodes in Mem0 conversation history")
    user_id: Optional[str] = Field(default=None, description="Optional user ID for personalized search")
    limit: int = Field(default=5, description="Maximum number of results to return (1-20)")


class SearchTrainsInput(BaseModel):
    """Input schema for search_trains tool"""
    departure_station: str = Field(description="Departure station code (e.g., HNO=Hà Nội, SGO=Sài Gòn, DNA=Đà Nẵng)")
    arrival_station: str = Field(description="Arrival station code")
    date: str = Field(default="", description="Travel date (YYYY-MM-DD), empty = today")
    limit: int = Field(default=5, description="Maximum number of trains to return (1-10)")


class BookFlightInput(BaseModel):
    """Input schema for book_flight tool"""
    flight_id: str = Field(description="Flight ID from search results")
    passenger_name: str = Field(description="Full name of passenger")
    passenger_phone: str = Field(description="Phone number")
    passenger_email: str = Field(description="Email address")
    seat_class: str = Field(default="economy", description="Seat class: economy, business, first_class")
    num_passengers: int = Field(default=1, description="Number of passengers")


class BookTrainInput(BaseModel):
    """Input schema for book_train tool"""
    train_id: str = Field(description="Train ID from search results")
    passenger_name: str = Field(description="Full name of passenger")
    passenger_phone: str = Field(description="Phone number")
    passenger_email: str = Field(description="Email address")
    seat_type: str = Field(
        default="soft_seat",
        description="Seat type: hard_seat, soft_seat, hard_sleeper_6, soft_sleeper_6, soft_sleeper_4, vip_cabin")
    num_passengers: int = Field(default=1, description="Number of passengers")


class SearchBusesInput(BaseModel):
    """Input schema for search_buses tool"""
    departure_station: str = Field(description="Departure bus station code (e.g., BXSG=Ho Chi Minh, BXHN=Ha Noi)")
    arrival_station: str = Field(description="Arrival bus station code")
    date: str = Field(default="", description="Travel date (YYYY-MM-DD), empty = today")
    limit: int = Field(default=5, description="Maximum number of buses to return (1-10)")


class BookBusInput(BaseModel):
    """Input schema for book_bus tool"""
    bus_id: str = Field(description="Bus ID from search results")
    passenger_name: str = Field(description="Full name of passenger")
    passenger_phone: str = Field(description="Phone number")
    passenger_email: str = Field(description="Email address")
    seat_type: str = Field(
        default="standard",
        description="Seat type: standard, premium, single_sleeper, double_sleeper")
    num_passengers: int = Field(default=1, description="Number of passengers")
    user_id: Optional[str] = Field(default=None, description="User ID if available")


class CreateTransportPaymentInput(BaseModel):
    """Input schema for create_transport_payment tool"""
    booking_type: str = Field(description="Transport booking type: flight or train")
    booking_id: str = Field(description="Booking ID returned by book_flight or book_train")
    payment_method: str = Field(default="vnpay", description="Payment method")


class EmptyInput(BaseModel):
    """Input schema for tools that do not require arguments"""
    pass


class RequestFlightSearchInput(BaseModel):
    """Input schema for request_flight_search tool - triggers Flight Agent"""
    user_query: str = Field(description="User's flight search request in natural language")
    departure_city: Optional[str] = Field(default=None, description="Departure city or airport code if mentioned")
    arrival_city: Optional[str] = Field(default=None, description="Arrival city or airport code if mentioned")
    date: Optional[str] = Field(default=None, description="Travel date if mentioned (YYYY-MM-DD)")


class RequestTrainSearchInput(BaseModel):
    """Input schema for request_train_search tool - triggers Train Agent"""
    user_query: str = Field(description="User's train search request in natural language")
    departure_city: Optional[str] = Field(default=None, description="Departure city or station code if mentioned")
    arrival_city: Optional[str] = Field(default=None, description="Arrival city or station code if mentioned")
    date: Optional[str] = Field(default=None, description="Travel date if mentioned (YYYY-MM-DD)")
