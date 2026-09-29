"""Normalize BTS flight CSVs and hourly airport weather into a training matrix.

This job is deliberately offline. It reads user-supplied archives, performs an
auditable UTC/hourly inner join, and never spends an API request. Historical
observations are a training proxy for forecast weather, not archived forecasts.
"""

import argparse
from collections import Counter
import glob
import json
import logging
from pathlib import Path
import re
import sys

import numpy as np
import pandas as pd

from .airports import resolve_airport, US_DOMESTIC_COUNTRIES
from .features import (
    FEATURE_COLUMNS, TARGET_COLUMN, build_history_features,
    normalize_flight_identity,
)


LOGGER = logging.getLogger(__name__)


def _normalized_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _column(frame: pd.DataFrame, *aliases: str, required: bool = False) -> str | None:
    names = {_normalized_name(str(name)): name for name in frame.columns}
    for alias in aliases:
        if _normalized_name(alias) in names:
            return names[_normalized_name(alias)]
    if required:
        raise ValueError(f"Missing required CSV column; accepted names: {', '.join(aliases)}")
    return None


def expand_paths(patterns) -> list[Path]:
    """Expand globs ourselves so PowerShell and Unix shells behave identically."""
    paths = []
    for pattern in patterns:
        matches = sorted(glob.glob(str(pattern)))
        if not matches:
            raise ValueError(f"No input files matched {pattern!r}.")
        paths.extend(Path(path).resolve() for path in matches)
    return list(dict.fromkeys(paths))


