import pandas as pd
import numpy as np
from services.model_service import model

categorical_features = ['airline', 'origin', 'destination']
numeric_features = ['dep_hour', 'day_of_week', 'distance']

def _get_grouped_importances():
    preprocessor = model.named_steps['preprocessor']
    classifier = model.named_steps['classifier']
    ohe_features = preprocessor.transformers_[0][1].get_feature_names_out(categorical_features).tolist()
    all_features = ohe_features + numeric_features
    importances = classifier.feature_importances_

    groups = {f: 0.0 for f in categorical_features + numeric_features}
    for feat, imp in zip(all_features, importances):
        for group in categorical_features:
            if feat.startswith(group + "_"):
                groups[group] += imp
                break
        else:
            if feat in numeric_features:
                groups[feat] += imp

    total = sum(groups.values())
    return [{"feature": k, "importance": round(v / total * 100, 1)} for k, v in sorted(groups.items(), key=lambda x: -x[1])]

FEATURE_IMPORTANCES = _get_grouped_importances()


def make_prediction(data):
    input_df = pd.DataFrame([{
        "airline": data["airline"],
        "origin": data["origin"],
        "destination": data["destination"],
        "dep_hour": data["dep_hour"],
        "day_of_week": data["day_of_week"],
        "distance": data["distance"]
    }])

    prediction = int(model.predict(input_df)[0])
    delay_probability = round(float(model.predict_proba(input_df)[0][1]), 4)
    prediction_label = "Delay Likely" if prediction == 1 else "On Time Likely"

    return prediction, prediction_label, delay_probability, FEATURE_IMPORTANCES
