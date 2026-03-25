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

if __name__ == "__main__":
    app.run(debug=True, port=5001)