import csv
import json
import time
from calendar import monthrange
from io import StringIO
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from services.live_weather import USER_AGENT, iata_to_icao


IEM_ASOS_BASE = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
IEM_SOURCE_NAME = "Iowa State IEM ASOS/METAR archive"
IEM_SOURCE_URL = "https://mesonet.agron.iastate.edu/request/download.phtml"
REFERENCE_YEAR = 2024
CACHE_TTL_SECONDS = 60 * 60 * 24
UNAVAILABLE_MESSAGE = "Historical airport weather is not currently available for this airport and month."

_HISTORICAL_WEATHER_CACHE = {}


def _parse_float(value):
    if value in [None, ""]:
        return None

    text = str(value).strip().replace("+", "")
    try:
        return float(text)
    except ValueError:
        return None


def _station_candidates(airport_code):
    airport = str(airport_code).upper().strip()
    icao = iata_to_icao(airport)
    candidates = [airport]

    if icao not in candidates:
        candidates.append(icao)

    return candidates


def _empty_context(airport_code, month, station=None, message=UNAVAILABLE_MESSAGE, cached=False):
    return {
        "available": False,
        "airport": str(airport_code).upper().strip(),
        "station": station,
        "month": int(month),
        "reference_year": REFERENCE_YEAR,
        "source": IEM_SOURCE_NAME,
        "source_url": IEM_SOURCE_URL,
        "cached": cached,
        "message": message,
    }


def _read_cached_context(airport_code, month):
    cache_key = (str(airport_code).upper().strip(), int(month))
    cached = _HISTORICAL_WEATHER_CACHE.get(cache_key)
    if not cached:
        return None

    fetched_at, payload = cached
    if time.time() - fetched_at > CACHE_TTL_SECONDS:
        return None

    return {**payload, "cached": True}


def _build_iem_url(station, month):
    last_day = monthrange(REFERENCE_YEAR, int(month))[1]
    params = [
        ("station", station),
        ("year1", REFERENCE_YEAR),
        ("month1", int(month)),
        ("day1", 1),
        ("year2", REFERENCE_YEAR),
        ("month2", int(month)),
        ("day2", last_day),
        ("tz", "UTC"),
        ("format", "onlycomma"),
        ("latlon", "no"),
        ("elev", "no"),
        ("missing", "empty"),
        ("trace", "empty"),
        ("direct", "no"),
        ("report_type", "3"),
        ("report_type", "4"),
    ]

    # Keep this list intentionally small. These fields are enough to create a
    # weather-risk signal without downloading the full ASOS/METAR record.
    for field in ["tmpf", "sknt", "gust", "vsby", "p01i", "skyc1", "skyl1", "wxcodes", "metar"]:
        params.append(("data", field))

    return f"{IEM_ASOS_BASE}?{urlencode(params)}"


def _fetch_iem_rows(station, month):
    request = Request(_build_iem_url(station, month), headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=10) as response:
        body = response.read().decode("utf-8")

    reader = csv.DictReader(StringIO(body))
    return [row for row in reader if row.get("station") and row.get("valid")]


def _percent(count, total):
    if total <= 0:
        return 0
    return round(count / total, 4)


def _summarize_rows(airport_code, station, month, rows, cached=False):
    observations = len(rows)
    visibility_values = []
    wind_values = []
    gust_values = []
    low_visibility = 0
    low_ceiling = 0
    gusty_wind = 0
    precipitation = 0
    thunderstorms = 0
    winter_precip = 0

    for row in rows:
        visibility = _parse_float(row.get("vsby"))
        wind = _parse_float(row.get("sknt"))
        gust = _parse_float(row.get("gust"))
        precipitation_inches = _parse_float(row.get("p01i"))
        ceiling = _parse_float(row.get("skyl1"))
        sky_cover = (row.get("skyc1") or "").upper()
        weather_codes = (row.get("wxcodes") or "").upper()
        raw_metar = (row.get("metar") or "").upper()
        weather_text = f"{weather_codes} {raw_metar}"
        row_has_gusty_wind = False

        if visibility is not None:
            visibility_values.append(visibility)
            if visibility < 3:
                low_visibility += 1

        if wind is not None:
            wind_values.append(wind)
            if wind >= 25:
                row_has_gusty_wind = True

        if gust is not None:
            gust_values.append(gust)
            if gust >= 30:
                row_has_gusty_wind = True

        if row_has_gusty_wind:
            gusty_wind += 1

        if precipitation_inches is not None and precipitation_inches > 0:
            precipitation += 1

        if ceiling is not None and ceiling < 1000 and sky_cover in {"BKN", "OVC", "VV"}:
            low_ceiling += 1

        if "TS" in weather_text:
            thunderstorms += 1

        if any(token in weather_text for token in ["SN", "FZRA", "FZDZ", "PL"]):
            winter_precip += 1

    return {
        "available": True,
        "airport": str(airport_code).upper().strip(),
        "station": station,
        "month": int(month),
        "reference_year": REFERENCE_YEAR,
        "source": IEM_SOURCE_NAME,
        "source_url": IEM_SOURCE_URL,
        "cached": cached,
        "observations": observations,
        "avg_visibility_miles": round(sum(visibility_values) / len(visibility_values), 1) if visibility_values else None,
        "avg_wind_speed_kt": round(sum(wind_values) / len(wind_values), 1) if wind_values else None,
        "max_gust_kt": round(max(gust_values), 1) if gust_values else None,
        "low_visibility_rate": _percent(low_visibility, observations),
        "low_ceiling_rate": _percent(low_ceiling, observations),
        "gusty_wind_rate": _percent(gusty_wind, observations),
        "precipitation_rate": _percent(precipitation, observations),
        "thunderstorm_rate": _percent(thunderstorms, observations),
        "winter_precip_rate": _percent(winter_precip, observations),
        "message": f"Historical ASOS/METAR summary for {station} in {REFERENCE_YEAR}-{int(month):02d}.",
    }


