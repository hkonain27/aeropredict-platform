from flask import Blueprint, request, jsonify
from services.predictor import make_dummy_prediction

predict_bp = Blueprint("predict", __name__)

@predict_bp.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()

    # Handle case where no JSON is sent
    if not data:
        return jsonify({
            "status": "error",
            "message": "No input data provided"
        }), 400

    # Define required input fields
    required_fields = ["airline", "origin", "destination", "dep_hour", "day_of_week", "month"]

    # Check for missing fields in request
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({
            "status": "error",
            "message": f"Missing required fields: {', '.join(missing_fields)}"
        }), 400

    try:
        # Convert inputs to correct data types
        airline = str(data["airline"]).strip()
        origin = str(data["origin"]).strip()
        destination = str(data["destination"]).strip()
        dep_hour = int(data["dep_hour"])
        day_of_week = int(data["day_of_week"])
        month = int(data["month"])
    except (ValueError, TypeError):
        return jsonify({
            "status": "error",
            "message": "Invalid data types provided"
        }), 400

    # Validate text fields
    if not airline or not origin or not destination:
        return jsonify({
            "status": "error",
            "message": "airline, origin, and destination cannot be empty"
        }), 400

    # Validate value ranges
    if dep_hour < 0 or dep_hour > 23:
        return jsonify({
            "status": "error",
            "message": "dep_hour must be between 0 and 23"
        }), 400

    if day_of_week < 1 or day_of_week > 7:
        return jsonify({
            "status": "error",
            "message": "day_of_week must be between 1 and 7"
        }), 400

    if month < 1 or month > 12:
        return jsonify({
            "status": "error",
            "message": "month must be between 1 and 12"
        }), 400

    prediction, prediction_label, delay_probability = make_dummy_prediction({
        "airline": airline,
        "origin": origin,
        "destination": destination,
        "dep_hour": dep_hour,
        "day_of_week": day_of_week,
        "month": month
    })

    # Return structured JSON response
    return jsonify({
        "status": "success",
        "input": {
            "airline": airline,
            "origin": origin,
            "destination": destination,
            "dep_hour": dep_hour,
            "day_of_week": day_of_week,
            "month": month
        },
        "prediction": prediction,
        "prediction_label": prediction_label,
        "delay_probability": delay_probability
    }), 200