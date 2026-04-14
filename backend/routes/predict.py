from flask import Blueprint, request, jsonify
from services.predictor import make_prediction
from services.delay_analysis import analyze_delay_risk
from services.delay_data import estimate_arrivals
from extensions import db
from models import Prediction

predict_bp = Blueprint("predict", __name__)


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

    record = Prediction(
        carrier=carrier,
        airport=airport,
        month=month,
        arr_flights=arr_flights,
        prediction=prediction,
        prediction_label=prediction_label,
        delay_probability=delay_probability,
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
            "prediction_label": prediction_label,
            "delay_probability": delay_probability,
            "feature_importances": feature_importances,
            "analysis": analysis,
        }
    ), 200