def get_historical_weather_context(airport_code, month):
    cached = _read_cached_context(airport_code, month)
    if cached:
        return cached

    cache_key = (str(airport_code).upper().strip(), int(month))
    payload = None

    for station in _station_candidates(airport_code):
        try:
            rows = _fetch_iem_rows(station, month)
        except HTTPError as exc:
            payload = _empty_context(airport_code, month, station, f"Historical weather API returned HTTP {exc.code}.")
            continue
        except (URLError, TimeoutError, csv.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
            payload = _empty_context(airport_code, month, station, f"Historical weather API request failed: {exc}")
            continue

        if rows:
            payload = _summarize_rows(airport_code, station, month, rows)
            break

        payload = _empty_context(airport_code, month, station)

    if payload is None:
        payload = _empty_context(airport_code, month)

    _HISTORICAL_WEATHER_CACHE[cache_key] = (time.time(), payload)
    return payload


def _quality_from_observations(observations):
    if observations >= 500:
        return 1.0
    if observations >= 150:
        return 0.75
    if observations >= 40:
        return 0.5
    if observations > 0:
        return 0.25
    return 0


def score_historical_weather_context(context):
    if not context.get("available"):
        return {
            "level": "Unknown",
            "score": 0,
            "quality": 0,
            "drivers": [context.get("message", UNAVAILABLE_MESSAGE)],
        }

    low_visibility = context.get("low_visibility_rate") or 0
    low_ceiling = context.get("low_ceiling_rate") or 0
    gusty_wind = context.get("gusty_wind_rate") or 0
    precipitation = context.get("precipitation_rate") or 0
    thunderstorms = context.get("thunderstorm_rate") or 0
    winter_precip = context.get("winter_precip_rate") or 0

    pressure = (
        (max(low_visibility, low_ceiling) * 0.35)
        + (gusty_wind * 0.20)
        + (precipitation * 0.20)
        + (thunderstorms * 0.15)
        + (winter_precip * 0.10)
    )
    pressure = round(pressure, 4)

    if pressure >= 0.18:
        level = "High"
        score = 0.78
    elif pressure >= 0.08:
        level = "Moderate"
        score = 0.55
    else:
        level = "Low"
        score = 0.28

    drivers = []
    if low_visibility >= 0.05:
        drivers.append(f"{low_visibility * 100:.1f}% of observations had visibility below 3 miles.")
    if low_ceiling >= 0.05:
        drivers.append(f"{low_ceiling * 100:.1f}% of observations had a low ceiling.")
    if gusty_wind >= 0.05:
        drivers.append(f"{gusty_wind * 100:.1f}% of observations had strong winds or gusts.")
    if precipitation >= 0.10:
        drivers.append(f"{precipitation * 100:.1f}% of observations reported precipitation.")
    if thunderstorms >= 0.02:
        drivers.append(f"{thunderstorms * 100:.1f}% of observations reported thunderstorms.")
    if winter_precip >= 0.02:
        drivers.append(f"{winter_precip * 100:.1f}% of observations reported winter precipitation.")

    if not drivers:
        drivers.append("Historical weather did not show a major disruption pattern for this month.")

    return {
        "level": level,
        "score": score,
        "quality": _quality_from_observations(context.get("observations") or 0),
        "pressure": pressure,
        "drivers": drivers,
    }
