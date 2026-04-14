import json
from pathlib import Path
from flask import Blueprint, jsonify
from models import Prediction

dashboard_bp = Blueprint("dashboard", __name__)

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "delay_dashboard.json"

@dashboard_bp.route("/api/dashboard-data", methods=["GET"])
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
            "avgDelay": round(item["delay_rate"] * 100, 1),
            "predicted": round(item["delay_rate"] * 100, 1),
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
            "day": item["carrier"],
            "actual": round(item["delay_rate"] * 100, 1),
            "predicted": round(item["delay_rate"] * 100, 1),
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
            "delayProbability": round(record.delay_probability * 100, 1),
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
    })
