"""Small serving layer; data preparation and training run as offline jobs."""
import hmac
import logging
import os
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS
from aeropredict.providers import ProviderError, search_route
from aeropredict.predict_live import load_artifact, predict_payload

LOGGER = logging.getLogger(__name__)


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        MAX_CONTENT_LENGTH=16_384,
        MODEL_ARTIFACT_PATH=os.environ.get('MODEL_ARTIFACT_PATH', 'artifacts/model.joblib'),
        API_TOKEN=os.environ.get('AEROPREDICT_API_TOKEN', ''),
    )
    if test_config:
        app.config.update(test_config)
    origins = [value.strip() for value in os.environ.get('ALLOWED_ORIGINS', 'http://localhost:5173').split(',') if value.strip()]
    CORS(app, resources={r'/api/*': {'origins': origins}})

    @app.get('/health')
    def health():
        return jsonify(status='ok')

    @app.get('/api/model-status')
    def model_status():
        return jsonify(available=Path(app.config['MODEL_ARTIFACT_PATH']).is_file(),
                       target='Signed arrival delay in minutes')

    @app.post('/api/predict-live')
    def predict():
        token = app.config['API_TOKEN']
        supplied = request.headers.get('Authorization', '').removeprefix('Bearer ')
        if token and not hmac.compare_digest(supplied, token):
            return jsonify(error='A valid bearer token is required.'), 401
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error='Provide a JSON object with origin, destination and date.'), 400
        if not Path(app.config['MODEL_ARTIFACT_PATH']).is_file():
            return jsonify(error='No trained delay-minute model is installed. Run data_prep.py and train_model.py first.'), 503
        try:
            for field in ('origin', 'destination', 'date'):
                if not isinstance(payload.get(field), str) or not payload[field].strip():
                    raise ValueError(f'{field} is required and must be text.')
            # Validate the artifact before any quota can be spent on a search.
            load_artifact(app.config['MODEL_ARTIFACT_PATH'])
            live = search_route(payload['origin'].strip().upper(), payload['destination'].strip().upper(), payload['date'])
            results = predict_payload(live, app.config['MODEL_ARTIFACT_PATH'])
            return jsonify(predictions=results, target='Signed arrival delay in minutes',
                           message='Model estimates are not airline-confirmed delay announcements.')
        except ProviderError as exc:
            # Never log request URLs: providers put API keys in query parameters.
            LOGGER.warning('Live provider request unavailable (%s)', type(exc).__name__)
            return jsonify(error=str(exc)), 503
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        except Exception:
            LOGGER.error('Prediction failed unexpectedly; inspect local model and provider configuration.')
            return jsonify(error='Prediction could not be completed.'), 500

    return app


app = create_app()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
    app.run(host='127.0.0.1', port=5001, debug=False)
