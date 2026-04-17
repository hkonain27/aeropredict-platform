from flask import Blueprint, request, jsonify
from extensions import db
from models import User

auth_bp = Blueprint("auth", __name__)


def _get_request_token():
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]
    return None


def _get_user_from_token():
    token = _get_request_token()
    if not token:
        return None
    return User.query.filter_by(auth_token=token).first()


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    email = str(data.get("email", "")).strip().lower()
    name = str(data.get("name", "")).strip()
    password = str(data.get("password", ""))

    if not email or not name or not password:
        return jsonify({"status": "error", "message": "Email, name, and password are required."}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"status": "error", "message": "A user with that email already exists."}), 400

    password = password.strip()
    user = User(email=email, name=name)
    user.set_password(password)
    user.generate_token()
    db.session.add(user)
    db.session.commit()

    return jsonify({"status": "success", "message": "User registered.", "token": user.auth_token, "profile": user.to_dict()})


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not email or not password:
        return jsonify({"status": "error", "message": "Email and password are required."}), 400

    password = password.strip()
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"status": "error", "message": "Invalid email or password."}), 401

    user.generate_token()
    db.session.commit()

    return jsonify({"status": "success", "token": user.auth_token, "profile": user.to_dict()})


@auth_bp.route("/profile", methods=["GET"])
def profile():
    user = _get_user_from_token()
    if not user:
        return jsonify({"status": "error", "message": "Unauthorized."}), 401
    return jsonify({"status": "success", "profile": user.to_dict()})


@auth_bp.route("/logout", methods=["POST"])
def logout():
    user = _get_user_from_token()
    if not user:
        return jsonify({"status": "error", "message": "Unauthorized."}), 401
    user.auth_token = None
    db.session.commit()
    return jsonify({"status": "success", "message": "Logged out."})
