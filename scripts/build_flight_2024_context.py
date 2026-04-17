import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "flight_data_2024.csv"
OUT_PATH = ROOT / "backend" / "data" / "flight_2024_context.json"
CHUNKSIZE = 300_000

USECOLS = [
    "month",
    "op_unique_carrier",
    "origin",
    "dest",
    "arr_delay",
    "cancelled",
    "diverted",
    "distance",
    "carrier_delay",
    "weather_delay",
    "nas_delay",
    "security_delay",
    "late_aircraft_delay",
]

SUM_COLUMNS = [
    "flights",
    "completed_flights",
    "delayed_flights",
    "arrival_delay_minutes",
    "delayed_arrival_delay_minutes",
    "cancelled_flights",
    "diverted_flights",
    "distance_total",
    "carrier_delay",
    "weather_delay",
    "nas_delay",
    "security_delay",
    "late_aircraft_delay",
]


def _prepare_chunk(chunk):
    frame = chunk.rename(
        columns={
            "op_unique_carrier": "carrier",
            "dest": "airport",
        }
    )
    frame["carrier"] = frame["carrier"].astype(str).str.upper().str.strip()
    frame["airport"] = frame["airport"].astype(str).str.upper().str.strip()
    frame["origin"] = frame["origin"].astype(str).str.upper().str.strip()
    frame["month"] = pd.to_numeric(frame["month"], errors="coerce").astype("Int64")

    for column in [
        "arr_delay",
        "cancelled",
        "diverted",
        "distance",
        "carrier_delay",
        "weather_delay",
        "nas_delay",
        "security_delay",
        "late_aircraft_delay",
    ]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)

    frame = frame.dropna(subset=["month", "carrier", "airport"])
    frame["month"] = frame["month"].astype(int)
    frame["flights"] = 1
    frame["completed_flights"] = ((frame["cancelled"] == 0) & (frame["diverted"] == 0)).astype(int)
    frame["delayed_flights"] = (frame["arr_delay"] >= 15).astype(int)
    frame["arrival_delay_minutes"] = frame["arr_delay"].where(frame["completed_flights"] == 1, 0)
    frame["delayed_arrival_delay_minutes"] = frame["arr_delay"].where(frame["arr_delay"] >= 15, 0)
    frame["cancelled_flights"] = (frame["cancelled"] == 1).astype(int)
    frame["diverted_flights"] = (frame["diverted"] == 1).astype(int)
    frame["distance_total"] = frame["distance"].where(frame["completed_flights"] == 1, 0)

    return frame


def _aggregate(frame, keys):
    return frame.groupby(keys, as_index=False)[SUM_COLUMNS].sum()


def _combine(parts, keys):
    combined = pd.concat(parts, ignore_index=True)
    return combined.groupby(keys, as_index=False)[SUM_COLUMNS].sum()


def _safe_rate(numerator, denominator):
    if denominator <= 0:
        return None
    return round(float(numerator) / float(denominator), 4)


def _safe_average(total, count, digits=1):
    if count <= 0:
        return None
    return round(float(total) / float(count), digits)


def _top_delay_cause(row):
    causes = {
        "Airline operations": row["carrier_delay"],
        "Weather": row["weather_delay"],
        "Air traffic system": row["nas_delay"],
        "Security": row["security_delay"],
        "Late inbound aircraft": row["late_aircraft_delay"],
    }
    name, minutes = max(causes.items(), key=lambda item: item[1])
    if minutes <= 0:
        return None
    return {"name": name, "minutes": round(float(minutes), 1)}


def _row_to_summary(row, label):
    flights = int(row["flights"])
    completed = int(row["completed_flights"])
    delayed = int(row["delayed_flights"])
    cancelled = int(row["cancelled_flights"])
    diverted = int(row["diverted_flights"])

    return {
        "label": label,
        "year": 2024,
        "flights": flights,
        "completed_flights": completed,
        "delayed_flights": delayed,
        "delay_rate": _safe_rate(delayed, completed),
        "cancelled_flights": cancelled,
        "cancellation_rate": _safe_rate(cancelled, flights),
        "diverted_flights": diverted,
        "diversion_rate": _safe_rate(diverted, flights),
        "avg_arrival_delay_minutes": _safe_average(row["arrival_delay_minutes"], completed),
        "avg_delay_minutes_when_delayed": _safe_average(row["delayed_arrival_delay_minutes"], delayed),
        "avg_distance": _safe_average(row["distance_total"], completed, digits=0),
        "top_delay_cause": _top_delay_cause(row),
    }


def _to_lookup(frame, keys, label):
    lookup = {}
    for _, row in frame.iterrows():
        key = "|".join(str(row[column]) for column in keys)
        lookup[key] = _row_to_summary(row, label)
    return lookup


def main():
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Missing raw 2024 flight file: {RAW_PATH}")

    exact_parts = []
    airport_month_parts = []
    carrier_month_parts = []
    month_parts = []
    rows = 0

    for chunk_number, chunk in enumerate(pd.read_csv(RAW_PATH, usecols=USECOLS, chunksize=CHUNKSIZE, low_memory=False), start=1):
        frame = _prepare_chunk(chunk)
        rows += len(frame)
        exact_parts.append(_aggregate(frame, ["carrier", "airport", "month"]))
        airport_month_parts.append(_aggregate(frame, ["airport", "month"]))
        carrier_month_parts.append(_aggregate(frame, ["carrier", "month"]))
        month_parts.append(_aggregate(frame, ["month"]))
        print(f"Processed chunk {chunk_number}: {rows:,} rows")

    exact = _combine(exact_parts, ["carrier", "airport", "month"])
    airport_month = _combine(airport_month_parts, ["airport", "month"])
    carrier_month = _combine(carrier_month_parts, ["carrier", "month"])
    month = _combine(month_parts, ["month"])

    payload = {
        "source": str(RAW_PATH.relative_to(ROOT)),
        "year": 2024,
        "rows": rows,
        "exact": _to_lookup(exact, ["carrier", "airport", "month"], "Exact 2024 carrier-airport-month flight records"),
        "airport_month": _to_lookup(airport_month, ["airport", "month"], "2024 airport-month flight records across carriers"),
        "carrier_month": _to_lookup(carrier_month, ["carrier", "month"], "2024 carrier-month flight records across airports"),
        "month": _to_lookup(month, ["month"], "2024 national month flight records"),
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, separators=(",", ":"))

    print(f"Saved 2024 flight context to {OUT_PATH}")
    print(f"Exact groups: {len(payload['exact']):,}")


if __name__ == "__main__":
    main()