def load_csvs(patterns) -> pd.DataFrame:
    paths = expand_paths(patterns)
    if sum(path.stat().st_size for path in paths) > 500_000_000:
        LOGGER.warning("Large CSV input: allow several times the input size in RAM; prepare a regional/year subset if needed.")
    frames = []
    for path in paths:
        with path.open("rb") as stream:
            if stream.read(80).startswith(b"version https://git-lfs.github.com/spec/v1"):
                raise ValueError(f"{path} is a Git LFS pointer, not a downloaded CSV.")
        try:
            frames.append(pd.read_csv(path, low_memory=False))
        except (pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
            raise ValueError(f"Cannot parse CSV {path}: {exc}") from exc
    return pd.concat(frames, ignore_index=True)


def _utc_series(values: pd.Series) -> pd.Series:
    # Names ending in UTC explicitly define naive values as UTC.
    return pd.to_datetime(values, utc=True, errors="coerce", format="mixed")


def _hhmm_minutes(values: pd.Series) -> pd.Series:
    """Accept BTS numeric HHMM and human HH:MM; 2400 is next-day midnight."""
    text = values.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
    text = text.str.replace(":", "", regex=False)
    valid_shape = text.str.fullmatch(r"\d{1,4}", na=False)
    numeric = pd.to_numeric(text.where(valid_shape), errors="coerce")
    hours, minutes = numeric // 100, numeric % 100
    valid_time = ((hours >= 0) & (hours < 24) & (minutes < 60)) | (numeric == 2400)
    return (hours * 60 + minutes).where(valid_time)


def normalize_flights(
    raw: pd.DataFrame, *, assumed_outcome_lag_hours: float | None = None,
    horizon_hours: float = 0.0, outcome_reporting_lag_hours: float = 0.0,
    airport_overrides: dict | None = None, drop_invalid: bool = False,
) -> tuple[pd.DataFrame, dict]:
    """Normalize one or many BTS archives, preserving only completed domestic flights.

    Minimal files without actual completion timestamps require a user-selected
    outcome lag. That assumption is retained in the audit; it cannot establish
    the exact instant an outcome was published. For reliable history use actual
    arrival UTC or BTS departure delay plus actual elapsed flight minutes.
    """
    if horizon_hours < 0 or outcome_reporting_lag_hours < 0:
        raise ValueError("Forecast horizon and reporting lag must be nonnegative.")
    if assumed_outcome_lag_hours is not None and assumed_outcome_lag_hours <= 0:
        raise ValueError("Assumed outcome lag must be positive.")
    audit = Counter(input_flight_rows=len(raw))
    frame = raw.copy()
    target = _column(frame, "arr_delay_min", "ARR_DELAY", "ArrDelay", "actual_arrival_delay_mins", "Actual Arrival Delay Minutes", required=True)
    excluded = pd.Series(False, index=frame.index)
    for alias in ("CANCELLED", "DIVERTED"):
        source = _column(frame, alias)
        if source:
            flagged = pd.to_numeric(frame[source], errors="coerce").fillna(0) != 0
            audit[f"excluded_{alias.lower()}"] = int(flagged.sum())
            excluded |= flagged
    numeric_target = pd.to_numeric(frame[target], errors="coerce")
    unknown_outcome = numeric_target.isna() | ~np.isfinite(numeric_target)
    audit["excluded_missing_outcome"] = int((unknown_outcome & ~excluded).sum())
    frame = frame.loc[~(excluded | unknown_outcome)].copy().reset_index(drop=True)
    result = pd.DataFrame(index=frame.index)
    result[TARGET_COLUMN] = pd.to_numeric(frame[target], errors="raise")
    number_col = _column(frame, "flight_number", "FL_NUM", "OP_CARRIER_FL_NUM", "OP_UNIQUE_CARRIER_FL_NUM", "Flight Number", "Reporting_Airline_Flight_Number", "Flight_Number_Reporting_Airline", required=True)
    carrier_col = _column(frame, "carrier", "OP_UNIQUE_CARRIER", "OP_CARRIER", "Reporting_Airline", "UNIQUE_CARRIER", "IATA_CODE_Reporting_Airline", "airline")
    if not carrier_col:
        # Prefixed values such as MX123 can supply the carrier, bare 123 cannot.
        carriers = pd.Series("", index=frame.index)
    else:
        carriers = frame[carrier_col]
    identities = {}
    for carrier, number in zip(carriers, frame[number_col]):
        key = (str(carrier), str(number))
        if key not in identities:
            try:
                identities[key] = normalize_flight_identity(carrier, number)
            except ValueError:
                identities[key] = (None, None)
    normalized = [identities[(str(carrier), str(number))] for carrier, number in zip(carriers, frame[number_col])]
    result["carrier"] = [item[0] for item in normalized]
    result["flight_number"] = [item[1] for item in normalized]
    origin_col = _column(frame, "origin", "ORIGIN_AIRPORT", "Origin Airport", "origin_airport_iata", "origin_airport_icao", required=True)
    destination_col = _column(frame, "destination", "DEST", "Destination Airport", "destination_airport_iata", "destination_airport_icao", required=True)
    origins = frame[origin_col].astype("string").str.strip().str.upper()
    destinations = frame[destination_col].astype("string").str.strip().str.upper()
    references = {}
    for code in set(origins.dropna()) | set(destinations.dropna()):
        try:
            references[code] = resolve_airport(code, airport_overrides)
        except ValueError:
            references[code] = None
    for output, source in (("origin", origins), ("destination", destinations)):
        result[output] = source.map(lambda code: references[code].iata if references.get(code) else None)
    result["origin_icao"] = origins.map(lambda code: references[code].icao if references.get(code) else None)
    result["origin_timezone"] = origins.map(lambda code: references[code].timezone if references.get(code) else None)
    domestic = origins.map(lambda code: references[code].country in US_DOMESTIC_COUNTRIES if references.get(code) else False)
    domestic &= destinations.map(lambda code: references[code].country in US_DOMESTIC_COUNTRIES if references.get(code) else False)
    known_airports = result.origin.notna() & result.destination.notna()
    excluded_international = known_airports & ~domestic
    audit["excluded_international"] = int(excluded_international.sum())
    utc_col = _column(frame, "scheduled_dep_utc", "scheduled_departure_time_utc", "scheduled_departure_utc")
    if utc_col:
        result["scheduled_dep_utc"] = _utc_series(frame[utc_col])
    else:
        date_col = _column(frame, "FL_DATE", "FlightDate", "Flight Date", required=True)
        time_col = _column(frame, "CRS_DEP_TIME", "CRSDepTime", "Scheduled Departure Time", required=True)
        # Numeric YYYYMMDD is a calendar date, never Unix nanoseconds.
        dates = pd.to_datetime(frame[date_col].astype('string'), errors="coerce", format="mixed").dt.normalize()
        naive = dates + pd.to_timedelta(_hhmm_minutes(frame[time_col]), unit="m")
        result["scheduled_dep_utc"] = pd.Series(pd.NaT, dtype="datetime64[ns, UTC]", index=result.index)
        for timezone, indices in result.groupby("origin_timezone").groups.items():
            # Ambiguous and nonexistent DST times are rejected below, never guessed.
            localized = naive.loc[indices].dt.tz_localize(timezone, ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC")
            result.loc[indices, "scheduled_dep_utc"] = localized
    arrival_col = _column(frame, "actual_arrival_utc", "actual_arrival_time_utc", "outcome_available_utc")
    departure_delay_col = _column(frame, "DEP_DELAY", "DepDelay", "departure_delay_min")
    elapsed_col = _column(frame, "ACTUAL_ELAPSED_TIME", "ActualElapsedTime")
    scheduled_elapsed_col = _column(frame, "CRS_ELAPSED_TIME", "CRSElapsedTime")
    if arrival_col:
        result["outcome_available_utc"] = _utc_series(frame[arrival_col])
        outcome_method = str(arrival_col)
    elif departure_delay_col and elapsed_col:
        minutes = pd.to_numeric(frame[departure_delay_col], errors="coerce") + pd.to_numeric(frame[elapsed_col], errors="coerce")
        result["outcome_available_utc"] = result.scheduled_dep_utc + pd.to_timedelta(minutes, unit="m")
        outcome_method = "scheduled departure + departure delay + actual elapsed minutes"
    elif scheduled_elapsed_col:
        minutes = pd.to_numeric(frame[scheduled_elapsed_col], errors="coerce") + result[TARGET_COLUMN]
        result["outcome_available_utc"] = result.scheduled_dep_utc + pd.to_timedelta(minutes, unit="m")
        outcome_method = "scheduled departure + scheduled elapsed minutes + arrival delay"
    elif assumed_outcome_lag_hours is not None:
        result["outcome_available_utc"] = result.scheduled_dep_utc + pd.Timedelta(hours=assumed_outcome_lag_hours)
        outcome_method = f"ASSUMED completion after {assumed_outcome_lag_hours:g} hours"
    else:
        raise ValueError("Outcome availability is required to prevent leakage. Include actual_arrival_utc, or DEP_DELAY + ACTUAL_ELAPSED_TIME, or CRS_ELAPSED_TIME. For a minimal archive explicitly set --assumed-outcome-lag-hours (for example 48); this is an assumption, not observed arrival timing.")
    result["outcome_available_utc"] += pd.Timedelta(hours=outcome_reporting_lag_hours)
    result["prediction_as_of_utc"] = result.scheduled_dep_utc - pd.Timedelta(hours=horizon_hours)
    invalid = result[["carrier", "flight_number", "origin", "destination", "scheduled_dep_utc", "outcome_available_utc"]].isna().any(axis=1)
    invalid |= result.outcome_available_utc <= result.scheduled_dep_utc
    invalid &= ~excluded_international
    audit["invalid_flight_rows"] = int(invalid.sum())
    if invalid.any() and not drop_invalid:
        examples = frame.index[invalid].tolist()[:5]
        raise ValueError(f"{int(invalid.sum())} invalid flight rows (zero-based source rows {examples}): check carrier/number, airport codes, HHMM, DST ambiguity, and outcome timing. Correct the data or explicitly use --drop-invalid.")
    result = result.loc[~(invalid | excluded_international)].copy()
    if result.empty:
        raise ValueError("No valid completed US domestic flights remain after normalization.")
    result["flight_key"] = result.carrier + "|" + result.flight_number + "|" + result.origin + "|" + result.destination
    for timezone, indices in result.groupby("origin_timezone").groups.items():
        local = result.loc[indices, "scheduled_dep_utc"].dt.tz_convert(timezone)
        result.loc[indices, "dep_hour"] = local.dt.hour
        result.loc[indices, "dep_month"] = local.dt.month
        result.loc[indices, "dep_day_of_week"] = local.dt.dayofweek
    for column in ("dep_hour", "dep_month", "dep_day_of_week"):
        result[column] = result[column].astype("int16")
    result["merge_hour"] = (result.scheduled_dep_utc + pd.Timedelta(minutes=30)).dt.floor("h")
    duplicates = result.duplicated(["flight_key", "scheduled_dep_utc"], keep=False)
    if duplicates.any():
        conflicts = result.loc[duplicates].groupby(["flight_key", "scheduled_dep_utc"])[[TARGET_COLUMN, "outcome_available_utc"]].nunique()
        if (conflicts > 1).any().any():
            raise ValueError("Conflicting flight records share a carrier/number/route/departure key.")
    before = len(result)
    result = result.drop_duplicates(["flight_key", "scheduled_dep_utc"]).sort_values("scheduled_dep_utc").reset_index(drop=True)
    audit["duplicate_flight_rows"] = before - len(result)
    audit["normalized_flight_rows"] = len(result)
    details = dict(audit)
    details.update(outcome_availability_method=outcome_method, outcome_reporting_lag_hours=outcome_reporting_lag_hours, forecast_horizon_hours=horizon_hours)
    return result, details


def normalize_weather(raw: pd.DataFrame, *, units: str = "canonical", airport_overrides: dict | None = None, drop_invalid: bool = False) -> tuple[pd.DataFrame, dict]:
    """Convert explicit canonical/imperial/metric/Meteostat columns to model units.

    Meteostat temp is Celsius, wspd is km/h, and prcp is mm. Visibility is
    frequently absent from Meteostat; retain NaN so training can handle missing
    information honestly. NOAA files must first expose the documented columns;
    packed station flags and sentinel codes are not silently interpreted.
    """
    if units not in {"canonical", "imperial", "metric", "meteostat"}:
        raise ValueError("Weather units must be canonical, imperial, metric, or meteostat.")
    time_col = _column(raw, "timestamp_utc", "weather_time_utc", "Timestamp", "time", "date", required=True)
    airport_col = _column(raw, "airport_icao", "Airport ICAO", "airport_iata", "airport", required=True)
    result = pd.DataFrame(index=raw.index)
    result["weather_time_utc"] = _utc_series(raw[time_col])
    codes = raw[airport_col].astype("string").str.strip().str.upper()
    airports = {}
    for code in codes.dropna().unique():
        try:
            airports[code] = resolve_airport(code, airport_overrides).icao
        except ValueError:
            airports[code] = None
    result["origin_icao"] = codes.map(airports)
    # Explicitly suffixed column units take precedence over --weather-units.
    specs = {
        "temperature_f": [("temperature_f", 1, 0), ("temperature_c", 1.8, 32)],
        "wind_speed_mph": [("wind_speed_mph", 1, 0), ("wind_speed_kmh", 1 / 1.609344, 0), ("wind_speed_ms", 2.2369362921, 0)],
        "visibility_miles": [("visibility_miles", 1, 0), ("visibility_km", 1 / 1.609344, 0), ("visibility_meters", 1 / 1609.344, 0)],
        "precipitation_inches": [("precipitation_inches", 1, 0), ("precipitation_mm", 1 / 25.4, 0)],
    }
    generic = {
        "temperature_f": ["temperature", "temp"],
        "wind_speed_mph": ["wind_speed", "Wind Speed", "wspd"],
        "visibility_miles": ["visibility", "vis"],
        "precipitation_inches": ["precipitation", "prcp"],
    }
    factors = {"temperature_f": (1.8, 32), "wind_speed_mph": (1 / 1.609344, 0), "visibility_miles": (1 / 1.609344, 0), "precipitation_inches": (1 / 25.4, 0)}
    missing_columns = []
    for output, candidates in specs.items():
        selected = None
        for alias, factor, offset in candidates:
            source = _column(raw, alias)
            if source:
                selected = source, factor, offset
                break
        if selected is None and units != "canonical":
            source = _column(raw, *generic[output])
            if source:
                factor, offset = factors[output] if units in {"metric", "meteostat"} else (1, 0)
                selected = source, factor, offset
        if selected is None:
            if output != "visibility_miles":
                raise ValueError(f"Missing weather feature {output}; generic column names require --weather-units imperial, metric, or meteostat.")
            result[output] = np.nan
            missing_columns.append(output)
        else:
            source, factor, offset = selected
            result[output] = pd.to_numeric(raw[source], errors="coerce") * factor + offset
    # Missing measurements are supported; impossible finite values become missing.
    measurements = ["temperature_f", "wind_speed_mph", "visibility_miles", "precipitation_inches"]
    result[measurements] = result[measurements].replace([np.inf, -np.inf], np.nan)
    result.loc[~result.temperature_f.between(-150, 160), "temperature_f"] = np.nan
    for output in measurements[1:]:
        result.loc[result[output] < 0, output] = np.nan
    invalid = result[["origin_icao", "weather_time_utc"]].isna().any(axis=1)
    off_hour = result.weather_time_utc.notna() & (result.weather_time_utc != result.weather_time_utc.dt.floor("h"))
    if off_hour.any():
        raise ValueError("Weather records must be hourly UTC timestamps at minute 00. Aggregate subhourly/raw NOAA observations first with documented interval and unit handling.")
    if invalid.any() and not drop_invalid:
        raise ValueError(f"{int(invalid.sum())} weather rows have unknown airports or invalid UTC timestamps; correct them or use --drop-invalid.")
    result = result.loc[~invalid].copy()
    duplicate = result.duplicated(["origin_icao", "weather_time_utc"], keep=False)
    if duplicate.any():
        conflict = result.loc[duplicate].groupby(["origin_icao", "weather_time_utc"])[measurements].nunique(dropna=False)
        if (conflict > 1).any().any():
            raise ValueError("Conflicting weather measurements share an airport and hour; resolve duplicate station records before merging.")
    before = len(result)
    result = result.drop_duplicates(["origin_icao", "weather_time_utc"]).reset_index(drop=True)
    result["merge_hour"] = result.weather_time_utc
    audit = {
        "input_weather_rows": len(raw), "invalid_weather_rows": int(invalid.sum()),
        "duplicate_weather_rows": before - len(result), "normalized_weather_rows": len(result),
        "weather_input_units": units, "missing_weather_columns": missing_columns,
        "missing_weather_measurements": {column: int(result[column].isna().sum()) for column in measurements},
    }
    return result, audit


def create_prediction_pipeline(
    flight_csv_paths, weather_csv_paths, *, output_path="data/processed/training.csv",
    weather_units="canonical", assumed_outcome_lag_hours=None, horizon_hours=0.0,
    outcome_reporting_lag_hours=0.0, airport_overrides=None, drop_invalid=False,
) -> tuple[pd.DataFrame, dict]:
    """Export features, labels, timestamps, and a JSON audit beside the matrix."""
    if isinstance(flight_csv_paths, (str, Path)):
        flight_csv_paths = [flight_csv_paths]
    if isinstance(weather_csv_paths, (str, Path)):
        weather_csv_paths = [weather_csv_paths]
    flights, flight_audit = normalize_flights(
        load_csvs(flight_csv_paths), assumed_outcome_lag_hours=assumed_outcome_lag_hours,
        horizon_hours=horizon_hours, outcome_reporting_lag_hours=outcome_reporting_lag_hours,
        airport_overrides=airport_overrides, drop_invalid=drop_invalid,
    )
    weather, weather_audit = normalize_weather(load_csvs(weather_csv_paths), units=weather_units, airport_overrides=airport_overrides, drop_invalid=drop_invalid)
    # Compute history before the inner join so a missing weather row never removes
    # an otherwise verified outcome from the rolling flight statistics.
    flights = build_history_features(flights)
    matrix = flights.merge(weather, on=["origin_icao", "merge_hour"], how="inner", validate="many_to_one")
    if matrix.empty:
        raise ValueError("No flight/weather matches. Verify archive date coverage, UTC conversion, and airport identifiers.")
    matrix = matrix.sort_values("scheduled_dep_utc").reset_index(drop=True)
    metadata_columns = ["flight_key", "scheduled_dep_utc", "prediction_as_of_utc", "outcome_available_utc", "origin_icao", "origin_timezone", "weather_time_utc", "hist_flight_num_delay_count"]
    matrix = matrix[metadata_columns + FEATURE_COLUMNS + [TARGET_COLUMN]]
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Preserve all normalized outcomes, including flights without weather, for
    # train-time recomputation and later rolling lookup snapshots.
    history_path = destination.with_suffix(".history.csv")
    history_columns = ["flight_key", "scheduled_dep_utc", "outcome_available_utc", TARGET_COLUMN]
    _atomic_csv(flights[history_columns], history_path)
    _atomic_csv(matrix, destination)
    audit = {
        "schema_version": 1, **flight_audit, **weather_audit,
        "training_rows": len(matrix), "flights_without_weather": len(flights) - len(matrix),
        "weather_match_rate": len(matrix) / len(flights), "feature_columns": FEATURE_COLUMNS,
        "target": TARGET_COLUMN, "history_path": history_path.name,
        "first_departure_utc": matrix.scheduled_dep_utc.min().isoformat(),
        "last_departure_utc": matrix.scheduled_dep_utc.max().isoformat(),
        "weather_semantics": "Nearest-hour observed origin weather; forecast inference has observation/forecast distribution shift. UTC rounding is half-up. Time features use origin local time.",
        "history_semantics": "Previous 30 scheduled-departure days, outcomes strictly known before prediction cutoff; exact carrier/number/route mean, then available global 30-day mean, then zero only with no history.",
        "flight_inputs": [str(path) for path in expand_paths(flight_csv_paths)],
        "weather_inputs": [str(path) for path in expand_paths(weather_csv_paths)],
    }
    audit_path = destination.with_suffix(".audit.json")
    temporary = audit_path.with_suffix(audit_path.suffix + ".tmp")
    temporary.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    temporary.replace(audit_path)
    LOGGER.info("Exported %s rows to %s; weather match rate %.1f%%", len(matrix), destination, audit["weather_match_rate"] * 100)
    return matrix, audit


def _atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flights", nargs="+", required=True, help="BTS CSV paths or quoted glob patterns")
    parser.add_argument("--weather", nargs="+", required=True, help="Hourly weather CSV paths or quoted glob patterns")
    parser.add_argument("--output", default="data/processed/training.csv")
    parser.add_argument("--weather-units", choices=["canonical", "imperial", "metric", "meteostat"], default="canonical")
    parser.add_argument("--assumed-outcome-lag-hours", type=float, help="Explicit fallback only when actual completion timing is unavailable")
    parser.add_argument("--outcome-reporting-lag-hours", type=float, default=0, help="Additional time until completed outcomes become available")
    parser.add_argument("--horizon-hours", type=float, default=0, help="How many hours before departure the model is intended to predict")
    parser.add_argument("--airport-overrides", type=Path, help="JSON object keyed by IATA/ICAO with icao,iata,tz,lat,lon,country records")
    parser.add_argument("--drop-invalid", action="store_true", help="Drop and count malformed records instead of failing")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        overrides = json.loads(args.airport_overrides.read_text(encoding="utf-8")) if args.airport_overrides else None
        _, audit = create_prediction_pipeline(
            args.flights, args.weather, output_path=args.output, weather_units=args.weather_units,
            assumed_outcome_lag_hours=args.assumed_outcome_lag_hours, horizon_hours=args.horizon_hours,
            outcome_reporting_lag_hours=args.outcome_reporting_lag_hours,
            airport_overrides=overrides, drop_invalid=args.drop_invalid,
        )
    except (ValueError, RuntimeError, OSError) as exc:
        LOGGER.error("Data preparation failed: %s", exc)
        return 1
    print(f"Prepared {audit['training_rows']:,} training rows; matched {audit['weather_match_rate']:.1%} of completed domestic flights to weather.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
