from flask import Blueprint, jsonify
from models import Prediction

predictions_history_bp = Blueprint("predictions_history", __name__)

@predictions_history_bp.route("/predictions", methods=["GET"])
def get_predictions():
    records = Prediction.query.order_by(Prediction.created_at.desc()).limit(50).all()
    return jsonify({"status": "success", "predictions": [r.to_dict() for r in records]}), 200
