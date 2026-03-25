def preprocess_input(data):
    """
    Prepare incoming JSON data for the model.
    Right now it just returns the same structure,
    but later this will handle encoding, scaling, etc.
    """
    return {
        "airline": data["airline"],
        "origin": data["origin"],
        "destination": data["destination"],
        "dep_hour": data["dep_hour"],
        "day_of_week": data["day_of_week"],
        "month": data["month"]
    }


def make_dummy_prediction(data):
    """
    Temporary prediction logic.
    Later this will use the trained ML model.
    """
    processed_data = preprocess_input(data)

    dep_hour = processed_data["dep_hour"]

    if dep_hour >= 15:
        prediction = 1
        prediction_label = "Delay Likely"
        delay_probability = 0.72
    else:
        prediction = 0
        prediction_label = "On Time Likely"
        delay_probability = 0.28

    return prediction, prediction_label, delay_probability