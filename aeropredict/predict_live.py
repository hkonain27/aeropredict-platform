"""Apply the historical feature contract to Google Flights and hourly forecasts.

This module predicts signed scheduled-arrival delay: a negative result means an
early arrival. Google Flights supplies scheduled legs, never training labels.
Missing forecasts produce an unavailable result, not invented weather or delay.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from .airports import Airport, US_DOMESTIC_COUNTRIES, resolve_airport
from .features import (
    FEATURE_COLUMNS, RollingHistory, departure_time_features, make_flight_key,
    nearest_hour_utc, normalize_flight_identity, normalize_utc_timestamp,
)
from .providers import BudgetedClient, ProviderConfigurationError, ProviderError, search_route

LOGGER = logging.getLogger(__name__)


def parse_serpapi_flights(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize and deduplicate individual legs in best_flights/other_flights.

    A connection is multiple flights and gets separate predictions. Schedule
    times without an offset are localized at each departure airport, including
    Alaska/Hawaii. Ambiguous/nonexistent DST wall times are rejected explicitly.
    """
    if not isinstance(payload, dict):
        raise ValueError("The flight payload must be a JSON object.")
    if payload.get("error"):
        raise ProviderError("The flight payload contains a SerpApi error.")
    groups = []
    for key in ("best_flights", "other_flights"):
        value = payload.get(key, [])
        if not isinstance(value, list):
            raise ValueError(f"{key} must be an array of Google Flights itineraries.")
        groups.extend(value)
    if not groups:
        return []
    flights, seen, rejected = [], set(), 0
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("flights"), list):
            rejected += 1
            continue
        for leg in group["flights"]:
            try:
                if not isinstance(leg, dict):
                    raise ValueError("Invalid flight leg.")
                departure, arrival = leg["departure_airport"], leg["arrival_airport"]
                origin, destination = resolve_airport(departure["id"]), resolve_airport(arrival["id"])
                if any(a.country not in US_DOMESTIC_COUNTRIES for a in (origin, destination)):
                    raise ValueError("Non-domestic flight.")
                carrier, number = normalize_flight_identity(leg.get("carrier", ""), leg["flight_number"])
                scheduled = normalize_utc_timestamp(departure["time"], timezone=origin.timezone)
                key = make_flight_key(carrier, number, origin.iata, destination.iata)
                identity = (key, scheduled.isoformat())
                if identity in seen:
                    continue
                seen.add(identity)
                flights.append({
                    "carrier": carrier, "flight_number": number, "flight_key": key,
                    "origin": origin.iata, "destination": destination.iata,
                    "origin_icao": origin.icao, "scheduled_dep_utc": scheduled,
                    "scheduled_departure_local": scheduled.tz_convert(origin.timezone).isoformat(),
                    "airline": str(leg.get("airline", carrier)),
                })
            except (KeyError, TypeError, ValueError):
                rejected += 1
    if rejected:
        LOGGER.warning("Ignored %s invalid or non-domestic Google Flights legs", rejected)
    if not flights and rejected:
        raise ValueError("No valid US domestic flight legs were found; check flight numbers, airport codes, and local times.")
    return sorted(flights, key=lambda item: (item["scheduled_dep_utc"], item["flight_key"]))


def _validate_weather_location(payload: dict[str, Any], airport: Airport) -> None:
    """Require forecast coordinates near the airport to prevent location mixups."""
    try:
        latitude, longitude = float(payload["location"]["lat"]), float(payload["location"]["lon"])
    except (KeyError, TypeError, ValueError):
        raise ProviderError(f"Weather for {airport.iata} has no valid location coordinates.") from None
    if not math.isfinite(latitude) or not math.isfinite(longitude) or not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise ProviderError(f"Weather for {airport.iata} has invalid location coordinates.")
    lat1, lat2 = math.radians(latitude), math.radians(airport.latitude)
    dlat, dlon = lat2 - lat1, math.radians(airport.longitude - longitude)
    haversine = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    distance_km = 6371 * 2 * math.asin(min(1.0, math.sqrt(haversine)))
    if distance_km > 100:
        raise ProviderError(f"Forecast location is too far from {airport.iata}; provide that airport's weather.")


