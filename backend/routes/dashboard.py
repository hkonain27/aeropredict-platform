from collections import defaultdict
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify

from models import Prediction
from services.predictor import FEATURE_IMPORTANCES

dashboard_bp = Blueprint("dashboard", __name__)

DAY_LABELS = {
    1: "Mon",
    2: "Tue",
    3: "Wed",
    4: "Thu",
    5: "Fri",
    6: "Sat",
    7: "Sun",
}

MONTH_LABELS = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}


def _pct_change(current, previous):
    if previous == 0:
        return "New" if current else "0.0%"
    delta = ((current - previous) / previous) * 100
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.1f}%"


def _avg_prob(records):
    if not records:
        return 0.0
    return sum(r.delay_probability for r in records) / len(records)


def _status_from_probability(probability):
    if probability >= 0.8:
        return "Critical"
    if probability >= 0.6:
        return "High Risk"
    if probability >= 0.4:
        return "Moderate"
    return "Low Risk"


def _confidence_from_probability(probability):
    return round(max(probability, 1 - probability) * 100)


def _format_feature_name(name):
    return name.replace("_", " ").title()


def _as_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dashboard_bp.route("/api/dashboard-data", methods=["GET"])
def get_dashboard_data():
    records = Prediction.query.order_by(Prediction.created_at.asc()).all()
    latest_first = list(reversed(records))

    now = datetime.now(timezone.utc)
    recent_cutoff = now - timedelta(days=7)
    previous_cutoff = now - timedelta(days=14)

    recent_records = [
        r for r in records
        if _as_utc(r.created_at) and _as_utc(r.created_at) >= recent_cutoff
    ]
    previous_records = [
        r for r in records
        if _as_utc(r.created_at) and previous_cutoff <= _as_utc(r.created_at) < recent_cutoff
    ]

    total_predictions = len(records)
    avg_probability = _avg_prob(records) * 100
    high_risk_predictions = sum(1 for r in records if r.prediction == 1)
    unique_routes = len({(r.origin, r.destination) for r in records})

    summary_cards = [
        {
            "title": "Flights Analyzed",
            "value": f"{total_predictions:,}",
            "change": _pct_change(len(recent_records), len(previous_records)),
            "icon": "Plane",
        },
        {
            "title": "Avg Delay Risk",
            "value": f"{avg_probability:.1f}%",
            "change": _pct_change(_avg_prob(recent_records), _avg_prob(previous_records)),
            "icon": "Clock3",
        },
        {
            "title": "High-Risk Predictions",
            "value": f"{high_risk_predictions:,}",
            "change": _pct_change(
                sum(1 for r in recent_records if r.prediction == 1),
                sum(1 for r in previous_records if r.prediction == 1),
            ),
            "icon": "CloudRain",
        },
        {
            "title": "Routes Covered",
            "value": f"{unique_routes:,}",
            "change": _pct_change(
                len({(r.origin, r.destination) for r in recent_records}),
                len({(r.origin, r.destination) for r in previous_records}),
            ),
            "icon": "TrendingUp",
        },
    ]

    month_buckets = defaultdict(list)
    airport_buckets = defaultdict(list)
    day_buckets = {day: [] for day in DAY_LABELS}

    for record in records:
        created_at = _as_utc(record.created_at) or now
        month_buckets[created_at.month].append(record)
        airport_buckets[record.origin].append(record)
        if record.day_of_week in day_buckets:
            day_buckets[record.day_of_week].append(record)

    monthly_delay_data = [
        {
            "month": MONTH_LABELS[month],
            "avgDelay": round(_avg_prob(bucket) * 100, 1),
            "predicted": round((sum(r.prediction for r in bucket) / len(bucket)) * 100, 1),
        }
        for month, bucket in sorted(month_buckets.items())
        if bucket
    ]

    airport_risk_data = [
        {
            "airport": airport,
            "risk": round(_avg_prob(bucket) * 100, 1),
        }
        for airport, bucket in sorted(
            airport_buckets.items(),
            key=lambda item: _avg_prob(item[1]),
            reverse=True,
        )[:6]
    ]

    cause_breakdown = [
        {
            "name": _format_feature_name(item["feature"]),
            "value": item["importance"],
        }
        for item in FEATURE_IMPORTANCES
    ]

    forecast_data = [
        {
            "day": DAY_LABELS[day],
            "actual": round(
                (sum(r.prediction for r in bucket) / len(bucket)) * 100, 1
            ) if bucket else 0,
            "predicted": round(_avg_prob(bucket) * 100, 1) if bucket else 0,
        }
        for day, bucket in day_buckets.items()
    ]

    recent_flights = [
        {
            "id": f"PRED-{record.id}",
            "route": f"{record.origin} -> {record.destination}",
            "airport": record.origin,
            "airline": record.airline,
            "day": DAY_LABELS.get(record.day_of_week, str(record.day_of_week)),
            "depHour": f"{record.dep_hour:02d}:00",
            "delayProbability": round(record.delay_probability * 100, 1),
            "confidence": _confidence_from_probability(record.delay_probability),
            "status": _status_from_probability(record.delay_probability),
            "createdAt": _as_utc(record.created_at).isoformat() if record.created_at else None,
        }
        for record in latest_first[:50]
    ]

    return jsonify(
        {
            "summaryCards": summary_cards,
            "monthlyDelayData": monthly_delay_data,
            "airportRiskData": airport_risk_data,
            "causeBreakdown": cause_breakdown,
            "forecastData": forecast_data,
            "recentFlights": recent_flights,
        }
    )
