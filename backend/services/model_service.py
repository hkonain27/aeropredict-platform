import joblib
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), "../../data/processed/delay_model.pkl")
model = joblib.load(MODEL_PATH)