def _weather_numbers(hour: dict[str, Any]) -> dict[str, float]:
    source_to_feature = {
        "temp_f": "temperature_f", "wind_mph": "wind_speed_mph",
        "vis_miles": "visibility_miles", "precip_in": "precipitation_inches",
    }
    result = {}
    for source, target in source_to_feature.items():
        value = hour.get(source)
        try:
            if isinstance(value, bool):
                raise ValueError("Boolean weather value.")
            number = float(value)
        except (TypeError, ValueError):
            raise ProviderError(f"Forecast is missing a numeric {source} value.") from None
        if not math.isfinite(number) or (source != "temp_f" and number < 0):
            raise ProviderError(f"Forecast contains an invalid {source} value.")
        result[target] = number
    return result


def weather_for_departure(
    origin: str,
    scheduled_dep_utc: Any,
    *,
    payload: dict[str, Any] | None = None,
    as_of: Any = None,
    client: BudgetedClient | None = None,
) -> dict[str, Any]:
    """Select exact rounded UTC hour, using forecast epoch values across DST.

    An offline payload is either a standard WeatherAPI forecast object or an
    airport-keyed object such as {"RDU": {"location": ..., "forecast": ...}}.
    All four fields are validated; current conditions never fill a future hour.
    """
    airport = resolve_airport(origin)
    scheduled = normalize_utc_timestamp(scheduled_dep_utc, timezone="UTC")
    target = nearest_hour_utc(scheduled)
    reference = normalize_utc_timestamp(as_of) if as_of is not None else pd.Timestamp.now(tz="UTC")
    if payload is None:
        try:
            horizon = int(os.getenv("WEATHERAPI_FORECAST_DAYS", "3"))
        except ValueError:
            raise ProviderConfigurationError("WEATHERAPI_FORECAST_DAYS must be an integer from 1 to 14.") from None
        if not 1 <= horizon <= 14:
            raise ProviderConfigurationError("WEATHERAPI_FORECAST_DAYS must be an integer from 1 to 14.")
        days_ahead = (target.tz_convert(airport.timezone).date() - reference.tz_convert(airport.timezone).date()).days
        if days_ahead < 0 or days_ahead >= horizon:
            raise ProviderError(f"{airport.iata} departure is outside the configured {horizon}-day forecast window.")
        provider = client or BudgetedClient("weatherapi")
        payload = provider.get_json(
            {"q": f"{airport.latitude:.5f},{airport.longitude:.5f}", "days": horizon, "aqi": "no", "alerts": "no"},
            cache_ttl=900,
        )
    elif isinstance(payload, dict) and "location" not in payload:
        payload = payload.get(airport.iata, payload.get(airport.icao))
    if not isinstance(payload, dict) or payload.get("error"):
        raise ProviderError(f"No usable WeatherAPI response was supplied for {airport.iata}.")
    _validate_weather_location(payload, airport)
    forecast = payload.get("forecast", {})
    forecastdays = forecast.get("forecastday", []) if isinstance(forecast, dict) else []
    if not isinstance(forecastdays, list):
        raise ProviderError("WeatherAPI forecastday must be an array.")
    for day in forecastdays:
        hours = day.get("hour", []) if isinstance(day, dict) else []
        if not isinstance(hours, list):
            continue
        for hour in hours:
            if not isinstance(hour, dict):
                continue
            try:
                epoch = float(hour["time_epoch"])
            except (KeyError, TypeError, ValueError):
                continue
            if math.isfinite(epoch) and epoch == target.timestamp():
                return {**_weather_numbers(hour), "weather_hour_utc": target.isoformat(), "weather_source": "WeatherAPI hourly forecast"}
    # A fresh observation is useful only in its own current UTC hour. It cannot
    # stand in for tomorrow's missing forecast (or a rounded-up future hour).
    current = payload.get("current", {})
    if isinstance(current, dict) and target == reference.floor("h"):
        try:
            observed = pd.Timestamp(float(current["last_updated_epoch"]), unit="s", tz="UTC")
            if reference - pd.Timedelta(hours=1) <= observed <= reference and observed.floor("h") == target:
                return {**_weather_numbers(current), "weather_hour_utc": target.isoformat(), "weather_source": "WeatherAPI current observation"}
        except (KeyError, TypeError, ValueError, OverflowError):
            pass
    raise ProviderError(f"No hourly weather for {airport.iata} at {target.isoformat()}; this forecast does not cover departure.")


