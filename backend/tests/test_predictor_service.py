import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.model_service import MODEL_PATH  # noqa: E402
from services.predictor import FEATURE_IMPORTANCES, make_prediction  # noqa: E402


class FakeModel:
    def predict(self, frame):
        self.frame = frame
        return [1]

    def predict_proba(self, frame):
        self.frame = frame
        return [[0.24, 0.76]]


class PredictorServiceTestCase(unittest.TestCase):
    def test_model_artifact_exists(self):
        self.assertTrue(os.path.exists(MODEL_PATH))

    def test_feature_importances_cover_expected_inputs(self):
        feature_names = {item["feature"] for item in FEATURE_IMPORTANCES}

        self.assertEqual(feature_names, {"carrier", "airport", "month", "arr_flights"})
        self.assertAlmostEqual(sum(item["importance"] for item in FEATURE_IMPORTANCES), 100.0, places=1)

    def test_make_prediction_returns_valid_shape(self):
        with patch("services.predictor.model", FakeModel()):
            prediction, label, probability, feature_importances = make_prediction(
                {
                    "carrier": "UA",
                    "airport": "ORD",
                    "month": 7,
                    "arr_flights": 1200,
                }
            )

        self.assertIn(prediction, [0, 1])
        self.assertIn(label, ["High Delay Risk", "Lower Delay Risk"])
        self.assertGreaterEqual(probability, 0.0)
        self.assertLessEqual(probability, 1.0)
        self.assertEqual(feature_importances, FEATURE_IMPORTANCES)


if __name__ == "__main__":
    unittest.main()
