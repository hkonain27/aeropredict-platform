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
            "carrier": "UA",
            "airport": "ORD",
            "month": 7,
        }

        response = self.client.post("/predict", json=payload)
        body = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "success")
        self.assertIn("prediction", body)
        self.assertIn("prediction_label", body)
        self.assertIn("delay_probability", body)
        self.assertIn("feature_importances", body)
        self.assertIn("analysis", body)
        self.assertIn("historical", body["analysis"])

        history_response = self.client.get("/predictions")
        history_body = history_response.get_json()

        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(len(history_body["predictions"]), 1)

    def test_predict_route_rejects_invalid_input(self):
        payload = {
            "carrier": "UA",
            "airport": "ORD",
            "month": 40,
        }

        response = self.client.post("/predict", json=payload)
        body = response.get_json()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(body["status"], "error")
        self.assertIn("month", body["message"])

    def test_predictions_history_returns_saved_predictions(self):
        self.client.post(
            "/predict",
            json={
                "carrier": "DL",
                "airport": "ATL",
                "month": 7,
            },
        )

        response = self.client.get("/predictions")
        body = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "success")
        self.assertEqual(len(body["predictions"]), 1)
        self.assertEqual(body["predictions"][0]["carrier"], "DL")

    def test_dashboard_route_returns_expected_sections(self):
        self.client.post(
            "/predict",
            json={
                "carrier": "AA",
                "airport": "CLT",
                "month": 12,
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

    def test_delay_risk_lookup_returns_historical_analysis_without_saving(self):
        response = self.client.post(
            "/api/delay-risk",
            json={
                "carrier": "AA",
                "airport": "CLT",
                "month": 12,
            },
        )
        body = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "success")
        self.assertIn("model", body)
        self.assertIn("historical", body)
        self.assertIn("matched_records", body)

        history_response = self.client.get("/predictions")
        history_body = history_response.get_json()

        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(history_body["predictions"], [])


if __name__ == "__main__":
    unittest.main()
