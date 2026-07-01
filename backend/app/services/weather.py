"""Shared current-weather fetch (OpenWeatherMap). Used by both the recommend
placeholder text (D-17) and course generation stage planning (D-26/SCRUM-78)."""
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def fetch_weather() -> dict | None:
    """Fetch Seoul weather from OpenWeatherMap. Returns None on any failure."""
    api_key = settings.OPENWEATHER_API_KEY
    if not api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"q": "Seoul,KR", "appid": api_key, "units": "metric", "lang": "kr"},
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "temp": round(data["main"]["temp"], 1),
                "feels_like": round(data["main"]["feels_like"], 1),
                "description": data["weather"][0]["description"],
                "main": data["weather"][0]["main"],
                "icon": data["weather"][0]["icon"],
            }
    except Exception as exc:
        logger.warning("Weather API failed: %s", exc)
        return None
