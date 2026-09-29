"""Meaningful leakage, chronology and real-XGBoost artifact regression tests."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd

from aeropredict.features import FEATURE_COLUMNS
from aeropredict.train_model import chronological_split, save_artifacts, train, validate_training_matrix


def synthetic_flights(count: int = 60) -> pd.DataFrame:
    """Known signed outcomes with intentionally poisoned precomputed history."""
    departures = pd.date_range("2024-01-01T12:00:00Z", periods=count, freq="12h")
    frame = pd.DataFrame({
        "carrier": "MX", "flight_number": "101", "origin": "RDU", "destination": "MCO",
        "flight_key": "MX|101|RDU|MCO", "scheduled_dep_utc": departures,
        "prediction_as_of_utc": departures - pd.Timedelta(hours=24),
        "outcome_available_utc": departures + pd.Timedelta(hours=3),
        "arr_delay_min": np.arange(count, dtype=float) % 20 - 5,
        "dep_hour": departures.hour, "dep_month": departures.month,
        "dep_day_of_week": departures.dayofweek,
        "hist_flight_num_delay_avg": 999999.0,
        "temperature_f": 60 + np.arange(count) % 10,
        "wind_speed_mph": np.arange(count) % 15,
        "visibility_miles": 10.0, "precipitation_inches": 0.0,
    })
    return frame


class TrainingTests(unittest.TestCase):
    def test_split_preserves_ties_and_purges_unknown_outcomes(self):
        frame = synthetic_flights()
        # A distinct route at exactly the same timestamp must stay on one side.
        duplicate_time = frame.iloc[[47]].copy()
        duplicate_time["flight_key"] = "AA|202|RDU|MCO"
        duplicate_time["carrier"] = "AA"
        duplicate_time["flight_number"] = "202"
        frame = validate_training_matrix(pd.concat([frame, duplicate_time], ignore_index=True))
        fitting, holdout, boundary = chronological_split(frame)
        self.assertLess(fitting["prediction_as_of_utc"].max(), holdout["prediction_as_of_utc"].min())
        self.assertTrue((fitting["outcome_available_utc"] < boundary).all())
        self.assertEqual(len(set(fitting["prediction_as_of_utc"]) & set(holdout["prediction_as_of_utc"])), 0)

    def test_training_recomputes_poisoned_history_and_freezes_test_labels(self):
        frame = synthetic_flights()
        original_builder = __import__("aeropredict.train_model", fromlist=["build_history_features"]).build_history_features
        calls = []

        def capture(flights, history=None, as_of=None):
            output = original_builder(flights, history=history, as_of=as_of)
            calls.append((flights.copy(), history.copy(), as_of, output.copy()))
            return output

        with patch("aeropredict.train_model.build_history_features", side_effect=capture):
            artifact = train(frame, n_estimators=8, max_depth=2, n_jobs=1)
        self.assertEqual(len(calls), 2)
        self.assertIsNone(calls[0][2])
        self.assertIsNotNone(calls[1][2])
        self.assertTrue((calls[1][1]["outcome_available_utc"] < calls[1][2]).all())
        self.assertLess(calls[0][3]["hist_flight_num_delay_avg"].max(), 999999)
        self.assertFalse(set(calls[1][0]["scheduled_dep_utc"]) & set(artifact["history"]["scheduled_dep_utc"]))
        self.assertEqual(artifact["forecast_horizon_hours"], 24)
        self.assertTrue(artifact["metrics"]["metrics_apply_to_saved_model"])

    def test_holdout_targets_cannot_change_model_or_frozen_baseline(self):
        first = synthetic_flights()
        _, holdout, _ = chronological_split(first)
        second = first.copy()
        second.loc[second["prediction_as_of_utc"].isin(holdout["prediction_as_of_utc"]), "arr_delay_min"] += 900
        a = train(first, n_estimators=8, max_depth=2, n_jobs=1)
        b = train(second, n_estimators=8, max_depth=2, n_jobs=1)
        probe = first[list(FEATURE_COLUMNS)].iloc[[-1]]
        np.testing.assert_array_equal(a["pipeline"].predict(probe), b["pipeline"].predict(probe))
        pd.testing.assert_frame_equal(a["history"], b["history"])

    def test_artifact_round_trip_supports_missing_weather_and_unseen_breeze_flight(self):
        frame = synthetic_flights()
        frame.loc[0:5, "temperature_f"] = np.nan
        artifact = train(frame, n_estimators=8, max_depth=2, n_jobs=1)
        with tempfile.TemporaryDirectory() as directory:
            saved_path = save_artifacts(artifact, directory)
            restored = joblib.load(saved_path)
            example = frame[list(FEATURE_COLUMNS)].iloc[[0]].copy()
            example["flight_number"] = "9999"
            example["destination"] = "LAX"
            prediction = restored["pipeline"].predict(example)
            self.assertTrue(np.isfinite(prediction).all())
            self.assertEqual(restored["run_id"], artifact["run_id"])
            self.assertTrue(Path(directory, "metrics.json").is_file())
            self.assertTrue(Path(directory, "history_lookup.csv").is_file())
            importance = pd.read_csv(Path(directory, "feature_importance.csv"))
            self.assertIn("normalized_gain", importance)

    def test_refit_all_preserves_honest_evaluation_provenance(self):
        artifact = train(synthetic_flights(), refit_all=True, n_estimators=8, max_depth=2, n_jobs=1,
                         as_of="2024-02-01T00:00:00Z")
        self.assertEqual(artifact["fitted_rows"], 60)
        self.assertTrue((artifact["history"]["scheduled_dep_utc"] >= pd.Timestamp("2024-01-02T00:00:00Z")).all())
        self.assertFalse(artifact["metrics"]["metrics_apply_to_saved_model"])

    def test_rejects_naive_times_mixed_horizons_and_invalid_target(self):
        frame = synthetic_flights()
        frame["scheduled_dep_utc"] = frame["scheduled_dep_utc"].dt.tz_localize(None)
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            validate_training_matrix(frame)
        frame = synthetic_flights()
        frame.loc[0, "prediction_as_of_utc"] += pd.Timedelta(hours=1)
        with self.assertRaisesRegex(ValueError, "forecast horizon"):
            validate_training_matrix(frame)
        frame = synthetic_flights()
        frame.loc[0, "arr_delay_min"] = float("inf")
        with self.assertRaisesRegex(ValueError, "infinite"):
            validate_training_matrix(frame)


if __name__ == "__main__":
    unittest.main()
