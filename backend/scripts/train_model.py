import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


CATEGORICAL_FEATURES = ["carrier", "airport"]
NUMERIC_FEATURES = ["month", "arr_flights"]
FEATURE_COLUMNS = CATEGORICAL_FEATURES + NUMERIC_FEATURES
TARGET_COLUMN = "is_delay_heavy"
DATE_COLUMN = "period_date"


def load_dataset(csv_path):
    df = pd.read_csv(csv_path, parse_dates=[DATE_COLUMN])
    required_columns = FEATURE_COLUMNS + [TARGET_COLUMN, DATE_COLUMN]
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
    return df.dropna(subset=required_columns)


def build_model(n_estimators, max_depth, min_samples_leaf, n_jobs):
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_FEATURES),
            ("num", StandardScaler(), NUMERIC_FEATURES),
        ]
    )

    classifier = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        random_state=42,
        n_jobs=n_jobs,
        class_weight="balanced_subsample",
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", classifier),
        ]
    )


def main():
    parser = argparse.ArgumentParser(description="Train the active AeroPredict delay-risk model.")
    parser.add_argument(
        "--data",
        default="../../data/processed/delay_processed.csv",
        help="Path to delay_processed.csv relative to backend/scripts/",
    )
    parser.add_argument(
        "--output",
        default="../../data/processed/delay_model.pkl",
        help="Where to write the trained model relative to backend/scripts/",
    )
    parser.add_argument(
        "--test-start-date",
        default="2025-01-01",
        help="Rows on or after this date are used for testing.",
    )
    parser.add_argument("--n-estimators", type=int, default=200)
    parser.add_argument("--max-depth", type=int, default=20)
    parser.add_argument("--min-samples-leaf", type=int, default=1)
    parser.add_argument("--n-jobs", type=int, default=-1)
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    data_path = (base_dir / args.data).resolve()
    output_path = (base_dir / args.output).resolve()

    print(f"Loading dataset from {data_path}")
    df = load_dataset(data_path)

    train_df = df[df[DATE_COLUMN] < args.test_start_date]
    test_df = df[df[DATE_COLUMN] >= args.test_start_date]
    if train_df.empty or test_df.empty:
        raise ValueError("Train/test split produced an empty set. Check --test-start-date.")

    X_train = train_df[FEATURE_COLUMNS]
    y_train = train_df[TARGET_COLUMN]
    X_test = test_df[FEATURE_COLUMNS]
    y_test = test_df[TARGET_COLUMN]

    print(f"Training rows: {len(train_df):,}")
    print(f"Testing rows: {len(test_df):,}")
    print(f"Training delay-heavy rate: {y_train.mean():.4f}")

    model = build_model(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        min_samples_leaf=args.min_samples_leaf,
        n_jobs=args.n_jobs,
    )

    print("Training Random Forest...")
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    proba = model.predict_proba(X_test)[:, 1]
    accuracy = accuracy_score(y_test, preds)
    roc_auc = roc_auc_score(y_test, proba)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_path)

    print(f"Accuracy: {accuracy:.4f}")
    print(f"ROC AUC: {roc_auc:.4f}")
    print(f"Saved model to {output_path}")


if __name__ == "__main__":
    main()
