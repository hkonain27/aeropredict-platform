import joblib
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), "../../data/processed/delay_model.pkl")
model = joblib.load(MODEL_PATH)

try:
    n_jobs_params = {name: 1 for name in model.get_params() if name.endswith("n_jobs")}
    if n_jobs_params:
        model.set_params(**n_jobs_params)
except (AttributeError, ValueError):
    pass
