"""Fit and evaluate a reproducible arrival-delay regressor.

The holdout is a *frozen-history* evaluation: its flight-history feature uses
only outcomes that were known when the first holdout prediction would have
been made. This is deliberately more conservative than refreshing history
with labels revealed during the test period. Historical observed weather is
still an imperfect proxy for the forecast available at prediction time.

Only load joblib artifacts created by a trusted training process: joblib uses
pickle and can execute code when an artifact is loaded.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor

from .features import (
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    NUMERIC_FEATURES,
    build_history_features,
    make_flight_key,
    RollingHistory,
)

LOGGER = logging.getLogger(__name__)
SCHEMA_VERSION = 1
TARGET_COLUMN = "arr_delay_min"
HISTORY_COLUMNS = ["flight_key", "scheduled_dep_utc", "outcome_available_utc", TARGET_COLUMN]


def load_training_matrix(path: str | Path) -> pd.DataFrame:
    """Read a prepared matrix without losing carrier/flight-number strings."""
    frame = pd.read_csv(path, dtype={name: "string" for name in CATEGORICAL_FEATURES})
    return validate_training_matrix(frame)


def validate_training_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    """Reject ambiguous timestamps, invalid targets and inconsistent horizons."""
    required = set(FEATURE_COLUMNS) | set(HISTORY_COLUMNS) | {"prediction_as_of_utc"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Training matrix is missing required columns: {', '.join(missing)}")
    frame = frame.copy()
    if len(frame) < 5:
        raise ValueError("At least five valid flights are required for a chronological 80/20 split.")
    for name in ("scheduled_dep_utc", "outcome_available_utc", "prediction_as_of_utc"):
        # Prepared timestamps must include an offset: interpreting naive local
        # times as UTC here would silently corrupt the learning history.
        for value in frame[name]:
            if pd.isna(value) or pd.Timestamp(value).tzinfo is None:
                raise ValueError(f"{name} must contain explicit, timezone-aware timestamps.")
        frame[name] = pd.to_datetime(frame[name], utc=True, errors="raise", format="mixed")
    for name in CATEGORICAL_FEATURES:
        frame[name] = frame[name].astype("string").str.strip().str.upper()
        if frame[name].isna().any() or frame[name].eq("").any():
            raise ValueError(f"{name} contains an empty flight identity.")
        frame[name] = frame[name].astype(str)
    if frame["flight_key"].isna().any() or frame["flight_key"].astype(str).str.strip().eq("").any():
        raise ValueError("flight_key must identify a carrier, flight number and route.")
    expected_keys = [make_flight_key(*row) for row in frame[list(CATEGORICAL_FEATURES)].itertuples(index=False, name=None)]
    if not frame["flight_key"].eq(expected_keys).all():
        raise ValueError("flight_key does not match the normalized carrier, flight number and route.")
    for name in list(NUMERIC_FEATURES) + [TARGET_COLUMN]:
        frame[name] = pd.to_numeric(frame[name], errors="raise")
        if np.isinf(frame[name].to_numpy(dtype=float)).any():
            raise ValueError(f"{name} contains an infinite value.")
    if frame[TARGET_COLUMN].isna().any():
        raise ValueError("Arrival delay targets must be observed finite numbers.")
    for column, lower, upper in (("dep_hour", 0, 23), ("dep_month", 1, 12), ("dep_day_of_week", 0, 6)):
        if not frame[column].between(lower, upper).all() or frame[column].mod(1).ne(0).any():
            raise ValueError(f"{column} must contain integers between {lower} and {upper}.")
    if (frame["outcome_available_utc"] <= frame["scheduled_dep_utc"]).any():
        raise ValueError("Outcome availability must be after the scheduled departure.")
    horizon = (frame["scheduled_dep_utc"] - frame["prediction_as_of_utc"]).dt.total_seconds() / 3600
    if (horizon < 0).any() or not np.allclose(horizon, horizon.iloc[0], atol=1e-6, rtol=0):
        raise ValueError("Train one model per consistent nonnegative forecast horizon.")
    identities = ["flight_key", "scheduled_dep_utc"]
    if frame.duplicated(identities).any():
        raise ValueError("Training matrix contains duplicate flight instances; deduplicate raw inputs first.")
    return frame.sort_values(["prediction_as_of_utc", "flight_key"], kind="stable").reset_index(drop=True)


def chronological_split(
    frame: pd.DataFrame, test_fraction: float = 0.2
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp]:
    """Split near 80/20 without placing equal prediction timestamps on both sides.

    Training labels must have become available *before* the first test
    prediction. Purging flights still in the air at the boundary prevents
    leaking those future arrivals into either model fitting or history.
    """
    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be between zero and one.")
    ordered = frame.sort_values("prediction_as_of_utc", kind="stable")
    timestamps = ordered["prediction_as_of_utc"]
    candidate_positions = np.flatnonzero(timestamps.ne(timestamps.shift()).to_numpy())[1:]
    if not len(candidate_positions):
        raise ValueError("A chronological split requires at least two different prediction timestamps.")
    desired = len(frame) * (1 - test_fraction)
    position = int(candidate_positions[np.argmin(np.abs(candidate_positions - desired))])
    boundary = timestamps.iloc[position]
    train = ordered[(timestamps < boundary) & (ordered["outcome_available_utc"] < boundary)].copy()
    test = ordered[timestamps >= boundary].copy()
    if len(train) < 2 or test.empty:
        raise ValueError("Too few completed flights remain after purging unavailable training outcomes.")
    return train.reset_index(drop=True), test.reset_index(drop=True), boundary


def make_regressor(
    *, n_estimators: int = 400, max_depth: int = 6, learning_rate: float = 0.05,
    n_jobs: int = 2, random_state: int = 42,
) -> Pipeline:
    """Construct preprocessing that is fitted exclusively on training rows.

    Tree models need no scaler. Missing numeric weather is median-imputed,
    with missingness indicators. Bounded one-hot cardinality keeps repeated
    retraining practical; unseen flights are handled by the historical feature
    and airport/carrier predictors instead of failing on unknown categories.
    """
    if n_estimators < 1 or max_depth < 1 or not 0 < learning_rate <= 1 or n_jobs < 1:
        raise ValueError("Use positive tree count, depth and worker count, and learning rate in (0, 1].")
    preprocessing = ColumnTransformer(
        transformers=[
            ("categorical", OneHotEncoder(
                handle_unknown="ignore", min_frequency=2, max_categories=256,
                sparse_output=True, dtype=np.float32,
            ), list(CATEGORICAL_FEATURES)),
            ("numeric", SimpleImputer(
                strategy="median", add_indicator=True, keep_empty_features=True,
            ), list(NUMERIC_FEATURES)),
        ],
        sparse_threshold=1.0,
    )
    model = XGBRegressor(
        objective="reg:squarederror", eval_metric="rmse", tree_method="hist",
        n_estimators=n_estimators, max_depth=max_depth, learning_rate=learning_rate,
        min_child_weight=10, subsample=0.8, colsample_bytree=0.9, reg_lambda=5,
        random_state=random_state, n_jobs=n_jobs,
    )
    return Pipeline([("preprocessor", preprocessing), ("regressor", model)])


def regression_metrics(actual: Any, predicted: Any) -> dict[str, float]:
    """Report signed-delay regression errors in minutes, without clipping."""
    return {
        "mae_minutes": float(mean_absolute_error(actual, predicted)),
        "rmse_minutes": float(np.sqrt(mean_squared_error(actual, predicted))),
    }


def train(
    frame: pd.DataFrame, *, refit_all: bool = False, as_of: str | pd.Timestamp | None = None,
    history: pd.DataFrame | None = None,
    n_estimators: int = 400, max_depth: int = 6, learning_rate: float = 0.05,
    n_jobs: int = 2, random_state: int = 42,
) -> dict[str, Any]:
    """Evaluate a chronological model and return a self-contained artifact.

    ``refit_all=False`` preserves exactly the evaluated model and the history
    available at its test boundary. ``True`` fits a new deployment model on all
    completed records; its metrics retain the earlier holdout provenance and
    do not claim that the refitted model was independently evaluated.
    """
    frame = validate_training_matrix(frame)
    # The prep sidecar retains completed flights lost by the weather inner join.
    # Combining and validating both sources also rejects conflicting labels.
    available_history = RollingHistory(pd.concat(
        [history[HISTORY_COLUMNS], frame[HISTORY_COLUMNS]], ignore_index=True
    ) if history is not None else frame[HISTORY_COLUMNS]).history
    trained_at = pd.Timestamp.now(tz="UTC")
    cutoff = trained_at if as_of is None else pd.Timestamp(as_of)
    if cutoff.tzinfo is None:
        raise ValueError("as_of must include an explicit timezone.")
    cutoff = cutoff.tz_convert("UTC")
    if cutoff > trained_at:
        raise ValueError("as_of cannot be in the future.")
    unavailable_count = int((frame["outcome_available_utc"] >= cutoff).sum())
    frame = frame[frame["outcome_available_utc"] < cutoff].copy()
    available_history = available_history[available_history['outcome_available_utc'] < cutoff]
    if len(frame) < 5:
        raise ValueError("At least five flights with known outcomes are required as of training time.")
    train_frame, test_frame, test_boundary = chronological_split(frame)
    train_history = available_history[available_history['outcome_available_utc'] < test_boundary].copy()
    training_features = build_history_features(train_frame, history=train_history)
    testing_features = build_history_features(test_frame, history=train_history, as_of=test_boundary)
    model_parameters = dict(
        n_estimators=n_estimators, max_depth=max_depth, learning_rate=learning_rate,
        n_jobs=n_jobs, random_state=random_state,
    )
    evaluated_pipeline = make_regressor(**model_parameters)
    evaluated_pipeline.fit(training_features[list(FEATURE_COLUMNS)], train_frame[TARGET_COLUMN])
    predictions = evaluated_pipeline.predict(testing_features[list(FEATURE_COLUMNS)])
    baseline = testing_features["hist_flight_num_delay_avg"].to_numpy(dtype=float)
    baseline_metrics = regression_metrics(test_frame[TARGET_COLUMN], baseline)
    metrics: dict[str, Any] = {
        "model": regression_metrics(test_frame[TARGET_COLUMN], predictions),
        "historical_mean_baseline": baseline_metrics,
        "zero_delay_baseline": regression_metrics(test_frame[TARGET_COLUMN], np.zeros(len(test_frame))),
        "train_rows": len(train_frame), "test_rows": len(test_frame),
        "test_fraction_actual": float(len(test_frame) / len(frame)),
        "purged_boundary_rows": int((frame["prediction_as_of_utc"] < test_boundary).sum() - len(train_frame)),
        "excluded_unavailable_outcomes": unavailable_count,
        "train_prediction_start_utc": train_frame["prediction_as_of_utc"].min().isoformat(),
        "train_prediction_end_utc": train_frame["prediction_as_of_utc"].max().isoformat(),
        "test_prediction_start_utc": test_boundary.isoformat(),
        "test_prediction_end_utc": test_frame["prediction_as_of_utc"].max().isoformat(),
        "evaluation": "chronological_80_20_frozen_history_at_first_test_prediction",
        "weather_limitation": "Historical observed weather is a proxy for live forecasts; this test does not measure forecast error.",
        "metrics_apply_to_saved_model": not refit_all,
        "refit_all": refit_all,
    }
    metrics["beats_historical_baseline_mae"] = metrics["model"]["mae_minutes"] < baseline_metrics["mae_minutes"]
    if refit_all:
        artifact_history = available_history.copy()
        all_features = build_history_features(frame, history=artifact_history)
        pipeline = make_regressor(**model_parameters)
        pipeline.fit(all_features[list(FEATURE_COLUMNS)], frame[TARGET_COLUMN])
        artifact_cutoff = cutoff
    else:
        pipeline, artifact_history, artifact_cutoff = evaluated_pipeline, train_history, test_boundary
    history_last_outcome = artifact_history["outcome_available_utc"].max()
    fitted_rows = len(frame) if refit_all else len(train_frame)
    # Future predictions cannot use observations older than this window.
    # Keeping only the lookup tail makes an artifact practical even when the
    # fitted model used millions of historical flights.
    artifact_history = artifact_history[
        artifact_history["scheduled_dep_utc"] >= artifact_cutoff - pd.Timedelta(days=30)
    ].copy()
    horizon = (frame["scheduled_dep_utc"].iloc[0] - frame["prediction_as_of_utc"].iloc[0]).total_seconds() / 3600
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": uuid.uuid4().hex,
        "pipeline": pipeline,
        "feature_columns": list(FEATURE_COLUMNS),
        "categorical_features": list(CATEGORICAL_FEATURES),
        "numeric_features": list(NUMERIC_FEATURES),
        "target_column": TARGET_COLUMN,
        "history": artifact_history.reset_index(drop=True),
        "history_window_days": 30,
        "history_default_minutes": 0.0,
        "history_fallback": "past_only_global_mean_then_zero",
        "history_last_outcome_utc": history_last_outcome.isoformat(),
        "fitted_rows": fitted_rows,
        "forecast_horizon_hours": float(horizon),
        "training_cutoff_utc": artifact_cutoff.isoformat(),
        "trained_at_utc": trained_at.isoformat(),
        "model_parameters": model_parameters,
        "metrics": metrics,
    }


def _atomic_write(destination: Path, writer: Any) -> None:
    """Commit one file using a temporary file on the same filesystem."""
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        writer(temporary)
        with temporary.open("r+b") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def save_artifacts(bundle: dict[str, Any], output_directory: str | Path) -> Path:
    """Write an atomic runtime bundle and separately generated review reports.

    Runtime loads only model.joblib. Its model, preprocessing, history and
    metadata cannot be mixed between runs. Reports contain the same run ID,
    are informational, and are never dependencies of inference.
    """
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    pipeline = bundle["pipeline"]
    names = pipeline.named_steps["preprocessor"].get_feature_names_out()
    importance = pd.DataFrame({
        "run_id": bundle["run_id"], "feature": names,
        "normalized_gain": pipeline.named_steps["regressor"].feature_importances_,
    }).sort_values("normalized_gain", ascending=False)
    history = bundle["history"].copy()
    history["run_id"] = bundle["run_id"]
    # Retain dated observations, not a permanently stale scalar per flight.
    # Inference recomputes the 30-day lookup for each requested departure.
    _atomic_write(output / "history_lookup.csv", lambda path: history.to_csv(path, index=False))
    _atomic_write(output / "feature_importance.csv", lambda path: importance.to_csv(path, index=False))
    report = {"run_id": bundle["run_id"], "trained_at_utc": bundle["trained_at_utc"], **bundle["metrics"]}
    _atomic_write(output / "metrics.json", lambda path: path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8"))
    model_path = output / "model.joblib"
    _atomic_write(model_path, lambda path: joblib.dump(bundle, path, compress=3))
    return model_path


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point for reproducible local or scheduled training."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="CSV produced by data_prep.py")
    parser.add_argument("--output", type=Path, default=Path("artifacts"), help="Artifact directory (default: artifacts)")
    parser.add_argument("--refit-all", action="store_true", help="Refit on all known outcomes after evaluating the 80/20 split")
    parser.add_argument("--as-of", help="UTC cutoff for available outcomes, e.g. 2025-01-01T00:00:00Z")
    parser.add_argument("--n-estimators", type=int, default=400)
    parser.add_argument("--max-depth", type=int, default=6)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--n-jobs", type=int, default=2)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        history_path = args.input.with_suffix('.history.csv')
        history = pd.read_csv(history_path) if history_path.is_file() else None
        bundle = train(
            load_training_matrix(args.input), refit_all=args.refit_all, as_of=args.as_of,
            history=history,
            n_estimators=args.n_estimators, max_depth=args.max_depth,
            learning_rate=args.learning_rate, n_jobs=args.n_jobs,
        )
        model_path = save_artifacts(bundle, args.output)
    except (OSError, ValueError, KeyError) as error:
        LOGGER.error("Training failed: %s", error)
        return 1
    scores = bundle["metrics"]
    print(f"Holdout MAE: {scores['model']['mae_minutes']:.2f} minutes")
    print(f"Holdout RMSE: {scores['model']['rmse_minutes']:.2f} minutes")
    print(f"Historical-mean baseline MAE: {scores['historical_mean_baseline']['mae_minutes']:.2f} minutes")
    print(f"Saved model and preprocessing/history bundle: {model_path}")
    if args.refit_all:
        print("Saved model was refitted on all known outcomes; scores describe the earlier holdout model.")
    if not scores["beats_historical_baseline_mae"]:
        print("Model did not improve on the historical baseline MAE; review before deploying.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
