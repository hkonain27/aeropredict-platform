import os
import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.model_service import MODEL_PATH  # noqa: E402
from services.predictor import FEATURE_IMPORTANCES, make_prediction  # noqa: E402


class PredictorServiceTestCase(unittest.TestCase):
    def test_model_artifact_exists(self):
        self.assertTrue(os.path.exists(MODEL_PATH))

    def test_feature_importances_cover_expected_inputs(self):
        feature_names = {item["feature"] for item in FEATURE_IMPORTANCES}

        self.assertEqual(
            feature_names,
            {"airline", "origin", "destination", "dep_hour", "day_of_week", "distance"},
        )
        self.assertAlmostEqual(sum(item["importance"] for item in FEATURE_IMPORTANCES), 100.0, places=1)

    def test_make_prediction_returns_valid_shape(self):
        prediction, label, probability, feature_importances = make_prediction(
            {
                "airline": "UA",
                "origin": "JFK",
                "destination": "LAX",
                "dep_hour": 17,
                "day_of_week": 5,
                "distance": 2475,
            }
        )

        self.assertIn(prediction, [0, 1])
        self.assertIn(label, ["Delay Likely", "On Time Likely"])
        self.assertGreaterEqual(probability, 0.0)
        self.assertLessEqual(probability, 1.0)
        self.assertEqual(feature_importances, FEATURE_IMPORTANCES)


if __name__ == "__main__":
    unittest.main()
