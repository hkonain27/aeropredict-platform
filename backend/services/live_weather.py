import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


AVIATION_WEATHER_BASE = "https://aviationweather.gov/api/data"
CACHE_TTL_SECONDS = 60
USER_AGENT = "AeroPredict/1.0 aviation-intelligence-platform"

_METAR_CACHE = {}


def iata_to_icao(airport_code):
    airport_code = str(airport_code).upper().strip()

    if len(airport_code) == 4:
        return airport_code

    if len(airport_code) == 3:
        return f"K{airport_code}"

    return airport_code


def _parse_number(value):
    if value in [None, ""]:
        return None

    if isinstance(value, (int, float)):
        return value

    text = str(value).strip().replace("+", "")
    try:
        return float(text)
    except ValueError:
        return None


def _weather_unavailable(station, message, cached=False):
    return {
        "available": False,
        "station": station,
        "cached": cached,
        "message": message,
    }


def _normalize_metar(station, metar, cached=False):
    return {
        "available": True,
        "station": station,
        "cached": cached,
        "raw_text": metar.get("rawOb"),
        "flight_category": metar.get("fltCat"),
        "temperature_c": _parse_number(metar.get("temp")),
        "dewpoint_c": _parse_number(metar.get("dewp")),
        "wind_direction": _parse_number(metar.get("wdir")),
        "wind_speed_kt": _parse_number(metar.get("wspd")),
        "wind_gust_kt": _parse_number(metar.get("wgst")),
        "visibility_miles": _parse_number(metar.get("visib")),
        "altimeter": _parse_number(metar.get("altim")),
        "observation_time": metar.get("reportTime"),
    }


def _read_cached_metar(station):
    cached = _METAR_CACHE.get(station)
    if not cached:
        return None

    fetched_at, payload = cached
    if time.time() - fetched_at > CACHE_TTL_SECONDS:
        return None

    return {**payload, "cached": True}


def get_live_metar(airport_code):
    station = iata_to_icao(airport_code)
    cached = _read_cached_metar(station)
    if cached:
        return cached

    query = urlencode({"ids": station, "format": "json"})
    request = Request(
        f"{AVIATION_WEATHER_BASE}/metar?{query}",
        headers={"User-Agent": USER_AGENT},
    )

    try:
        with urlopen(request, timeout=8) as response:
            if response.status == 204:
                data = None
            else:
                body = response.read().decode("utf-8")
                data = json.loads(body) if body else None
    except HTTPError as exc:
        if exc.code == 204:
            payload = _weather_unavailable(station, "No recent METAR available.")
        elif exc.code == 429:
            payload = _weather_unavailable(station, "Weather API rate limit reached.")
        else:
            payload = _weather_unavailable(station, f"Weather API returned HTTP {exc.code}.")
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        payload = _weather_unavailable(station, f"Weather API request failed: {exc}")
    else:
        if data is None:
            payload = _weather_unavailable(station, "No recent METAR available.")
        elif not data:
            payload = _weather_unavailable(station, "No weather report returned.")
        else:
            payload = _normalize_metar(station, data[0])

    _METAR_CACHE[station] = (time.time(), payload)
    return payload


def score_weather_risk(weather):
    if not weather.get("available"):
        return {
            "level": "Unknown",
            "score": 0,
            "drivers": [weather.get("message", "Live weather was not available.")],
        }

    score = 0
    drivers = []
    raw_text = (weather.get("raw_text") or "").upper()
    flight_category = weather.get("flight_category")
    visibility = _parse_number(weather.get("visibility_miles"))
    wind_speed = _parse_number(weather.get("wind_speed_kt"))
    wind_gust = _parse_number(weather.get("wind_gust_kt"))

    if flight_category in ["IFR", "LIFR"]:
        score += 3
        drivers.append(f"Flight category is {flight_category}.")
    elif flight_category == "MVFR":
        score += 1
        drivers.append("Flight category is MVFR.")

    if visibility is not None and visibility < 3:
        score += 2
        drivers.append(f"Visibility is low at {visibility:g} miles.")

    if wind_speed is not None and wind_speed >= 25:
        score += 2
        drivers.append(f"Sustained winds are {wind_speed:g} kt.")

    if wind_gust is not None and wind_gust >= 30:
        score += 2
        drivers.append(f"Wind gusts are {wind_gust:g} kt.")

    if "TS" in raw_text:
        score += 3
        drivers.append("Thunderstorms are reported in the METAR.")

    if any(token in raw_text for token in ["SN", "FZRA", "FZDZ", "PL"]):
        score += 3
        drivers.append("Winter precipitation is reported in the METAR.")

    if score >= 5:
        level = "High"
    elif score >= 2:
        level = "Moderate"
    else:
        level = "Low"

    if not drivers:
        drivers.append("No major live-weather delay signal detected.")

    return {
        "level": level,
        "score": score,
        "drivers": drivers,
    }
