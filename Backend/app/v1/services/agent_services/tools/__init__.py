
"""
Agent Tools Module
Tools for agents to use
"""
from typing import List
from langchain_core.tools import StructuredTool
from .mcp_tools import (
    create_booking_tool,
    get_user_bookings_tool,
    update_booking_tool,
    delete_booking_tool,
    verify_otp_and_confirm_booking_tool,
    resend_otp_tool,
    create_payment_tool,
    create_transport_payment_tool,
    apply_promotion_code_tool,
    search_tour_packages_tool,
    request_recommendation_tool,
    search_flights_tool,
    book_flight_tool,
    get_airports_tool,
    request_flight_search_tool,
    search_trains_tool,
    book_train_tool,
    get_train_stations_tool,
    get_seat_types_tool,
    request_train_search_tool,
    search_buses_tool,
    book_bus_tool,
    get_bus_stations_tool,
    request_bus_search_tool,
    search_hotels_tool,
    get_hotel_details_tool,
    book_hotel_tool,
    get_hotel_locations_tool,
    request_hotel_search_tool,
    get_current_temperature_tool,
    get_weather_forecast_tool,
    get_local_festivals_tool,
    search_mem0_episodes_tool,
    generate_tour_ui_tool,
    generate_payment_ui_tool,
    search_latest_tour_info_tool
)

__all__ = ["get_chat_tools"]


def get_chat_tools() -> List[StructuredTool]:
    """
    Get all tools available to Chat Agent

    Returns:
        List of StructuredTool instances
    """
    return [
        create_booking_tool(),
        get_user_bookings_tool(),
        update_booking_tool(),
        delete_booking_tool(),
        verify_otp_and_confirm_booking_tool(),
        resend_otp_tool(),
        create_payment_tool(),
        create_transport_payment_tool(),
        apply_promotion_code_tool(),
        generate_payment_ui_tool(),
        search_tour_packages_tool(),
        request_recommendation_tool(),
        search_flights_tool(),
        book_flight_tool(),
        get_airports_tool(),
        request_flight_search_tool(),
        search_trains_tool(),
        book_train_tool(),
        get_train_stations_tool(),
        get_seat_types_tool(),
        request_train_search_tool(),
        search_buses_tool(),
        book_bus_tool(),
        get_bus_stations_tool(),
        request_bus_search_tool(),
        search_hotels_tool(),
        get_hotel_details_tool(),
        book_hotel_tool(),
        get_hotel_locations_tool(),
        request_hotel_search_tool(),
        get_current_temperature_tool(),
        get_weather_forecast_tool(),
        get_local_festivals_tool(),
        search_mem0_episodes_tool(),
        generate_tour_ui_tool(),
        search_latest_tour_info_tool()
    ]
