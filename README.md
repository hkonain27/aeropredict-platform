# AeroPredict

### AI-Powered Flight Delay Prediction Platform

AeroPredict is a full-stack flight delay prediction system built with Flask, scikit-learn, React, and SQLite. The platform lets users submit carrier, airport, and month details, get a final delay-risk prediction, compare scenarios, review saved prediction history, and see live METAR weather context from AviationWeather.gov.

## What The App Does

- Predicts whether a carrier-airport-month scenario is likely to be delay-heavy
- Rejects carriers and airports that are not present in the historical dataset
- Returns a final user-facing risk label from a weighted score based on model probability, historical delay context, 2024 flight records, and live METAR weather risk
- Shows individual 2024 flight-record evidence from `data/raw/flight_data_2024.csv`
- Keeps the raw model-only prediction available in the response for explanation
- Saves the final displayed risk to SQLite for history and dashboard analytics
- Shows dashboard summaries from processed delay data and saved prediction activity
- Supports lightweight what-if analysis by comparing the current prediction with the previous one

## Project Structure

```text
aviation-intelligence-platform/
|-- backend/          # Flask API, model serving, SQLite persistence
|-- frontend/         # React dashboard and prediction UI
|-- scripts/          # Data preprocessing, model training, dashboard data build scripts
`-- data/
    |-- raw/          # Local raw source files, gitignored
    |-- processed/    # Processed datasets and trained model artifact
    |-- preprocessing.ipynb
    `-- train_model.ipynb
```

## Dataset

- Raw source file expected locally: `data/raw/airline_delay_cause.csv`
- Raw data is gitignored, so place the source CSV there before running preprocessing
- Active processed file in repo: `data/processed/delay_processed.csv`
- Dashboard snapshot: `backend/data/delay_dashboard.json`

The older `flights_processed.csv` notebook workflow is still present for reference, but the running Flask app uses the delay-cause pipeline listed above.

## Model

- Algorithm: Random Forest Classifier inside a scikit-learn pipeline
- Saved artifact loaded by the backend: `data/processed/delay_model.pkl`
- Current input features:
  - `carrier`
  - `airport`
  - `month`
  - `arr_flights`
- Target:
  - `is_delay_heavy`, based on whether the historical delay rate is at least 20%

## Risk Labels

The app separates the raw model result from the final displayed risk:

- Raw model risk: the direct scikit-learn model output from `carrier`, `airport`, `month`, and `arr_flights`
- Historical analysis risk: a rule-based label using raw model probability plus historical delay rate
- 2024 flight-record risk: evidence from individual 2024 flights matching the carrier, arrival airport, and month
- Final displayed risk: the label shown to users and saved in prediction history after applying data-quality weights to all evidence layers

`POST /predict` returns both:

- `prediction_label` and `final_risk_label`: final user-facing risk
- `final_risk_score`: weighted final score used to choose the label
- `final_risk_components`: each evidence layer's score, effective weight, and contribution
- `raw_model.prediction_label`: model-only risk
- `weather_risk`: live METAR-based risk contribution
- `flight_2024_context`: 2024 flight counts, delay rate, cancellation rate, average delay, and top delay cause

## Backend

The Flask backend lives in `backend/` and exposes:

- `GET /health`
  - health check endpoint
- `POST /predict`
  - validates input
  - rejects unknown carriers and airports
  - estimates arrival volume from historical data
  - loads the trained model
  - calls AviationWeather.gov for live METAR data
  - returns final risk, raw model risk, probability, historical analysis, 2024 flight-record evidence, model-factor context, and live weather risk
  - saves the final displayed risk to SQLite
- `GET /predictions`
  - returns the latest saved predictions
- `GET /api/dashboard-data`
  - returns dashboard aggregates computed from the processed dataset and saved prediction history
- `GET` or `POST /api/delay-risk`
  - returns a model and historical risk lookup without saving a record

Database:

- SQLite file: `backend/predictions.db`
- ORM: Flask-SQLAlchemy

## Live Weather

