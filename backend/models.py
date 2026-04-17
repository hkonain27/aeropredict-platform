import secrets
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    auth_token = db.Column(db.String(128), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_token(self):
        self.auth_token = secrets.token_urlsafe(48)
        return self.auth_token

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
        }


class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    carrier = db.Column(db.String(20), nullable=False)
    airport = db.Column(db.String(20), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    arr_flights = db.Column(db.Integer, nullable=False)
    prediction = db.Column(db.Integer, nullable=False)
    prediction_label = db.Column(db.String(30), nullable=False)
    delay_probability = db.Column(db.Float, nullable=False)
    final_risk_score = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        displayed_probability = self.final_risk_score if self.final_risk_score is not None else self.delay_probability
        return {
            "id": self.id,
            "carrier": self.carrier,
            "airport": self.airport,
            "month": self.month,
            "prediction": self.prediction,
            "prediction_label": self.prediction_label,
            "delay_probability": displayed_probability,
            "model_delay_probability": self.delay_probability,
            "final_risk_score": self.final_risk_score,
            "created_at": self.created_at.isoformat(),
        }
