from functools import lru_cache
from pathlib import Path

import pandas as pd


DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "delay_processed.csv"


@lru_cache(maxsize=1)
def load_delay_data():
    df = pd.read_csv(DATA_PATH)
    df["carrier"] = df["carrier"].astype(str).str.upper().str.strip()
    df["airport"] = df["airport"].astype(str).str.upper().str.strip()
    return df


def estimate_arrivals(carrier, airport, month):
    df = load_delay_data()
    carrier = str(carrier).upper().strip()
    airport = str(airport).upper().strip()
    month = int(month)

    candidates = [
        df[(df["carrier"] == carrier) & (df["airport"] == airport) & (df["month"] == month)],
        df[(df["carrier"] == carrier) & (df["airport"] == airport)],
        df[(df["airport"] == airport) & (df["month"] == month)],
        df[(df["carrier"] == carrier) & (df["month"] == month)],
        df[df["month"] == month],
        df,
    ]

    for frame in candidates:
        values = frame["arr_flights"].dropna()
        if not values.empty:
            return max(1, int(round(float(values.median()))))

    return 1


def validate_known_carrier_airport(carrier, airport):
    df = load_delay_data()
    carrier = str(carrier).upper().strip()
    airport = str(airport).upper().strip()

    messages = []
    if not bool((df["carrier"] == carrier).any()):
        messages.append(f"Carrier {carrier} not found in historical dataset.")

    if not bool((df["airport"] == airport).any()):
        messages.append(f"Airport {airport} not found in historical dataset.")

    return messages
