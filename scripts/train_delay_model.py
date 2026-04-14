import pandas as pd
import joblib
from pathlib import Path

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
data_path = ROOT / "data" / "processed" / "delay_processed.csv"
model_path = ROOT / "data" / "processed" / "delay_model.pkl"

df = pd.read_csv(data_path, parse_dates=["period_date"])

# split features + target
X = df[["carrier", "airport", "month", "arr_flights"]]
y = df["is_delay_heavy"]

# train/test split (time-based)
train_df = df[df["period_date"] < "2025-01-01"]
test_df = df[df["period_date"] >= "2025-01-01"]

X_train = train_df[["carrier", "airport", "month", "arr_flights"]]
y_train = train_df["is_delay_heavy"]

X_test = test_df[["carrier", "airport", "month", "arr_flights"]]
y_test = test_df["is_delay_heavy"]

# preprocessing
categorical = ["carrier", "airport"]
numeric = ["month", "arr_flights"]

preprocessor = ColumnTransformer([
    ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
    ("num", StandardScaler(), numeric)
])

# model
model = Pipeline([
    ("preprocessor", preprocessor),
    ("classifier", RandomForestClassifier(
        n_estimators=200,
        max_depth=20,
        random_state=42,
        n_jobs=-1
    ))
])

# train
model.fit(X_train, y_train)

# evaluate
preds = model.predict(X_test)
probs = model.predict_proba(X_test)[:, 1]

print("accuracy:", accuracy_score(y_test, preds))
print("roc_auc:", roc_auc_score(y_test, probs))

# save model
joblib.dump(model, model_path)
print("model saved to:", model_path)