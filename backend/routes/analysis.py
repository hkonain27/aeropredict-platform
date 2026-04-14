from flask import Blueprint, jsonify, request

from services.delay_analysis import analyze_delay_risk


analysis_bp = Blueprint("analysis", __name__)


def _read_payload():
    if request.method == "GET":
        return {
            "carrier": request.args.get("carrier"),
            "airport": request.args.get("airport"),
            "month": request.args.get("month"),
        }
    return request.get_json()


def _validate_payload(data):
    if not data:
        return None, ("No input data provided", 400)

    required_fields = ["carrier", "airport", "month"]
    missing_fields = [field for field in required_fields if data.get(field) in [None, ""]]
    if missing_fields:
        return None, (f"Missing required fields: {', '.join(missing_fields)}", 400)

    try:
        parsed = {
            "carrier": str(data["carrier"]).strip().upper(),
            "airport": str(data["airport"]).strip().upper(),
            "month": int(data["month"]),
        }
    except (ValueError, TypeError):
        return None, ("Invalid data types provided", 400)

    if len(parsed["carrier"]) not in [2, 3]:
        return None, ("carrier must be a 2-3 character carrier code", 400)

    if len(parsed["airport"]) != 3:
        return None, ("airport must be a 3-letter airport code", 400)

    if parsed["month"] < 1 or parsed["month"] > 12:
        return None, ("month must be between 1 and 12", 400)

    return parsed, None


@analysis_bp.route("/api/delay-risk", methods=["GET", "POST"])
def delay_risk_lookup():
    parsed, error = _validate_payload(_read_payload())
    if error:
        message, status_code = error
        return jsonify({"status": "error", "message": message}), status_code

    return jsonify(analyze_delay_risk(parsed)), 200
