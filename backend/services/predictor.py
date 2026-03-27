import pandas as pd
from services.model_service import model


def make_prediction(data):
    input_df = pd.DataFrame([{
        "airline": data["airline"],
        "origin": data["origin"],
        "destination": data["destination"],
        "dep_hour": data["dep_hour"],
        "day_of_week": data["day_of_week"],
        "month": data["month"],
        "distance": data["distance"]
    }])

    prediction = int(model.predict(input_df)[0])
    delay_probability = round(float(model.predict_proba(input_df)[0][1]), 4)
    prediction_label = "Delay Likely" if prediction == 1 else "On Time Likely"

    return prediction, prediction_label, delay_probability