def load_artifact(path: str | Path) -> dict[str, Any]:
    """Load a locally trained, trusted artifact; joblib must not load user uploads."""
    model_path = Path(path)
    if not model_path.is_file():
        raise ValueError("No trained model found. Run data_prep.py and train_model.py first.")
    try:
        artifact = joblib.load(model_path)
    except Exception:
        raise ValueError("The trained model could not be loaded; retrain with the installed dependencies.") from None
    if not isinstance(artifact, dict) or artifact.get("schema_version") != 1:
        raise ValueError("Unsupported model artifact schema; retrain this model.")
    if artifact.get("feature_columns") != FEATURE_COLUMNS:
        raise ValueError("Model feature schema does not match live inference; retrain this model.")
    if not callable(getattr(artifact.get("pipeline"), "predict", None)) or not isinstance(artifact.get("history"), pd.DataFrame):
        raise ValueError("Model artifact is incomplete; retrain this model.")
    return artifact


def predict_payload(
    payload: dict[str, Any],
    artifact_path: str | Path,
    weather_payload: dict[str, Any] | None = None,
    as_of: Any = None,
) -> list[dict[str, Any]]:
    """Predict each unique domestic flight, with structured unavailable results.

    ``as_of`` must include a UTC offset when provided. It makes saved fixtures
    reproducible and determines which historical outcomes were available.
    Use trusted model paths from application configuration, never request input.
    """
    flights = parse_serpapi_flights(payload)
    if not flights:
        return []
    artifact = load_artifact(artifact_path)
    history = RollingHistory(artifact["history"])
    reference = normalize_utc_timestamp(as_of) if as_of is not None else pd.Timestamp.now(tz="UTC")
    cutoff = artifact.get("training_cutoff_utc")
    if cutoff and reference < normalize_utc_timestamp(cutoff, timezone="UTC"):
        raise ValueError("Prediction time predates the model's training cutoff; choose a model trained only on earlier outcomes.")
    results = []
    for flight in flights:
        display_number = f"{flight['carrier']}{flight['flight_number']}"
        base = {
            "flight_number": display_number, "carrier": flight["carrier"],
            "airline": flight["airline"], "origin": flight["origin"], "destination": flight["destination"],
            "scheduled_dep_utc": flight["scheduled_dep_utc"].isoformat(),
            "scheduled_departure_local": flight["scheduled_departure_local"],
        }
        try:
            if flight["scheduled_dep_utc"] <= reference:
                raise ValueError("This engine predicts before scheduled departure; select a future flight.")
            airport = resolve_airport(flight["origin"])
            trained_horizon = float(artifact.get('forecast_horizon_hours', 0))
            history_cutoff = min(reference, flight['scheduled_dep_utc'] - pd.Timedelta(hours=trained_horizon))
            prior = history.lookup(flight["flight_key"], history_cutoff, flight["scheduled_dep_utc"])
            weather = weather_for_departure(
                flight["origin"], flight["scheduled_dep_utc"], payload=weather_payload, as_of=reference,
            )
            features = {**flight, **departure_time_features(flight["scheduled_dep_utc"], airport.timezone), **prior, **weather}
            matrix = pd.DataFrame([{name: features[name] for name in FEATURE_COLUMNS}], columns=FEATURE_COLUMNS)
            prediction = float(artifact["pipeline"].predict(matrix)[0])
            if not math.isfinite(prediction):
                raise ValueError("The model returned a non-finite prediction; retrain and validate this artifact.")
            minutes = round(prediction, 1)
            timing = f"{minutes:.1f} minutes late" if minutes >= 0 else f"{abs(minutes):.1f} minutes early"
            message = f"Flight {display_number} from {flight['origin']} is predicted to be {timing}."
            metrics = artifact.get("metrics", {})
            results.append({
                **base, "status": "ok", "predicted_arrival_delay_minutes": minutes,
                "history_sample_count": prior["hist_flight_num_delay_count"],
                "historical_delay_average_minutes": prior["hist_flight_num_delay_avg"],
                "weather_source": weather["weather_source"], "weather_hour_utc": weather["weather_hour_utc"],
                "model_trained_at_utc": artifact.get("trained_at_utc"),
                "evaluation_mae_minutes": metrics.get('model', {}).get('mae_minutes'),
                "evaluation_applies_to_saved_model": metrics.get('metrics_apply_to_saved_model', False),
                "trained_forecast_horizon_hours": trained_horizon,
                "actual_forecast_horizon_hours": (flight['scheduled_dep_utc'] - reference).total_seconds()/3600,
                "history_information_cutoff_utc": history_cutoff.isoformat(),
                "history_fallback_used": prior['hist_flight_num_delay_count'] == 0,
                "message": message,
            })
        except (ProviderError, ValueError, KeyError, TypeError) as error:
            # Our provider exceptions exclude URLs, keys, and raw response bodies.
            LOGGER.warning("Prediction unavailable for %s: %s", display_number, type(error).__name__)
            results.append({**base, "status": "unavailable", "error": str(error)})
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Predict US domestic arrival-delay minutes with a trained XGBoost model.")
    parser.add_argument("--model", default=os.getenv("MODEL_ARTIFACT_PATH", "artifacts/model.joblib"), help="Trusted local model.joblib path")
    parser.add_argument("--flights-json", type=Path, help="Saved SerpApi JSON for offline inference")
    parser.add_argument("--weather-json", type=Path, help="Saved WeatherAPI JSON or airport-keyed forecasts")
    parser.add_argument("--origin", help="Origin airport code for a live route search")
    parser.add_argument("--destination", help="Destination airport code for a live route search")
    parser.add_argument("--date", help="Departure date YYYY-MM-DD")
    parser.add_argument("--as-of", help="Prediction information cutoff with timezone, for reproducible offline fixtures")
    parser.add_argument("--json", action="store_true", help="Print structured prediction results")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if args.flights_json and any((args.origin, args.destination, args.date)):
        parser.error("Use either --flights-json or --origin/--destination/--date.")
    if not args.flights_json and not all((args.origin, args.destination, args.date)):
        parser.error("Provide --flights-json or all of --origin, --destination, and --date.")
    if args.as_of and not (args.flights_json and args.weather_json):
        parser.error("--as-of requires saved flight and weather files; current API calls cannot reproduce past forecasts.")
    try:
        # Validate the model before a search can spend even a single request.
        load_artifact(args.model)
        flights = json.loads(args.flights_json.read_text(encoding="utf-8")) if args.flights_json else search_route(args.origin, args.destination, args.date)
        weather = json.loads(args.weather_json.read_text(encoding="utf-8")) if args.weather_json else None
        results = predict_payload(flights, args.model, weather_payload=weather, as_of=args.as_of)
        if args.json:
            print(json.dumps(results, indent=2, allow_nan=False))
        elif not results:
            print("No matching flights were returned by Google Flights.")
        else:
            for result in results:
                print(result.get("message") or f"Flight {result['flight_number']}: prediction unavailable. {result['error']}")
        return 0 if results and all(result["status"] == "ok" for result in results) else 2
    except (OSError, ValueError, ProviderError) as error:
        LOGGER.error("%s", error)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
