import pandas as pd
from services.model_service import model
from services.delay_data import estimate_arrivals


FALLBACK_FEATURE_IMPORTANCES = [
    {"feature": "carrier", "importance": 45.0},
    {"feature": "airport", "importance": 12.5},
    {"feature": "month", "importance": 25.0},
    {"feature": "arr_flights", "importance": 17.5},
]


def _group_feature_importances():
    try:
        preprocessor = model.named_steps["preprocessor"]
        classifier = model.named_steps["classifier"]
        feature_names = preprocessor.get_feature_names_out()
        importances = classifier.feature_importances_
    except (AttributeError, KeyError):
        return FALLBACK_FEATURE_IMPORTANCES

    grouped = {
        "carrier": 0.0,
        "airport": 0.0,
        "month": 0.0,
        "arr_flights": 0.0,
    }

    for name, importance in zip(feature_names, importances):
        raw_name = name.split("__", 1)[1] if "__" in name else name

        if raw_name.startswith("carrier_"):
            grouped["carrier"] += float(importance)
        elif raw_name.startswith("airport_"):
            grouped["airport"] += float(importance)
        elif raw_name in grouped:
            grouped[raw_name] += float(importance)

    total = sum(grouped.values())
    if total <= 0:
        return FALLBACK_FEATURE_IMPORTANCES

    return [
        {"feature": feature, "importance": round((importance / total) * 100, 1)}
        for feature, importance in grouped.items()
    ]


FEATURE_IMPORTANCES = _group_feature_importances()


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
