from flask import Blueprint, request, jsonify
from services.predictor import make_prediction
from services.delay_analysis import analyze_delay_risk
from services.delay_data import estimate_arrivals, validate_known_carrier_airport
from services.flight_2024_context import get_flight_2024_context, score_flight_2024_context
from services.historical_weather import get_historical_weather_context, score_historical_weather_context
from services.live_weather import get_live_metar, score_weather_risk
from extensions import db
from models import Prediction

predict_bp = Blueprint("predict", __name__)


BASE_WEIGHTS = {
    "model": 0.47,
    "historical": 0.25,
    "flight_2024": 0.18,
    "historical_weather": 0.10,
}


def _score_delay_rate(delay_rate):
    if delay_rate is None:
        return None
    if delay_rate >= 0.35:
        return 0.85
    if delay_rate >= 0.25:
        return 0.72
    if delay_rate >= 0.20:
        return 0.55
    if delay_rate >= 0.15:
        return 0.35
    return 0.25


def _score_2024_summary(summary):
    delay_score = _score_delay_rate(summary.get("delay_rate")) or 0.4
    cancellation_rate = summary.get("cancellation_rate") or 0
    diversion_rate = summary.get("diversion_rate") or 0

    if cancellation_rate >= 0.05:
        cancellation_score = 0.8
    elif cancellation_rate >= 0.025:
        cancellation_score = 0.55
    else:
        cancellation_score = 0.25

    diversion_score = 0.55 if diversion_rate >= 0.01 else 0.25
    return round((delay_score * 0.65) + (cancellation_score * 0.25) + (diversion_score * 0.10), 4)


def _historical_quality(reliability):
    return {
        "Strong": 1.0,
        "Moderate": 0.75,
        "Limited": 0.55,
    }.get(reliability, 0)


def _flight_2024_quality(context):
    if not context.get("available"):
        return 0

    completed_flights = context["summary"].get("completed_flights") or 0
    if context.get("exact_match") and completed_flights >= 500:
        return 1.0
    if context.get("exact_match") and completed_flights >= 50:
        return 0.75
    if completed_flights >= 500:
        return 0.65
    if completed_flights >= 50:
        return 0.45
    return 0.25


def _component(key, label, score, base_weight, quality, detail):
    effective_weight = base_weight * quality
    if score is None or effective_weight <= 0:
        return None

    return {
        "key": key,
        "label": label,
        "score": round(float(score), 4),
        "base_weight": base_weight,
        "quality": round(float(quality), 2),
        "effective_weight": round(float(effective_weight), 4),
        "detail": detail,
    }


def _risk_label_from_score(score):
    if score >= 0.60:
        return "High Delay Risk"
    if score >= 0.40:
        return "Elevated Delay Risk"
    return "Lower Delay Risk"


def _combine_final_risk(delay_probability, analysis, flight_2024_context, flight_2024_risk, historical_weather_risk):
    historical_context = analysis.get("historical", {}).get("context_used")
    historical_rate = historical_context.get("delay_rate") if historical_context else None
    historical_reliability = analysis.get("historical", {}).get("reliability")
    flight_2024_summary = flight_2024_context.get("summary") if flight_2024_context.get("available") else None

    components = [
        _component(
            "model",
            "Model",
            delay_probability,
            BASE_WEIGHTS["model"],
            1.0,
            "Trained model probability from carrier, airport, month, and estimated arrivals.",
        ),
        _component(
            "historical",
            "Historical",
            _score_delay_rate(historical_rate),
            BASE_WEIGHTS["historical"],
            _historical_quality(historical_reliability),
            f"{historical_reliability} historical evidence from the processed delay dataset.",
        ),
        _component(
            "flight_2024",
            "2024 flights",
            _score_2024_summary(flight_2024_summary) if flight_2024_summary else None,
            BASE_WEIGHTS["flight_2024"],
            _flight_2024_quality(flight_2024_context),
            "Individual 2024 flight records provide recent supporting evidence.",
        ),
        _component(
            "historical_weather",
            "Historical weather",
            historical_weather_risk.get("score"),
            BASE_WEIGHTS["historical_weather"],
            historical_weather_risk.get("quality", 0),
            "Historical ASOS/METAR airport weather for the selected month.",
        ),
    ]
    components = [component for component in components if component]
    total_weight = sum(component["effective_weight"] for component in components)

    final_score = sum(component["score"] * component["effective_weight"] for component in components) / total_weight

    for component in components:
        normalized_weight = component["effective_weight"] / total_weight
        component["normalized_weight"] = round(normalized_weight, 4)
        component["weight_percent"] = round(normalized_weight * 100, 1)
        component["contribution"] = round(component["score"] * normalized_weight, 4)
        component["contribution_percent"] = round(component["score"] * normalized_weight * 100, 1)

    final_label = _risk_label_from_score(final_score)
    reasons = [
        f"Weighted final score is {final_score * 100:.1f}%.",
        "The trained model is the anchor, while historical records, 2024 flights, and historical airport weather act as supporting evidence.",
        "Live METAR is shown for situational awareness only and is not weighted into month-based predictions.",
        "No single supporting layer can force a high-risk label by itself.",
    ]

    return final_label, round(final_score, 4), components, reasons


