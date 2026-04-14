# AeroPredict

AeroPredict is an aviation intelligence platform for predicting flight delay risk and exploring saved delay patterns. Built with Flask, scikit-learn, React, and SQLite, it lets users submit flight details, generate a real-time prediction, compare scenarios, and review historical prediction activity in a dashboard.

## What The App Does

- Predicts whether a flight is likely to be delayed by 15+ minutes
- Returns a delay probability and a simple model-factor view
- Saves predictions to SQLite for history and dashboard analytics
- Shows dashboard summaries based on saved prediction activity
- Supports lightweight what-if analysis by comparing the current prediction with the previous one

## Project Structure

```text
aviation-intelligence-platform/
├── backend/          # Flask API, model serving, SQLite persistence
├── frontend/         # React dashboard and prediction UI
└── data/
    ├── raw/          # Kaggle source dataset
    ├── processed/    # Cleaned dataset + trained model artifact
    ├── preprocessing.ipynb
    └── train_model.ipynb
```

## Dataset

- Source file used locally: `data/raw/flight_data_2024.csv`
- Raw-data note: `data/raw/*.csv` is gitignored, so you should place the 2024 source CSV there locally before running preprocessing
- Processed file in repo: `data/processed/flights_processed.csv`

## Model

- Algorithm: Random Forest Classifier inside a scikit-learn pipeline
- Saved artifact: `data/processed/model.pkl`
- Current input features:
  - `airline`
  - `origin`
  - `destination`
  - `dep_hour`
  - `day_of_week`
  - `distance`
- Target:
  - `delayed` = whether `dep_delay >= 15`
- Current local training flow:
  - `backend/scripts/train_model.py` trains a Random Forest from `data/processed/flights_processed.csv`
  - the script defaults to a stratified sample so retraining stays practical on a local machine

## Backend

The Flask backend lives in `backend/` and exposes:

- `GET /health`
  - health check endpoint
- `POST /predict`
  - validates input
  - loads the trained model
  - returns a prediction, probability, and grouped feature importance
  - saves the result to SQLite
- `GET /predictions`
  - returns the latest saved predictions
- `GET /api/dashboard-data`
  - returns dashboard aggregates computed from saved prediction history

Database:

- SQLite file: `backend/predictions.db`
- ORM: Flask-SQLAlchemy

## Frontend

The React frontend lives in `frontend/` and includes:

- Overview dashboard cards and charts
- Real-time prediction form
- Prediction history table
- Saved-records table with filtering
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

## Example Prediction Request

```json
{
  "airline": "UA",
  "origin": "JFK",
  "destination": "LAX",
  "dep_hour": 17,
  "day_of_week": 5,
  "distance": 2475
}
```

## Example Prediction Response

```json
{
  "status": "success",
  "input": {
    "airline": "UA",
    "origin": "JFK",
    "destination": "LAX",
    "dep_hour": 17,
    "day_of_week": 5,
    "distance": 2475
  },
  "prediction": 0,
  "prediction_label": "On Time Likely",
  "delay_probability": 0.2131,
  "feature_importances": [
    {
      "feature": "distance",
      "importance": 24.0
    }
  ]
}
```

## Testing

Backend route tests are located in `backend/tests/test_api.py`.

Run them with:

```bash
python -m unittest discover -s backend/tests
```

## Reproducing The Model

1. Run `data/preprocessing.ipynb`
2. Generate `data/processed/flights_processed.csv`
3. Run `backend/scripts/train_model.py`
4. Generate `data/processed/model.pkl`

Example:

```bash
cd backend
../.venv/bin/python scripts/train_model.py --sample-rows 50000
```

## Current Scope Notes

- The live app is driven by flight features listed above
- The dashboard currently summarizes saved app predictions, not the full raw historical dataset directly
- Weather-specific features are not part of the current deployed prediction pipeline
- Weather integration can be framed as a future enhancement unless the team decides to expand scope

## Team Alignment

Suggested ownership based on the current implementation:

- Backend and API: Elijah
- Data science and prediction logic: Yennah
- Frontend and UX: Aleena
- Deployment: Maimouna
- Documentation and testing: Hafsa
