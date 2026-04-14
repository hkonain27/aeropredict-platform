import pandas as pd

from services.predictor import make_prediction
from services.delay_data import estimate_arrivals, load_delay_data


CAUSE_COLUMNS = [
    ("carrier_delay", "Airline operations"),
    ("weather_delay", "Weather"),
    ("nas_delay", "Air traffic system"),
    ("security_delay", "Security"),
    ("late_aircraft_delay", "Late inbound aircraft"),
]


def _safe_round(value, digits=4):
    if value is None or pd.isna(value):
        return None
    return round(float(value), digits)


def _weighted_delay_rate(frame):
    arrivals = float(frame["arr_flights"].sum())
    if arrivals <= 0:
        return None
    return float(frame["arr_del15"].sum()) / arrivals


def _cause_breakdown(frame):
    totals = []
    total_delay_minutes = 0.0

    for column, label in CAUSE_COLUMNS:
        minutes = float(frame[column].sum())
        total_delay_minutes += minutes
        totals.append({"name": label, "minutes": round(minutes, 1)})

    if total_delay_minutes <= 0:
        return []

    return [
        {
            **item,
            "share": round((item["minutes"] / total_delay_minutes) * 100, 1),
        }
        for item in totals
    ]


def _summarize(frame, label):
    if frame.empty:
        return None

    arrivals = float(frame["arr_flights"].sum())
    delayed_arrivals = float(frame["arr_del15"].sum())
    delay_minutes = float(frame["arr_delay"].sum())
    cancelled = float(frame["arr_cancelled"].sum())
    diverted = float(frame["arr_diverted"].sum())

    return {
        "label": label,
        "records": int(len(frame)),
        "years": sorted(int(year) for year in frame["year"].dropna().unique().tolist()),
        "arrivals": int(round(arrivals)),
        "delayed_arrivals": int(round(delayed_arrivals)),
        "delay_rate": _safe_round(_weighted_delay_rate(frame)),
        "avg_delay_minutes_per_delayed_arrival": _safe_round(
            delay_minutes / delayed_arrivals if delayed_arrivals > 0 else None,
            1,
        ),
        "cancel_rate": _safe_round(cancelled / arrivals if arrivals > 0 else None),
        "diversion_rate": _safe_round(diverted / arrivals if arrivals > 0 else None),
        "cause_breakdown": _cause_breakdown(frame),
    }


def _reliability(summary):
    if not summary:
        return "No historical match"
    if summary["records"] >= 3 and summary["arrivals"] >= 500:
        return "Strong"
    if summary["records"] >= 2 or summary["arrivals"] >= 200:
        return "Moderate"
    return "Limited"


def _risk_label(model_probability, historical_rate):
    if model_probability >= 0.65 or (historical_rate is not None and historical_rate >= 0.25):
        return "High Delay Risk"
    if model_probability >= 0.4 or (historical_rate is not None and historical_rate >= 0.2):
        return "Elevated Delay Risk"
    return "Lower Delay Risk"


def _records_for_display(frame):
    if frame.empty:
        return []

    rows = frame.sort_values(["year", "month"], ascending=[False, False]).head(8)
    records = []
    for _, row in rows.iterrows():
        records.append(
            {
                "year": int(row["year"]),
                "month": int(row["month"]),
                "carrier": row["carrier"],
                "carrier_name": row["carrier_name"],
                "airport": row["airport"],
                "airport_name": row["airport_name"],
                "arrivals": int(round(float(row["arr_flights"]))),
                "delayed_arrivals": int(round(float(row["arr_del15"]))),
                "delay_rate": _safe_round(row["delay_rate"]),
            }
        )
    return records


def analyze_delay_risk(payload, prediction_result=None):
    carrier = str(payload["carrier"]).upper().strip()
    airport = str(payload["airport"]).upper().strip()
    month = int(payload["month"])
    arr_flights = int(payload.get("arr_flights") or estimate_arrivals(carrier, airport, month))

    if prediction_result is None:
        prediction, prediction_label, delay_probability, feature_importances = make_prediction(
            {
                "carrier": carrier,
                "airport": airport,
                "month": month,
                "arr_flights": arr_flights,
            }
        )
    else:
        prediction = prediction_result["prediction"]
        prediction_label = prediction_result["prediction_label"]
        delay_probability = prediction_result["delay_probability"]
        feature_importances = prediction_result["feature_importances"]

    df = load_delay_data()

    exact = df[(df["carrier"] == carrier) & (df["airport"] == airport) & (df["month"] == month)]
    carrier_airport = df[(df["carrier"] == carrier) & (df["airport"] == airport)]
    airport_month = df[(df["airport"] == airport) & (df["month"] == month)]
    carrier_month = df[(df["carrier"] == carrier) & (df["month"] == month)]
    month_all = df[df["month"] == month]
    airport_all = df[df["airport"] == airport]
    carrier_all = df[df["carrier"] == carrier]

    context_candidates = [
        (exact, "Exact carrier-airport-month match"),
        (carrier_airport, "Same carrier and airport across all months"),
        (airport_month, "Same airport and month across all carriers"),
        (carrier_month, "Same carrier and month across all airports"),
        (month_all, "Same month across the national dataset"),
    ]
    context_frame, context_label = next(
        ((frame, label) for frame, label in context_candidates if not frame.empty),
        (pd.DataFrame(), "No historical context"),
    )

    context_summary = _summarize(context_frame, context_label)
    month_summary = _summarize(month_all, "All carriers and airports for this month")
    exact_summary = _summarize(exact, "Exact carrier-airport-month match")
    airport_summary = _summarize(airport_all, "Airport across all carriers and months")
    carrier_summary = _summarize(carrier_all, "Carrier across all airports and months")

    historical_rate = context_summary["delay_rate"] if context_summary else None
    risk_label = _risk_label(delay_probability, historical_rate)
    month_baseline = month_summary["delay_rate"] if month_summary else None
    historical_delta = (
        _safe_round(historical_rate - month_baseline)
        if historical_rate is not None and month_baseline is not None
        else None
    )

    return {
        "status": "success",
        "input": {
            "carrier": carrier,
            "airport": airport,
            "month": month,
        },
        "model": {
            "prediction": prediction,
            "prediction_label": prediction_label,
            "delay_heavy_probability": delay_probability,
            "feature_importances": feature_importances,
        },
        "risk_label": risk_label,
        "historical": {
            "context_used": context_summary,
            "exact": exact_summary,
            "month_baseline": month_summary,
            "airport_profile": airport_summary,
            "carrier_profile": carrier_summary,
            "reliability": _reliability(context_summary),
            "delay_rate_vs_month_baseline": historical_delta,
        },
        "matched_records": _records_for_display(exact if not exact.empty else context_frame),
        "availability": {
            "carrier_known": bool((df["carrier"] == carrier).any()),
            "airport_known": bool((df["airport"] == airport).any()),
            "exact_matches": int(len(exact)),
        },
    }
