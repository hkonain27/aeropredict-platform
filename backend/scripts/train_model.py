import argparse
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


CATEGORICAL_FEATURES = ["airline", "origin", "destination"]
NUMERIC_FEATURES = ["dep_hour", "day_of_week", "distance"]
FEATURE_COLUMNS = CATEGORICAL_FEATURES + NUMERIC_FEATURES
TARGET_COLUMN = "delayed"


def load_dataset(csv_path: Path, sample_rows: int | None) -> pd.DataFrame:
    df = pd.read_csv(csv_path, usecols=FEATURE_COLUMNS + [TARGET_COLUMN])

    if sample_rows is None or sample_rows >= len(df):
        return df

    sampled, _ = train_test_split(
        df,
        train_size=sample_rows,
        random_state=42,
        stratify=df[TARGET_COLUMN],
    )
    return sampled.reset_index(drop=True)


def build_model(n_estimators: int, max_depth: int, min_samples_leaf: int) -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
            ("num", StandardScaler(), NUMERIC_FEATURES),
        ]
    )

    classifier = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced_subsample",
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", classifier),
        ]
    )


def main():
    parser = argparse.ArgumentParser(description="Train the flight delay model.")
    parser.add_argument(
        "--data",
        default="../../data/processed/flights_processed.csv",
        help="Path to the processed CSV relative to backend/scripts/",
    )
    parser.add_argument(
        "--output",
        default="../../data/processed/model.pkl",
        help="Where to write the trained model relative to backend/scripts/",
    )
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=250000,
        help="Stratified sample size to train on. Use 0 to train on the full dataset.",
    )
    parser.add_argument("--n-estimators", type=int, default=80)
    parser.add_argument("--max-depth", type=int, default=18)
    parser.add_argument("--min-samples-leaf", type=int, default=10)
    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent
    data_path = (base_dir / args.data).resolve()
    output_path = (base_dir / args.output).resolve()
    sample_rows = None if args.sample_rows == 0 else args.sample_rows

    print(f"Loading dataset from {data_path}")
    df = load_dataset(data_path, sample_rows)
    print(f"Training rows: {len(df):,}")
    print(f"Delay rate: {df[TARGET_COLUMN].mean():.4f}")

    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = build_model(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        min_samples_leaf=args.min_samples_leaf,
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
