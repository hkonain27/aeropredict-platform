import json
from functools import lru_cache
from pathlib import Path
from flask import Blueprint, jsonify
from models import Prediction
from services.delay_data import load_delay_data

dashboard_bp = Blueprint("dashboard", __name__)

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "delay_dashboard.json"


@lru_cache(maxsize=1)
def _build_suggestion_scenarios():
    df = load_delay_data()
    grouped = (
        df.groupby(["carrier", "airport", "month"], as_index=False)
        .agg(arrivals=("arr_flights", "sum"), delayed=("arr_del15", "sum"), records=("year", "count"))
    )
    # Suggestions use only historical rows with enough arrivals and repeated BTS records
    # so the low/medium/high examples are stable and not driven by tiny samples.
    grouped = grouped[(grouped["arrivals"] >= 1000) & (grouped["records"] >= 2)].copy()
    grouped["delay_rate"] = grouped["delayed"] / grouped["arrivals"]

    scenarios = [
        (
            "Low",
            "Lower historical delay pattern",
            grouped[grouped["delay_rate"] < 0.16].sort_values("arrivals", ascending=False),
        ),
        (
            "Medium",
            "Worth watching",
            grouped[(grouped["delay_rate"] >= 0.20) & (grouped["delay_rate"] < 0.25)]
            .assign(distance_from_midpoint=lambda frame: (frame["delay_rate"] - 0.225).abs())
            .sort_values(["distance_from_midpoint", "arrivals"], ascending=[True, False]),
        ),
        (
            "High",
            "Higher historical delay pattern",
            grouped[grouped["delay_rate"] >= 0.28].sort_values(["delay_rate", "arrivals"], ascending=[False, False]),
        ),
    ]

    suggestions = []
    for risk, label, frame in scenarios:
        if frame.empty:
            continue

        row = frame.iloc[0]
        suggestions.append(
            {
                "risk": risk,
                "label": label,
                "carrier": row["carrier"],
                "airport": row["airport"],
                "month": str(int(row["month"])),
                "delayRate": round(float(row["delay_rate"]) * 100, 1),
                "records": int(row["records"]),
                "arrivals": int(round(float(row["arrivals"]))),
            }
        )

    return suggestions

@dashboard_bp.route("/dashboard-data", methods=["GET"])
def get_dashboard_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = Prediction.query.order_by(Prediction.created_at.desc()).limit(50).all()

    summary = data["summary"]
    monthly = data["monthly_delay_rate"]
    top_airports = data["top_airports"]
    top_carriers = data["top_carriers"]
    cause_totals = data["cause_totals"]

    summary_cards = [
        {
            "title": "Records Analyzed",
            "value": f"{summary['records']:,}",
            "change": f"{len(summary['years'])} years",
            "icon": "Plane",
        },
        {
            "title": "Avg Delay Rate",
            "value": f"{summary['avg_delay_rate'] * 100:.1f}%",
            "change": f"{summary['carriers']} carriers",
            "icon": "Clock3",
        },
        {
            "title": "Airports Covered",
            "value": f"{summary['airports']:,}",
            "change": "arrival-based",
            "icon": "MapPin",
        },
        {
            "title": "Carriers Covered",
            "value": f"{summary['carriers']:,}",
            "change": "real BTS data",
            "icon": "TrendingUp",
        },
    ]

    monthly_delay_data = [
        {
            "month": str(item["month"]),
            "monthLabel": [
                "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
            ][int(item["month"]) - 1],
            "avgDelay": round(item["delay_rate"] * 100, 1),
        }
        for item in monthly
    ]

    airport_risk_data = [
        {
            "airport": item["airport"],
            "risk": round(item["delay_rate"] * 100, 1),
        }
        for item in top_airports
    ]

    cause_breakdown = [
        {"name": "Carrier", "value": cause_totals["carrier"]},
        {"name": "Weather", "value": cause_totals["weather"]},
        {"name": "NAS", "value": cause_totals["nas"]},
        {"name": "Security", "value": cause_totals["security"]},
        {"name": "Late Aircraft", "value": cause_totals["late_aircraft"]},
    ]

    forecast_data = [
        {
            "day": item.get("carrier_name") or item["carrier"],
            "carrier": item["carrier"],
            "carrierName": item.get("carrier_name") or item["carrier"],
            "actual": round(item["delay_rate"] * 100, 1),
        }
        for item in top_carriers[:7]
    ]

    recent_flights = [
        {
            "id": f"PRED-{record.id}",
            "route": f"{record.carrier} @ {record.airport}",
            "airport": record.airport,
            "airline": record.carrier,
            "day": f"Month {record.month}",
            "delayProbability": round((record.final_risk_score if record.final_risk_score is not None else record.delay_probability) * 100, 1),
            "confidence": round(max(record.delay_probability, 1 - record.delay_probability) * 100),
            "status": record.prediction_label,
            "createdAt": record.created_at.isoformat() if record.created_at else None,
        }
        for record in records
    ]

    return jsonify({
        "summaryCards": summary_cards,
        "monthlyDelayData": monthly_delay_data,
        "airportRiskData": airport_risk_data,
        "causeBreakdown": cause_breakdown,
        "forecastData": forecast_data,
        "recentFlights": recent_flights,
        "suggestionScenarios": _build_suggestion_scenarios(),
    })
