import sys
import unittest
from pathlib import Path
from unittest.mock import patch


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

        self.weather_patcher = patch(
            "routes.predict.get_live_metar",
            return_value={
                "available": True,
                "station": "KORD",
                "cached": False,
                "flight_category": "VFR",
                "wind_speed_kt": 8,
                "wind_gust_kt": None,
                "visibility_miles": 10,
                "raw_text": "KORD test METAR",
                "observation_time": "2026-04-14T18:52:00Z",
            },
        )
        self.risk_patcher = patch(
            "routes.predict.score_weather_risk",
            return_value={
                "level": "Low",
                "score": 0,
                "drivers": ["No major live-weather delay signal detected."],
            },
        )
        self.historical_weather_patcher = patch(
            "routes.predict.get_historical_weather_context",
            return_value={
                "available": True,
                "airport": "ORD",
                "station": "ORD",
                "month": 7,
                "reference_year": 2024,
                "source": "Iowa State IEM ASOS/METAR archive",
                "observations": 700,
                "low_visibility_rate": 0.01,
                "low_ceiling_rate": 0.01,
                "gusty_wind_rate": 0.02,
                "precipitation_rate": 0.08,
                "thunderstorm_rate": 0.01,
                "winter_precip_rate": 0,
            },
        )
        self.historical_weather_risk_patcher = patch(
            "routes.predict.score_historical_weather_context",
            return_value={
                "level": "Low",
                "score": 0.28,
                "quality": 1.0,
                "drivers": ["Historical weather did not show a major disruption pattern for this month."],
            },
        )
        self.weather_patcher.start()
        self.risk_patcher.start()
        self.historical_weather_patcher.start()
        self.historical_weather_risk_patcher.start()

    def tearDown(self):
        self.historical_weather_risk_patcher.stop()
        self.historical_weather_patcher.stop()
        self.risk_patcher.stop()
        self.weather_patcher.stop()

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
        self.assertIn("final_risk_label", body)
        self.assertIn("final_risk_reasons", body)
        self.assertIn("raw_model", body)
        self.assertIn("delay_probability", body)
        self.assertIn("feature_importances", body)
        self.assertIn("analysis", body)
        self.assertIn("flight_2024_context", body)
        self.assertIn("flight_2024_risk", body)
        self.assertIn("historical_weather", body)
        self.assertIn("historical_weather_risk", body)
        self.assertIn("live_weather", body)
        self.assertIn("weather_risk", body)
        self.assertFalse(body["live_weather_used_in_final_score"])
        self.assertTrue(body["flight_2024_context"]["available"])
        self.assertEqual(body["weather_risk"]["level"], "Low")
        self.assertEqual(body["prediction_label"], body["final_risk_label"])
        self.assertEqual(
            body["raw_model"]["prediction_label"],
            "High Delay Risk" if body["prediction"] == 1 else "Lower Delay Risk",
        )
        self.assertIn("historical", body["analysis"])

        history_response = self.client.get("/predictions")
        history_body = history_response.get_json()

        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(len(history_body["predictions"]), 1)
        self.assertEqual(history_body["predictions"][0]["prediction_label"], body["final_risk_label"])
        self.assertEqual(history_body["predictions"][0]["delay_probability"], body["final_risk_score"])
        self.assertEqual(history_body["predictions"][0]["model_delay_probability"], body["delay_probability"])
        self.assertEqual(history_body["predictions"][0]["final_risk_score"], body["final_risk_score"])

    def test_predict_route_keeps_live_weather_display_only(self):
        with patch(
            "routes.predict.get_live_metar",
            return_value={
                "available": True,
                "station": "KCLT",
                "cached": False,
                "flight_category": "IFR",
                "wind_speed_kt": 30,
                "wind_gust_kt": 38,
                "visibility_miles": 2,
                "raw_text": "KCLT test METAR TS",
                "observation_time": "2026-04-14T18:52:00Z",
            },
        ), patch(
            "routes.predict.score_weather_risk",
            return_value={
                "level": "High",
                "score": 7,
                "drivers": ["Live test weather is high risk."],
            },
        ):
            high_weather_response = self.client.post(
                "/predict",
                json={
                    "carrier": "AA",
                    "airport": "CLT",
                    "month": 12,
                },
            )
        with patch(
            "routes.predict.get_live_metar",
            return_value={
                "available": True,
                "station": "KCLT",
                "cached": False,
                "flight_category": "VFR",
                "wind_speed_kt": 5,
                "wind_gust_kt": None,
                "visibility_miles": 10,
                "raw_text": "KCLT test METAR VFR",
                "observation_time": "2026-04-14T18:52:00Z",
            },
        ), patch(
            "routes.predict.score_weather_risk",
            return_value={
                "level": "Low",
                "score": 0,
                "drivers": ["No major live-weather delay signal detected."],
            },
        ):
            low_weather_response = self.client.post(
                "/predict",
                json={
                    "carrier": "AA",
                    "airport": "CLT",
                    "month": 12,
                },
            )
        body = high_weather_response.get_json()
        low_weather_body = low_weather_response.get_json()

        self.assertEqual(high_weather_response.status_code, 200)
        self.assertEqual(low_weather_response.status_code, 200)
        self.assertEqual(body["weather_risk"]["level"], "High")
        self.assertFalse(body["live_weather_used_in_final_score"])
        self.assertIn("final_risk_score", body)
        self.assertIn("final_risk_components", body)
        self.assertEqual(body["final_risk_score"], low_weather_body["final_risk_score"])
        self.assertNotIn("weather", {component["key"] for component in body["final_risk_components"]})
        self.assertIn("historical_weather", {component["key"] for component in body["final_risk_components"]})

        history_response = self.client.get("/predictions")
        history_body = history_response.get_json()

        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(len(history_body["predictions"]), 2)

    def test_predict_route_uses_2024_flight_records_as_weighted_supporting_signal(self):
        response = self.client.post(
            "/predict",
            json={
                "carrier": "DL",
                "airport": "ATL",
                "month": 7,
            },
        )
        body = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["raw_model"]["prediction_label"], "Lower Delay Risk")
        self.assertEqual(body["flight_2024_context"]["group_type"], "exact")
        self.assertEqual(body["flight_2024_risk"]["level"], "High")
        self.assertEqual(body["final_risk_label"], "Elevated Delay Risk")
        self.assertGreaterEqual(body["final_risk_score"], 0.4)
        self.assertLess(body["final_risk_score"], 0.6)

        history_response = self.client.get("/predictions")
        history_body = history_response.get_json()

        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(history_body["predictions"][0]["prediction_label"], "Elevated Delay Risk")

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

    def test_predict_route_rejects_unknown_carrier_and_airport(self):
        response = self.client.post(
            "/predict",
            json={
                "carrier": "ZZ",
                "airport": "XXX",
                "month": 6,
            },
        )
        body = response.get_json()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(body["status"], "error")
        self.assertIn("Carrier ZZ not found in historical dataset.", body["message"])
        self.assertIn("Airport XXX not found in historical dataset.", body["message"])

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
        self.assertEqual(body["recentFlights"][0]["delayProbability"], round(body["recentFlights"][0]["delayProbability"], 1))

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

    def test_delay_risk_lookup_rejects_unknown_airport_without_saving(self):
        response = self.client.post(
            "/api/delay-risk",
            json={
                "carrier": "AA",
                "airport": "XXX",
                "month": 12,
            },
        )
        body = response.get_json()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(body["status"], "error")
        self.assertEqual(body["message"], "Airport XXX not found in historical dataset.")

        history_response = self.client.get("/predictions")
        history_body = history_response.get_json()

        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(history_body["predictions"], [])


if __name__ == "__main__":
    unittest.main()
