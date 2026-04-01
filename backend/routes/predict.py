from flask import Blueprint, request, jsonify
from services.predictor import make_prediction
from extensions import db
from models import Prediction

predict_bp = Blueprint("predict", __name__)

@predict_bp.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()

    if not data:
        return jsonify({"status": "error", "message": "No input data provided"}), 400

    required_fields = ["airline", "origin", "destination", "dep_hour", "day_of_week", "distance"]
    missing_fields = [f for f in required_fields if f not in data]
    if missing_fields:
        return jsonify({"status": "error", "message": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    try:
        airline = str(data["airline"]).strip()
        origin = str(data["origin"]).strip()
        destination = str(data["destination"]).strip()
        dep_hour = int(data["dep_hour"])
        day_of_week = int(data["day_of_week"])
        distance = int(data["distance"])
    except (ValueError, TypeError):
        return jsonify({"status": "error", "message": "Invalid data types provided"}), 400
    if dep_hour < 0 or dep_hour > 23:
        return jsonify({"status": "error", "message": "dep_hour must be between 0 and 23"}), 400
    if day_of_week < 1 or day_of_week > 7:
        return jsonify({"status": "error", "message": "day_of_week must be between 1 and 7"}), 400
    if distance < 0:
        return jsonify({"status": "error", "message": "distance must be a positive number"}), 400

    prediction, prediction_label, delay_probability, feature_importances = make_prediction({
        "airline": airline, "origin": origin, "destination": destination,
        "dep_hour": dep_hour, "day_of_week": day_of_week, "distance": distance
    })

    record = Prediction(
        airline=airline, origin=origin, destination=destination,
        dep_hour=dep_hour, day_of_week=day_of_week, distance=distance,
        prediction=prediction, prediction_label=prediction_label, delay_probability=delay_probability
    )
    db.session.add(record)
    db.session.commit()

    return jsonify({
        "status": "success",
        "input": {
            "airline": airline, "origin": origin, "destination": destination,
            "dep_hour": dep_hour, "day_of_week": day_of_week, "distance": distance
        },
        "prediction": prediction,
        "prediction_label": prediction_label,
        "delay_probability": delay_probability,
        "feature_importances": feature_importances
    }), 200
