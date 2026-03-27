from flask import Flask, request, jsonify
from flask_cors import CORS
from routes.health import health_bp
from routes.predict import predict_bp

def create_app():
    app = Flask(__name__)
    #Add CORS
    CORS(app)
    app.register_blueprint(health_bp)
    app.register_blueprint(predict_bp)
    return app

app = create_app()

@app.route("/")
def index():
    return {"message": "Welcome to the Flask API!"}

# /predict endpoint
@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()

    if not data:
        return jsonify({
            "status": "error",
            "message": "No input data provided"
        }), 400

    # Extract input fields
    airline = data.get("airline")
    origin = data.get("origin")
    dest = data.get("dest")
    dep_hour = data.get("dep_hour")

    # Check required fields
    if airline is None or origin is None or dest is None or dep_hour is None:
        return jsonify({
            "status": "error",
            "message": "Missing one or more required fields: airline, origin, dest, dep_hour"
        }), 400

    try:
        dep_hour = int(dep_hour)
    except (ValueError, TypeError):
        return jsonify({
            "status": "error",
            "message": "dep_hour must be a number"
        }), 400

    # Dummy logic for now
    if dep_hour > 18:
        prediction = 1
        probability = 0.75
    else:
        prediction = 0
        probability = 0.25

    return jsonify({
        "status": "success",
        "prediction": prediction,
        "probability": probability
    })

@app.route("/api/dashboard-data", methods=["GET"])
def get_dashboard_data():
    summary_cards = [
        {"title": "Flights Analyzed", "value": "184,230", "change": "+12.4%", "icon": "Plane"},
        {"title": "Avg Delay", "value": "18 min", "change": "-3.2%", "icon": "Clock3"},
        {"title": "High-Risk Weather Days", "value": "47", "change": "+6.8%", "icon": "CloudRain"},
        {"title": "Prediction Accuracy", "value": "87.9%", "change": "+1.1%", "icon": "TrendingUp"},
    ]

    monthly_delay_data = [
        {"month": "Jan", "avgDelay": 22, "predicted": 20},
        {"month": "Feb", "avgDelay": 19, "predicted": 18},
        {"month": "Mar", "avgDelay": 25, "predicted": 23},
        {"month": "Apr", "avgDelay": 17, "predicted": 16},
        {"month": "May", "avgDelay": 15, "predicted": 14},
        {"month": "Jun", "avgDelay": 24, "predicted": 21},
        {"month": "Jul", "avgDelay": 29, "predicted": 26},
        {"month": "Aug", "avgDelay": 21, "predicted": 20},
        {"month": "Sep", "avgDelay": 16, "predicted": 15},
        {"month": "Oct", "avgDelay": 14, "predicted": 13},
        {"month": "Nov", "avgDelay": 20, "predicted": 18},
        {"month": "Dec", "avgDelay": 31, "predicted": 28},
    ]

    airport_risk_data = [
        {"airport": "ATL", "risk": 84},
        {"airport": "CLT", "risk": 73},
        {"airport": "JFK", "risk": 79},
        {"airport": "ORD", "risk": 88},
        {"airport": "DFW", "risk": 68},
        {"airport": "LAX", "risk": 55},
    ]

    cause_breakdown = [
        {"name": "Weather", "value": 34},
        {"name": "Carrier", "value": 26},
        {"name": "NAS", "value": 18},
        {"name": "Late Aircraft", "value": 15},
        {"name": "Security", "value": 7},
    ]

    forecast_data = [
        {"day": "Mon", "actual": 14, "predicted": 17},
        {"day": "Tue", "actual": 19, "predicted": 22},
        {"day": "Wed", "actual": 12, "predicted": 13},
        {"day": "Thu", "actual": 21, "predicted": 25},
        {"day": "Fri", "actual": 28, "predicted": 31},
        {"day": "Sat", "actual": 26, "predicted": 29},
        {"day": "Sun", "actual": 18, "predicted": 21},
    ]

    mock_flights = [
        {"id": "AA102", "route": "CLT → JFK", "airport": "CLT", "airline": "American", "weather": "Rain", "predictedDelay": 42, "status": "High Risk", "confidence": 91},
        {"id": "DL248", "route": "ATL → ORD", "airport": "ATL", "airline": "Delta", "weather": "Storm", "predictedDelay": 58, "status": "Critical", "confidence": 94},
        {"id": "UA771", "route": "EWR → LAX", "airport": "EWR", "airline": "United", "weather": "Clear", "predictedDelay": 9, "status": "Low Risk", "confidence": 82},
        {"id": "WN503", "route": "DAL → HOU", "airport": "DAL", "airline": "Southwest", "weather": "Wind", "predictedDelay": 27, "status": "Moderate", "confidence": 86},
        {"id": "B6291", "route": "JFK → MCO", "airport": "JFK", "airline": "JetBlue", "weather": "Snow", "predictedDelay": 49, "status": "High Risk", "confidence": 90},
    ]

    return jsonify({
        "summaryCards": summary_cards,
        "monthlyDelayData": monthly_delay_data,
        "airportRiskData": airport_risk_data,
        "causeBreakdown": cause_breakdown,
        "forecastData": forecast_data,
        "mockFlights": mock_flights
    })

if __name__ == "__main__":
    app.run(debug=True, port=5001)
