from datetime import datetime, timezone
from extensions import db

class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    airline = db.Column(db.String(10), nullable=False)
    origin = db.Column(db.String(10), nullable=False)
    destination = db.Column(db.String(10), nullable=False)
    dep_hour = db.Column(db.Integer, nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)
    distance = db.Column(db.Integer, nullable=False)
    prediction = db.Column(db.Integer, nullable=False)
    prediction_label = db.Column(db.String(20), nullable=False)
    delay_probability = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "airline": self.airline,
            "origin": self.origin,
            "destination": self.destination,
            "dep_hour": self.dep_hour,
            "day_of_week": self.day_of_week,
            "distance": self.distance,
            "prediction": self.prediction,
            "prediction_label": self.prediction_label,
            "delay_probability": self.delay_probability,
            "created_at": self.created_at.isoformat(),
        }
