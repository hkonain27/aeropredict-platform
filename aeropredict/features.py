"""Shared feature contract used by preparation, training, and inference.

History is keyed by airline, flight number, and route: AA123 from JFK to LAX
must never borrow the same-numbered flight from a different airline. Outcomes
become usable only strictly before the prediction's information cutoff.
"""

from collections import defaultdict
import re

import numpy as np
import pandas as pd


CATEGORICAL_FEATURES = ["carrier", "flight_number", "origin", "destination"]
NUMERIC_FEATURES = [
    "dep_hour", "dep_month", "dep_day_of_week", "hist_flight_num_delay_avg",
    "temperature_f", "wind_speed_mph", "visibility_miles", "precipitation_inches",
]
FEATURE_COLUMNS = CATEGORICAL_FEATURES + NUMERIC_FEATURES
TARGET_COLUMN = "arr_delay_min"
HISTORY_COLUMNS = ["flight_key", "scheduled_dep_utc", "outcome_available_utc", TARGET_COLUMN]
WINDOW = pd.Timedelta(days=30)


def normalize_flight_identity(carrier, flight_number) -> tuple[str, str]:
    """Normalize numeric BTS numbers and prefixed provider flight numbers."""
    carrier = "" if pd.isna(carrier) else re.sub(r"\s+", "", str(carrier)).upper()
    number = "" if pd.isna(flight_number) else re.sub(r"\s+", "", str(flight_number)).upper()
    if re.fullmatch(r"\d+\.0", number):
        number = number[:-2]
    if carrier and number.startswith(carrier) and number[len(carrier):].isdigit():
        number = number[len(carrier):]
    elif not carrier:
        matched = re.fullmatch(r"([A-Z0-9]{2,3}?)(\d{1,4})", number)
        if matched:
            carrier, number = matched.groups()
    if not re.fullmatch(r"[A-Z0-9]{2,3}", carrier) or not re.fullmatch(r"\d{1,5}", number):
        raise ValueError(f"Flight identity needs an airline code and number, got {carrier!r}/{number!r}.")
    return carrier, str(int(number))


def make_flight_key(carrier, flight_number, origin, destination) -> str:
    carrier, number = normalize_flight_identity(carrier, flight_number)
    return "|".join((carrier, number, str(origin).upper().strip(), str(destination).upper().strip()))


def normalize_utc_timestamp(value, timezone: str | None = None) -> pd.Timestamp:
    """Parse a timestamp; naive local times require an explicit IANA time zone.

    DST folds and gaps raise instead of silently shifting a flight an hour.
    Pass timezone='UTC' for a column that explicitly documents UTC timestamps.
    """
    timestamp = pd.Timestamp(value)
    if pd.isna(timestamp):
        raise ValueError("Timestamp is missing.")
    if timestamp.tzinfo is None:
        if not timezone:
            raise ValueError("Naive timestamp requires an explicit time zone.")
        timestamp = timestamp.tz_localize(timezone, ambiguous="raise", nonexistent="raise")
    return timestamp.tz_convert("UTC")


def nearest_hour_utc(value) -> pd.Timestamp:
    """Round half up, including midnight rollover, identically in both phases."""
    timestamp = normalize_utc_timestamp(value, timezone="UTC")
    return (timestamp + pd.Timedelta(minutes=30)).floor("h")


def departure_time_features(timestamp, timezone: str) -> dict:
    """Scheduling season and rush-hour features use the origin's local clock."""
    local = normalize_utc_timestamp(timestamp, timezone="UTC").tz_convert(timezone)
    return {"dep_hour": local.hour, "dep_month": local.month, "dep_day_of_week": local.dayofweek}


def _validated_history(history: pd.DataFrame) -> pd.DataFrame:
    missing = set(HISTORY_COLUMNS) - set(history.columns)
    if missing:
        raise ValueError(f"History is missing columns: {', '.join(sorted(missing))}")
    result = history[HISTORY_COLUMNS].copy()
    for column in ("scheduled_dep_utc", "outcome_available_utc"):
        result[column] = pd.to_datetime(result[column], utc=True, errors="raise", format="mixed")
    result[TARGET_COLUMN] = pd.to_numeric(result[TARGET_COLUMN], errors="raise")
    if result.isna().any().any() or not np.isfinite(result[TARGET_COLUMN]).all():
        raise ValueError("History contains missing or non-finite values.")
    if (result.outcome_available_utc <= result.scheduled_dep_utc).any():
        raise ValueError("Outcome availability must be later than scheduled departure.")
    duplicate = result.duplicated(["flight_key", "scheduled_dep_utc"], keep=False)
    if duplicate.any():
        conflicts = result.loc[duplicate].groupby(["flight_key", "scheduled_dep_utc"])[
            ["outcome_available_utc", TARGET_COLUMN]
        ].nunique()
        if (conflicts > 1).any().any():
            raise ValueError("History has conflicting outcomes for the same flight occurrence.")
        result = result.drop_duplicates(["flight_key", "scheduled_dep_utc"])
    return result.sort_values("scheduled_dep_utc").reset_index(drop=True)


