MORNING_FOG_AIRPORTS = {"SFO", "SEA", "PDX", "BOS", "JFK", "EWR"}
WINTER_DISRUPTION_AIRPORTS = {"ORD", "DEN", "MSP", "DTW", "BOS", "JFK", "EWR", "BUF", "SLC"}
STORM_PRONE_AIRPORTS = {"ATL", "MCO", "MIA", "CLT", "DFW", "IAH", "ORD", "BNA", "TPA", "FLL"}
COASTAL_WIND_AIRPORTS = {"SFO", "LGA", "JFK", "BOS", "SAN", "SEA", "MIA"}


def _add_driver(drivers, label, detail, severity):
    drivers.append(
        {
            "label": label,
            "detail": detail,
            "severity": severity,
        }
    )


def build_weather_context(origin, destination, dep_hour, distance):
    origin = str(origin).upper().strip()
    destination = str(destination).upper().strip()
    dep_hour = int(dep_hour)
    distance = int(distance)

    drivers = []
    risk_score = 0

    if dep_hour <= 8 and ({origin, destination} & MORNING_FOG_AIRPORTS):
        _add_driver(
            drivers,
            "Morning low-visibility exposure",
            "Early departures at coastal or fog-prone airports can face visibility-related slowdowns.",
            "moderate",
        )
        risk_score += 1

    if dep_hour >= 15 and ({origin, destination} & STORM_PRONE_AIRPORTS):
        _add_driver(
            drivers,
            "Late-day thunderstorm exposure",
            "Afternoon and evening flights through storm-prone hubs often see weather-related flow delays.",
            "high",
        )
        risk_score += 2

    if {origin, destination} & WINTER_DISRUPTION_AIRPORTS:
        _add_driver(
            drivers,
            "Seasonal winter sensitivity",
            "This route touches airports that often experience snow, de-icing, or winter weather disruptions.",
            "moderate",
        )
        risk_score += 1

    if {origin, destination} & COASTAL_WIND_AIRPORTS:
        _add_driver(
            drivers,
            "Coastal wind exposure",
            "Coastal airports can be more sensitive to strong winds, low ceilings, and marine weather changes.",
            "low",
        )
        risk_score += 1

    if distance >= 1800:
        _add_driver(
            drivers,
            "Long-haul routing sensitivity",
            "Longer routes have more opportunity to absorb weather-driven traffic management constraints along the way.",
            "low",
        )
        risk_score += 1

    if not drivers:
        drivers.append(
            {
                "label": "No major route-specific weather flag",
                "detail": "This route does not trigger any of the broad airport climate heuristics used for weather context.",
                "severity": "low",
            }
        )

    if risk_score >= 4:
        headline = "Elevated weather watch"
        summary = "This route has several typical weather-related exposure points worth monitoring."
    elif risk_score >= 2:
        headline = "Moderate weather watch"
        summary = "There are some common weather patterns that can affect operations on this route."
    else:
        headline = "Low weather watch"
        summary = "No major weather-sensitive pattern stands out from the route heuristics alone."

    return {
        "headline": headline,
        "summary": summary,
        "drivers": drivers,
        "disclaimer": "This weather context is informational and is not currently used by the prediction model.",
    }
