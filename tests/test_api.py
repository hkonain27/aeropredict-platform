"""The HTTP adapter fails before spending quota when input/model/auth is invalid."""
from unittest.mock import Mock
from backend.app import create_app


def test_health_and_missing_model_do_not_call_providers(tmp_path,monkeypatch):
    search = Mock()
    monkeypatch.setattr('backend.app.search_route',search)
    app = create_app({'TESTING':True,'MODEL_ARTIFACT_PATH':str(tmp_path/'absent.joblib')})
    client = app.test_client()
    assert client.get('/health').get_json() == {'status':'ok'}
    assert client.get('/api/model-status').get_json()['available'] is False
    assert client.post('/api/predict-live',json={'origin':'RDU','destination':'MCO','date':'2025-05-02'}).status_code == 503
    assert client.post('/api/predict-live',json=[]).status_code == 400
    search.assert_not_called()


def test_token_and_corrupt_artifact_checked_before_search(tmp_path,monkeypatch):
    artifact = tmp_path/'bad.joblib'
    artifact.write_text('invalid')
    search = Mock()
    monkeypatch.setattr('backend.app.search_route',search)
    app = create_app({'TESTING':True,'MODEL_ARTIFACT_PATH':str(artifact),'API_TOKEN':'server-access'})
    client = app.test_client()
    payload = {'origin':'RDU','destination':'MCO','date':'2025-05-02'}
    assert client.post('/api/predict-live',json=payload).status_code == 401
    assert client.post('/api/predict-live',json=payload,headers={'Authorization':'Bearer server-access'}).status_code == 400
    search.assert_not_called()
