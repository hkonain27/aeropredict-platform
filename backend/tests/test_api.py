import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app  # noqa: E402
from extensions import db  # noqa: E402


class ApiRoutesTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            }
        )
        self.client = self.app.test_client()

        with self.app.app_context():
            db.drop_all()
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_health_route(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_predict_route_returns_prediction_and_persists_record(self):
        payload = {
            "airline": "UA",
            "origin": "JFK",
            "destination": "LAX",
            "dep_hour": 17,
            "day_of_week": 5,
            "distance": 2475,
        }

        response = self.client.post("/predict", json=payload)
        body = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "success")
        self.assertIn("prediction", body)
        self.assertIn("prediction_label", body)
        self.assertIn("delay_probability", body)
        self.assertIn("feature_importances", body)
        self.assertIn("weather_context", body)
        self.assertIn("headline", body["weather_context"])
        self.assertIn("drivers", body["weather_context"])

        history_response = self.client.get("/predictions")
        history_body = history_response.get_json()

        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(len(history_body["predictions"]), 1)

    def test_predict_route_rejects_invalid_input(self):
        payload = {
            "airline": "UA",
            "origin": "JFK",
            "destination": "LAX",
            "dep_hour": 40,
            "day_of_week": 5,
            "distance": 2475,
        }

        response = self.client.post("/predict", json=payload)
        body = response.get_json()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(body["status"], "error")
        self.assertIn("dep_hour", body["message"])

    def test_predict_route_rejects_missing_fields(self):
        response = self.client.post(
            "/predict",
            json={
                "airline": "UA",
                "origin": "JFK",
            },
        )
        body = response.get_json()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(body["status"], "error")
        self.assertIn("destination", body["message"])

    def test_predict_route_rejects_invalid_types(self):
        response = self.client.post(
            "/predict",
            json={
                "airline": "UA",
                "origin": "JFK",
                "destination": "LAX",
                "dep_hour": "evening",
                "day_of_week": 5,
                "distance": 2475,
            },
        )
        body = response.get_json()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(body["status"], "error")
        self.assertIn("Invalid data types", body["message"])

    def test_predictions_history_returns_saved_predictions(self):
        self.client.post(
            "/predict",
            json={
                "airline": "DL",
                "origin": "ATL",
                "destination": "ORD",
                "dep_hour": 9,
                "day_of_week": 2,
                "distance": 606,
            },
        )

        response = self.client.get("/predictions")
        body = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "success")
        self.assertEqual(len(body["predictions"]), 1)
        self.assertEqual(body["predictions"][0]["airline"], "DL")

    def test_dashboard_route_returns_expected_sections(self):
        self.client.post(
            "/predict",
            json={
                "airline": "AA",
                "origin": "CLT",
                "destination": "MIA",
                "dep_hour": 12,
                "day_of_week": 3,
                "distance": 650,
            },
        )

        response = self.client.get("/api/dashboard-data")
        body = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("summaryCards", body)
        self.assertIn("monthlyDelayData", body)
        self.assertIn("airportRiskData", body)
        self.assertIn("causeBreakdown", body)
        self.assertIn("forecastData", body)
        self.assertIn("recentFlights", body)


if __name__ == "__main__":
    unittest.main()