class RollingHistory:
    """Lookup a bounded 30-day route/flight mean with a past-only global fallback."""

    def __init__(self, history: pd.DataFrame):
        self.history = _validated_history(history)
        self.departures = self.history.scheduled_dep_utc.astype("int64").to_numpy()

    def lookup(self, flight_key: str, as_of, scheduled_dep_utc=None) -> dict:
        cutoff = normalize_utc_timestamp(as_of, timezone="UTC")
        anchor = normalize_utc_timestamp(
            scheduled_dep_utc if scheduled_dep_utc is not None else cutoff, timezone="UTC"
        )
        if cutoff > anchor:
            raise ValueError("Prediction cutoff cannot be after scheduled departure.")
        left = np.searchsorted(self.departures, (anchor - WINDOW).value, side="left")
        right = np.searchsorted(self.departures, anchor.value, side="left")
        available = self.history.iloc[left:right]
        available = available[available.outcome_available_utc < cutoff]
        specific = available[available.flight_key == flight_key]
        selected = specific if len(specific) else available
        return {
            "hist_flight_num_delay_avg": float(selected[TARGET_COLUMN].mean()) if len(selected) else 0.0,
            "hist_flight_num_delay_count": int(len(specific)),
        }


def build_history_features(flights: pd.DataFrame, history: pd.DataFrame | None = None, as_of=None) -> pd.DataFrame:
    """Compute past-only history in O((flights + history) log n), bounded memory.

    The common path sorts once and sweeps departures and outcome availability.
    It maintains sums and counts instead of scanning millions of prior rows for
    each flight. A nonmonotonic information cutoff uses the safe scalar lookup.
    Passing a fixed as_of freezes information at a chronological holdout boundary.
    """
    result = flights.copy()
    if result.empty:
        result["hist_flight_num_delay_avg"] = pd.Series(dtype=float)
        result["hist_flight_num_delay_count"] = pd.Series(dtype=int)
        return result
    validated = _validated_history(flights if history is None else history)
    anchors = pd.to_datetime(result.scheduled_dep_utc, utc=True, format="mixed")
    if as_of is None:
        cutoffs = pd.to_datetime(result.get("prediction_as_of_utc", result.scheduled_dep_utc), utc=True, format="mixed")
    else:
        cutoffs = pd.Series(normalize_utc_timestamp(as_of, timezone="UTC"), index=result.index)
    if anchors.isna().any() or cutoffs.isna().any() or (cutoffs > anchors).any():
        raise ValueError("Prediction cutoffs must be present and no later than departure.")
    order = np.argsort(anchors.astype("int64").to_numpy(), kind="stable")
    cutoff_ns = cutoffs.astype("int64").to_numpy()
    anchor_ns = anchors.astype("int64").to_numpy()
    means, counts = np.zeros(len(result)), np.zeros(len(result), dtype=np.int32)
    keys = result.flight_key.to_numpy()
    if (np.diff(cutoff_ns[order]) < 0).any():
        lookup = RollingHistory(validated)
        for row in order:
            answer = lookup.lookup(keys[row], cutoffs.iloc[row], anchors.iloc[row])
            means[row], counts[row] = answer["hist_flight_num_delay_avg"], answer["hist_flight_num_delay_count"]
    else:
        dep = validated.scheduled_dep_utc.astype("int64").to_numpy()
        availability = validated.outcome_available_utc.astype("int64").to_numpy()
        values, history_keys = validated[TARGET_COLUMN].to_numpy(), validated.flight_key.to_numpy()
        known_order = np.argsort(availability, kind="stable")
        active = np.zeros(len(validated), dtype=bool)
        group_sums, group_counts = defaultdict(float), defaultdict(int)
        total_sum, total_count, next_known, next_expired = 0.0, 0, 0, 0
        for row in order:
            start = anchor_ns[row] - WINDOW.value
            while next_known < len(validated) and availability[known_order[next_known]] < cutoff_ns[row]:
                item = known_order[next_known]
                next_known += 1
                if dep[item] < start:
                    continue
                key, value = history_keys[item], values[item]
                active[item] = True
                group_sums[key] += value
                group_counts[key] += 1
                total_sum += value
                total_count += 1
            while next_expired < len(validated) and dep[next_expired] < start:
                item = next_expired
                next_expired += 1
                if active[item]:
                    key, value = history_keys[item], values[item]
                    group_sums[key] -= value
                    group_counts[key] -= 1
                    total_sum -= value
                    total_count -= 1
                    active[item] = False
            count = group_counts.get(keys[row], 0)
            counts[row] = count
            means[row] = group_sums[keys[row]] / count if count else (total_sum / total_count if total_count else 0.0)
    result["hist_flight_num_delay_avg"], result["hist_flight_num_delay_count"] = means, counts
    return result


def add_historical_features(flights: pd.DataFrame, horizon_hours: float = 0) -> pd.DataFrame:
    result = flights.copy()
    result["prediction_as_of_utc"] = pd.to_datetime(result.scheduled_dep_utc, utc=True, format="mixed") - pd.Timedelta(hours=horizon_hours)
    return build_history_features(result)