@predict_bp.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()

    if not data:
        return jsonify({"status": "error", "message": "No input data provided"}), 400

    required_fields = ["carrier", "airport", "month"]
    missing_fields = [f for f in required_fields if data.get(f) in [None, ""]]
    if missing_fields:
        return jsonify({"status": "error", "message": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    try:
        carrier = str(data["carrier"]).strip().upper()
        airport = str(data["airport"]).strip().upper()
        month = int(data["month"])
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Invalid data types provided"}), 400

    if month < 1 or month > 12:
        return jsonify({"status": "error", "message": "month must be between 1 and 12"}), 400

    if len(carrier) not in [2, 3]:
        return jsonify({"status": "error", "message": "carrier must be a 2-3 character carrier code"}), 400

    if len(airport) != 3:
        return jsonify({"status": "error", "message": "airport must be a 3-letter airport code"}), 400

    unknown_messages = validate_known_carrier_airport(carrier, airport)
    if unknown_messages:
        return jsonify({"status": "error", "message": " ".join(unknown_messages)}), 400

    arr_flights = estimate_arrivals(carrier, airport, month)

    prediction, prediction_label, delay_probability, feature_importances = make_prediction(
        {
            "carrier": carrier,
            "airport": airport,
            "month": month,
            "arr_flights": arr_flights,
        }
    )
    analysis = analyze_delay_risk(
        {
            "carrier": carrier,
            "airport": airport,
            "month": month,
            "arr_flights": arr_flights,
        },
        prediction_result={
            "prediction": prediction,
            "prediction_label": prediction_label,
            "delay_probability": delay_probability,
            "feature_importances": feature_importances,
        },
    )
    flight_2024_context = get_flight_2024_context(carrier, airport, month)
    flight_2024_risk = score_flight_2024_context(flight_2024_context)
    historical_weather = get_historical_weather_context(airport, month)
    historical_weather_risk = score_historical_weather_context(historical_weather)
    live_weather = get_live_metar(airport)
    weather_risk = score_weather_risk(live_weather)
    final_risk_label, final_risk_score, final_risk_components, final_risk_reasons = _combine_final_risk(
        delay_probability,
        analysis,
        flight_2024_context,
        flight_2024_risk,
        historical_weather_risk,
    )

    record = Prediction(
        carrier=carrier,
        airport=airport,
        month=month,
        arr_flights=arr_flights,
        prediction=prediction,
        prediction_label=final_risk_label,
        delay_probability=delay_probability,
        final_risk_score=final_risk_score,
    )
    db.session.add(record)
    db.session.commit()

    return jsonify(
        {
            "status": "success",
            "input": {
                "carrier": carrier,
                "airport": airport,
                "month": month,
            },
            "prediction": prediction,
            "prediction_label": final_risk_label,
            "final_risk_label": final_risk_label,
            "final_risk_score": final_risk_score,
            "final_risk_components": final_risk_components,
            "final_risk_reasons": final_risk_reasons,
            "raw_model": {
                "prediction": prediction,
                "prediction_label": prediction_label,
                "delay_probability": delay_probability,
            },
            "delay_probability": delay_probability,
            "feature_importances": feature_importances,
            "analysis": analysis,
            "flight_2024_context": flight_2024_context,
            "flight_2024_risk": flight_2024_risk,
            "historical_weather": historical_weather,
            "historical_weather_risk": historical_weather_risk,
            "live_weather": live_weather,
            "weather_risk": weather_risk,
            "live_weather_used_in_final_score": False,
        }
    ), 200
