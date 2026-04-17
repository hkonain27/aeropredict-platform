import json
from functools import lru_cache
from pathlib import Path


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "flight_2024_context.json"


@lru_cache(maxsize=1)
def load_flight_2024_data():
    if not DATA_PATH.exists():
        return None

    with open(DATA_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _lookup(data, section, parts):
    key = "|".join(str(part) for part in parts)
    return data.get(section, {}).get(key)


def get_flight_2024_context(carrier, airport, month):
    data = load_flight_2024_data()
    carrier = str(carrier).upper().strip()
    airport = str(airport).upper().strip()
    month = int(month)

    if not data:
        return {
            "available": False,
            "message": "2024 flight-record context is not available.",
        }

    candidates = [
        ("exact", _lookup(data, "exact", [carrier, airport, month])),
        ("airport_month", _lookup(data, "airport_month", [airport, month])),
        ("carrier_month", _lookup(data, "carrier_month", [carrier, month])),
        ("month", _lookup(data, "month", [month])),
    ]

    for group_type, summary in candidates:
        if summary:
            return {
                "available": True,
                "source": data.get("source"),
                "group_type": group_type,
                "exact_match": group_type == "exact",
                "summary": summary,
            }

    return {
        "available": False,
        "source": data.get("source"),
        "message": "No 2024 flight-record context matched this scenario.",
    }


def score_flight_2024_context(context):
    if not context.get("available"):
        return {
            "level": "Unknown",
            "drivers": [context.get("message", "2024 flight-record context was not available.")],
        }

    summary = context["summary"]
    delay_rate = summary.get("delay_rate") or 0
    cancellation_rate = summary.get("cancellation_rate") or 0
    diversion_rate = summary.get("diversion_rate") or 0
    completed_flights = summary.get("completed_flights") or 0

    drivers = []
    score = 0

    if completed_flights < 50:
        drivers.append("2024 evidence is limited because fewer than 50 completed flights matched.")

    if delay_rate >= 0.25:
        score += 2
        drivers.append(f"2024 delay rate was {delay_rate * 100:.1f}%.")
    elif delay_rate >= 0.20:
        score += 1
        drivers.append(f"2024 delay rate was {delay_rate * 100:.1f}%.")

    if cancellation_rate >= 0.05:
        score += 2
        drivers.append(f"2024 cancellation rate was {cancellation_rate * 100:.1f}%.")
    elif cancellation_rate >= 0.025:
        score += 1
        drivers.append(f"2024 cancellation rate was {cancellation_rate * 100:.1f}%.")

    if diversion_rate >= 0.01:
        score += 1
        drivers.append(f"2024 diversion rate was {diversion_rate * 100:.1f}%.")

    top_cause = summary.get("top_delay_cause")
    if top_cause:
        drivers.append(f"Top 2024 delay cause was {top_cause['name']}.")

    if score >= 3:
        level = "High"
    elif score >= 1:
        level = "Moderate"
    else:
        level = "Low"
        drivers.append("2024 flight records do not add a major delay signal.")

    return {
        "level": level,
        "drivers": drivers,
    }
