import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
raw_path = ROOT / "data" / "raw" / "airline_delay_cause.csv"
processed_path = ROOT / "data" / "processed" / "delay_processed.csv"

df = pd.read_csv(raw_path)

cols = [
    "year", "month", "carrier", "carrier_name", "airport", "airport_name",
    "arr_flights", "arr_del15",
    "carrier_ct", "weather_ct", "nas_ct", "security_ct", "late_aircraft_ct",
    "arr_cancelled", "arr_diverted",
    "arr_delay", "carrier_delay", "weather_delay", "nas_delay",
    "security_delay", "late_aircraft_delay"
]
df = df[cols].copy()

numeric_cols = [
    "arr_flights", "arr_del15",
    "carrier_ct", "weather_ct", "nas_ct", "security_ct", "late_aircraft_ct",
    "arr_cancelled", "arr_diverted",
    "arr_delay", "carrier_delay", "weather_delay", "nas_delay",
    "security_delay", "late_aircraft_delay"
]

for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
df["month"] = pd.to_numeric(df["month"], errors="coerce").astype("Int64")

df = df.dropna(subset=["year", "month", "carrier", "airport", "arr_flights", "arr_del15"])
df = df[df["arr_flights"] > 0].copy()

df["delay_rate"] = df["arr_del15"] / df["arr_flights"]
df["is_delay_heavy"] = (df["delay_rate"] >= 0.20).astype(int)

df["period_date"] = pd.to_datetime(
    df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2) + "-01",
    errors="coerce"
)

df = df.dropna(subset=["period_date"])

processed_path.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(processed_path, index=False)

print("saved:", processed_path)
print("shape:", df.shape)
print("min year:", df["year"].min())
print("max year:", df["year"].max())
print("avg delay rate:", round(df["delay_rate"].mean(), 4))