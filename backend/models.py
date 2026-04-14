from datetime import datetime, timezone
from extensions import db

class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    carrier = db.Column(db.String(20), nullable=False)
    airport = db.Column(db.String(20), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    arr_flights = db.Column(db.Integer, nullable=False)
    prediction = db.Column(db.Integer, nullable=False)
    prediction_label = db.Column(db.String(30), nullable=False)
    delay_probability = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "carrier": self.carrier,
            "airport": self.airport,
            "month": self.month,
            "prediction": self.prediction,
            "prediction_label": self.prediction_label,
            "delay_probability": self.delay_probability,
            "created_at": self.created_at.isoformat(),
        }
