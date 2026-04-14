import pandas as pd
from services.model_service import model
from services.delay_data import estimate_arrivals

FEATURE_IMPORTANCES = [
    {"feature": "carrier", "importance": 45.0},
    {"feature": "airport", "importance": 40.0},
    {"feature": "month", "importance": 15.0},
]

def make_prediction(data):
    arr_flights = data.get("arr_flights") or estimate_arrivals(
        data["carrier"],
        data["airport"],
        data["month"],
    )

    input_df = pd.DataFrame([{
        "carrier": data["carrier"],
        "airport": data["airport"],
        "month": data["month"],
        "arr_flights": arr_flights,
    }])

    prediction = int(model.predict(input_df)[0])
    delay_probability = round(float(model.predict_proba(input_df)[0][1]), 4)
    prediction_label = "High Delay Risk" if prediction == 1 else "Lower Delay Risk"

    return prediction, prediction_label, delay_probability, FEATURE_IMPORTANCES
