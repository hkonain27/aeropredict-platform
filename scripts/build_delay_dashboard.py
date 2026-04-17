import json
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
data_path = ROOT / "data" / "processed" / "delay_processed.csv"
out_path = ROOT / "backend" / "data" / "delay_dashboard.json"

df = pd.read_csv(data_path)

summary = {
    "records": int(len(df)),
    "avg_delay_rate": round(float(df["delay_rate"].mean()), 4),
    "years": sorted(df["year"].dropna().unique().tolist()),
    "airports": int(df["airport"].nunique()),
    "carriers": int(df["carrier"].nunique())
}

monthly = (
    df.groupby("month", as_index=False)["delay_rate"]
    .mean()
    .sort_values("month")
)
monthly["delay_rate"] = monthly["delay_rate"].round(4)

top_airports = (
    df.groupby(["airport", "airport_name"], as_index=False)
    .agg(delay_rate=("delay_rate", "mean"), arr_flights=("arr_flights", "sum"))
)

top_airports = top_airports[top_airports["arr_flights"] >= 50000]

top_airports = (
    top_airports
    .sort_values(["delay_rate", "arr_flights"], ascending=[False, False])
    .head(10)
)

top_airports["delay_rate"] = top_airports["delay_rate"].round(4)

top_carriers = (
    df.groupby(["carrier", "carrier_name"], as_index=False)
    .agg(delay_rate=("delay_rate", "mean"), arr_flights=("arr_flights", "sum"))
    .sort_values("delay_rate", ascending=False)
    .head(10)
)
top_carriers["delay_rate"] = top_carriers["delay_rate"].round(4)

cause_totals = {
    "carrier": round(float(df["carrier_delay"].sum()), 2),
    "weather": round(float(df["weather_delay"].sum()), 2),
    "nas": round(float(df["nas_delay"].sum()), 2),
    "security": round(float(df["security_delay"].sum()), 2),
    "late_aircraft": round(float(df["late_aircraft_delay"].sum()), 2),
}

payload = {
    "summary": summary,
    "monthly_delay_rate": monthly.to_dict(orient="records"),
    "top_airports": top_airports.to_dict(orient="records"),
    "top_carriers": top_carriers.to_dict(orient="records"),
    "cause_totals": cause_totals
}

out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2)

print("dashboard data saved to:", out_path)