import json
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import httpx2
from langchain_core.tools import tool

WEATHER_DESCRIPTIONS = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


@tool
def get_weather(city: str, forecast_date: str) -> dict:
    """Get the weather forecast for a city on a given date (YYYY-MM-DD)."""

    try:
        requested_date = date.fromisoformat(forecast_date)
    except ValueError:
        return {"error": "Invalid date. Use YYYY-MM-DD format."}

    # Resolve the city to geographic coordinates.
    try:
        with httpx2.Client(timeout=10.0) as client:
            geo_response = client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1, "language": "en"},
            )
            geo_response.raise_for_status()
            locations = geo_response.json().get("results", [])

            if not locations:
                return {"error": f"City '{city}' not found."}

            location = locations[0]

            # Request the daily forecast for the selected location.
            weather_response = client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": location["latitude"],
                    "longitude": location["longitude"],
                    "daily": (
                        "temperature_2m_max,"
                        "temperature_2m_min,"
                        "precipitation_sum,"
                        "precipitation_probability_max,"
                        "weather_code"
                    ),
                    "timezone": "auto",
                    "start_date": requested_date.isoformat(),
                    "end_date": requested_date.isoformat(),
                },
            )
            weather_response.raise_for_status()
            data = weather_response.json()

    except httpx2.HTTPError as exc:
        return {"error": f"Weather API request failed: {exc}"}

    daily = data.get("daily", {})
    if not daily.get("time"):
        return {"error": "Forecast unavailable for the requested date."}

    return {
        "city": location["name"],
        "country": location.get("country"),
        "date": daily["time"][0],
        "temperature_max_c": daily["temperature_2m_max"][0],
        "temperature_min_c": daily["temperature_2m_min"][0],
        "precipitation_mm": daily["precipitation_sum"][0],
        "precipitation_probability_percent": daily["precipitation_probability_max"][0],
        "weather_code": daily["weather_code"][0],
        "weather_description": WEATHER_DESCRIPTIONS.get(
            daily["weather_code"][0],
            "Unknown weather condition",
        ),
    }


RESERVATIONS_FILE = Path(__file__).resolve().parent / "reservations.json"


@tool
def book_activity(
    activity: str,
    city: str,
    booking_date: str,
    people: int,
) -> dict:
    """Book an outdoor activity for a given city, date, and number of people."""

    try:
        requested_date = date.fromisoformat(booking_date)
    except ValueError:
        return {"error": "Invalid date. Use YYYY-MM-DD format."}

    if requested_date < datetime.now(UTC).date():
        return {"error": "Cannot book an activity in the past."}

    if people < 1:
        return {"error": "Number of people must be greater than zero."}

    if not activity.strip() or not city.strip():
        return {"error": "Activity and city are required."}

    if RESERVATIONS_FILE.exists():
        with RESERVATIONS_FILE.open(encoding="utf-8") as file:
            reservations = json.load(file)
    else:
        reservations = []

    reservation = {
        "id": f"RES-{uuid4().hex[:8].upper()}",
        "activity": activity,
        "city": city,
        "date": requested_date.isoformat(),
        "people": people,
    }

    reservations.append(reservation)

    with RESERVATIONS_FILE.open("w", encoding="utf-8") as file:
        json.dump(reservations, file, indent=2, ensure_ascii=False)

    return {
        "status": "confirmed",
        "reservation": reservation,
    }


if __name__ == "__main__":
    result = get_weather.invoke(
        {
            "city": "Teruel",
            "forecast_date": "2026-10-11",
        }
    )
    print(result)

    result = book_activity.invoke(
        {
            "activity": "Hiking",
            "city": "Teruel",
            "booking_date": "2026-10-11",
            "people": 3,
        }
    )
    print(result)