`POST /predict` calls the AviationWeather.gov METAR endpoint from Flask, not from React:

```text
https://aviationweather.gov/api/data/metar?ids=KCLT&format=json
```

The app converts three-letter U.S. airport codes like `CLT` to ICAO station IDs like `KCLT`, sets a custom user agent, caches each station for 60 seconds, and gracefully handles missing or unavailable weather data.

Live METAR weather affects the final displayed risk through the weighted score:

- The model remains the largest influence
- Weather can raise concern, but it does not automatically force a high-risk label
- Unavailable weather is omitted from the weighted score

## Weighted Final Risk

The final prediction is intentionally model-led so the app does not mark everything as high risk just because one supporting source looks concerning.

Base evidence weights:

```text
Model probability: 47%
Historical delay context: 25%
2024 individual flight records: 18%
Live METAR weather: 10%
```

The historical and 2024 layers can receive less effective weight when their evidence is limited. For example, exact 2024 carrier-airport-month evidence with hundreds of completed flights gets stronger weight than a broad fallback month-level match.

Final labels:

```text
0.00 - 0.39 = Lower Delay Risk
0.40 - 0.59 = Elevated Delay Risk
0.60 - 1.00 = High Delay Risk
```

## 2024 Flight-Record Evidence

The raw 2024 flight file is large, so the app does not read it during requests. Instead, `scripts/build_flight_2024_context.py` aggregates `data/raw/flight_data_2024.csv` into:

```text
backend/data/flight_2024_context.json
```

For each prediction, the backend looks for 2024 evidence in this order:

1. Exact carrier, arrival airport, and month
2. Same arrival airport and month across carriers
3. Same carrier and month across airports
4. Same month nationally

The UI shows the matched 2024 flight count, delay rate, cancellation rate, average arrival delay, and top delay cause. Strong 2024 evidence can raise the weighted final score:

- High 2024 evidence usually raises a lower model result to `Elevated Delay Risk`
- It reaches `High Delay Risk` only when the model or other evidence is also concerning
- Low or unavailable 2024 evidence does not increase the final label

## Frontend

The React frontend lives in `frontend/` and includes:

- Overview dashboard cards and charts
- Real-time prediction form
- Prediction history table
- Saved-records table with filtering
- Historical delay context
- 2024 flight-record evidence panel
- Live METAR weather panel
- Raw model-only result details
- Scenario comparison between the latest and previous prediction

## Setup

### Prerequisites

- Python 3.13+
- Node.js 18+

### Backend setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

### Frontend setup

```bash
cd frontend
npm install
```

## Running The App

### Start the backend

```bash
cd backend
python app.py
```

Backend runs at `http://localhost:5001`

### Start the frontend

```bash
cd frontend
npm run dev
```

Frontend runs at `http://localhost:5173`

## Data And Model Pipeline

Run these from the repository root after placing the raw CSV at `data/raw/airline_delay_cause.csv`:

```bash
python scripts/preprocess_delay.py
python scripts/build_delay_dashboard.py
python scripts/build_flight_2024_context.py
python backend/scripts/train_model.py
```

These commands generate or refresh:

- `data/processed/delay_processed.csv`
- `backend/data/delay_dashboard.json`
- `backend/data/flight_2024_context.json`
- `data/processed/delay_model.pkl`

## Testing

Backend tests:

```bash
python -m unittest discover -s backend/tests
```

Frontend checks:

```bash
cd frontend
npm run lint
npm run build
```

## Current Scope Notes

- The trained model itself uses historical delay-cause data plus estimated arrival volume
- 2024 flight records and live METAR weather are not trained model features, but both are used as weighted evidence in the final displayed prediction label
- The dashboard summarizes processed historical data and saved app predictions
- External weather calls are cached to respect AviationWeather.gov usage guidance

## Team Alignment

Suggested ownership based on the current implementation:

- Backend and API: Elijah
- Data science and prediction logic: Yennah
- Frontend and UX: Aleena
- Deployment: Maimouna
- Documentation and testing: Hafsa
