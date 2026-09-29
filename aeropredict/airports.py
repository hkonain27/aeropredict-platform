"""Airport identifiers and IANA time zones, without guessing an ICAO prefix.

The airportsdata reference includes small airports as well as major hubs. An
optional override mapping is useful for a private airfield or corrected record.
"""

from dataclasses import dataclass
from functools import lru_cache
from typing import Mapping


US_DOMESTIC_COUNTRIES = frozenset({"US", "PR", "VI", "GU", "AS", "MP"})


@dataclass(frozen=True)
class Airport:
    iata: str
    icao: str
    timezone: str
    latitude: float
    longitude: float
    country: str


@lru_cache(maxsize=1)
def _airport_index() -> dict:
    try:
        import airportsdata
    except ImportError as exc:
        raise RuntimeError("Airport references are missing; install requirements.txt first.") from exc
    index = airportsdata.load("ICAO")
    index.update(airportsdata.load("IATA"))
    return index


def resolve_airport(code: str, overrides: Mapping | None = None) -> Airport:
    """Resolve IATA or ICAO to a complete airport reference; reject unknown codes."""
    code = str(code).strip().upper()
    record = (overrides or {}).get(code)
    if record is None:
        record = _airport_index().get(code)
    if record is None:
        raise ValueError(f"Unknown airport {code!r}; supply an airport override with its time zone.")
    if isinstance(record, Airport):
        return record
    try:
        return Airport(
            iata=str(record.get("iata") or code).upper(),
            icao=str(record["icao"]).upper(),
            timezone=str(record.get("timezone") or record["tz"]),
            latitude=float(record.get("latitude", record.get("lat"))),
            longitude=float(record.get("longitude", record.get("lon"))),
            country=str(record["country"]).upper(),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Incomplete airport reference for {code!r}: {exc}") from exc
