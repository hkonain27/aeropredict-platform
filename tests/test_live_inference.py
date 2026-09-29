"""Provider contracts, cost controls, and shared live feature transformations."""
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

import pandas as pd
import pytest
import requests

from aeropredict.airports import resolve_airport
from aeropredict.features import FEATURE_COLUMNS
from aeropredict.predict_live import parse_serpapi_flights, predict_payload, weather_for_departure
from aeropredict.providers import BudgetedClient, ProviderError, RequestBudgetExceeded, search_route


def flight_payload():
    return {'best_flights':[{'flights':[{'flight_number':'MX 101','airline':'Breeze Airways',
        'departure_airport':{'id':'RDU','time':'2025-01-02 09:40'},
        'arrival_airport':{'id':'MCO','time':'2025-01-02 11:40'}}]}]}


def weather_payload():
    airport = resolve_airport('RDU')
    return {'location':{'lat':airport.latitude,'lon':airport.longitude},
            'forecast':{'forecastday':[{'hour':[{
                'time_epoch':pd.Timestamp('2025-01-02T15:00Z').timestamp(),
                'temp_f':65,'wind_mph':10,'vis_miles':9,'precip_in':0.1}]}]}}


def test_parse_deduplicates_provider_legs_and_uses_airport_timezone():
    payload = flight_payload()
    payload['other_flights'] = payload['best_flights']
    flights = parse_serpapi_flights(payload)
    assert len(flights) == 1
    assert flights[0]['carrier'] == 'MX'
    assert flights[0]['flight_number'] == '101'
    assert flights[0]['scheduled_dep_utc'] == pd.Timestamp('2025-01-02T14:40Z')


def test_forecast_exact_hour_missing_and_wrong_airport():
    payload = weather_payload()
    weather = weather_for_departure('RDU','2025-01-02T14:40Z',payload=payload,as_of='2025-01-01T14:40Z')
    assert weather['temperature_f'] == 65
    assert weather['weather_hour_utc'] == '2025-01-02T15:00:00+00:00'
    with pytest.raises(ProviderError, match='No hourly weather'):
        weather_for_departure('RDU','2025-01-02T17:00Z',payload=payload,as_of='2025-01-01T14:40Z')
    payload['location'] = {'lat':34.05,'lon':-118.25}
    with pytest.raises(ProviderError, match='too far'):
        weather_for_departure('RDU','2025-01-02T14:40Z',payload=payload,as_of='2025-01-01T14:40Z')


def test_inference_uses_fitted_feature_order_signed_minutes_and_training_horizon(monkeypatch):
    pipeline = Mock()
    pipeline.predict.return_value = [-7.25]
    history = pd.DataFrame({'flight_key':['MX|101|RDU|MCO'],
        'scheduled_dep_utc':['2024-12-31T14:40Z'], 'outcome_available_utc':['2024-12-31T17:00Z'],
        'arr_delay_min':[15]})
    artifact = {'schema_version':1,'pipeline':pipeline,'feature_columns':FEATURE_COLUMNS,'history':history,
        'training_cutoff_utc':'2025-01-01T00:00Z','forecast_horizon_hours':24,
        'metrics':{'model':{'mae_minutes':12},'metrics_apply_to_saved_model':True}}
    monkeypatch.setattr('aeropredict.predict_live.load_artifact',lambda path:artifact)
    results = predict_payload(flight_payload(),'unused',weather_payload(),as_of='2025-01-01T14:40Z')
    assert results[0]['status'] == 'ok'
    assert 'minutes early' in results[0]['message']
    assert results[0]['evaluation_mae_minutes'] == 12
    frame = pipeline.predict.call_args.args[0]
    assert list(frame.columns) == FEATURE_COLUMNS
    assert frame.dep_hour.iloc[0] == 9
    assert frame.hist_flight_num_delay_avg.iloc[0] == 15
    assert results[0]['history_sample_count'] == 1
    missing = weather_payload()
    missing['forecast']['forecastday'][0]['hour'] = []
    unavailable = predict_payload(flight_payload(),'unused',missing,as_of='2025-01-01T14:40Z')
    assert unavailable[0]['status'] == 'unavailable'
    with pytest.raises(ValueError,match='training cutoff'):
        predict_payload(flight_payload(),'unused',weather_payload(),as_of='2024-12-01T00:00Z')


def test_zero_default_budget_and_invalid_routes_never_reach_network(tmp_path):
    network = Mock()
    client = BudgetedClient('serpapi',state_path=tmp_path/'cache.db',api_key='secret',daily_limit=0,month_limit=0,transport=network)
    with pytest.raises(RequestBudgetExceeded):
        client.get_json({'engine':'google_flights'})
    with pytest.raises(ValueError,match='US domestic'):
        search_route('RDU','LHR','2025-01-02',client=client,now='2025-01-01T00:00Z')
    with pytest.raises(ValueError,match='forecast window'):
        search_route('RDU','MCO','2025-02-02',client=client,now='2025-01-01T00:00Z')
    network.assert_not_called()


def test_durable_cache_sanitizes_secrets_and_avoids_second_call(tmp_path):
    response = Mock(status_code=200)
    response.json.return_value = {'best_flights':[], 'api_key':'secret', 'link':'https://example.com/?key=secret'}
    network = Mock(return_value=response)
    arguments = dict(api_key='secret',state_path=tmp_path/'cache.db',daily_limit=1,month_limit=1,transport=network)
    first = BudgetedClient('serpapi',**arguments).get_json({'engine':'google_flights'})
    second = BudgetedClient('serpapi',**arguments).get_json({'engine':'google_flights'})
    assert first == second
    assert 'api_key' not in first
    assert 'secret' not in first['link']
    assert network.call_count == 1
    assert network.call_args.kwargs['allow_redirects'] is False
    with pytest.raises(RequestBudgetExceeded):
        BudgetedClient('serpapi',**arguments).get_json({'engine':'google_flights','q':'new'})


def test_failed_call_counts_and_31day_budget_survives_new_day(tmp_path):
    now = [2_000_000.0]
    network = Mock(side_effect=requests.Timeout('URL with secret key must not surface'))
    client = BudgetedClient('weatherapi',api_key='secret',state_path=tmp_path/'cache.db',
        daily_limit=1,month_limit=1,transport=network,clock=lambda:now[0])
    with pytest.raises(ProviderError,match='No automatic retry') as error:
        client.get_json({'q':'35,-78'})
    assert 'secret' not in str(error.value)
    now[0] += 2*86400
    with pytest.raises(RequestBudgetExceeded):
        client.get_json({'q':'35,-78'})
    assert network.call_count == 1


def test_atomic_budget_caps_concurrent_requests(tmp_path):
    response = Mock(status_code=200)
    response.json.return_value = {'forecast':{}}
    network = Mock(return_value=response)
    client = BudgetedClient('weatherapi',api_key='secret',state_path=tmp_path/'cache.db',
                            daily_limit=2,month_limit=2,transport=network)
    def attempt(index):
        try:
            client.get_json({'q':str(index)})
            return True
        except RequestBudgetExceeded:
            return False
    with ThreadPoolExecutor(max_workers=4) as pool:
        accepted = list(pool.map(attempt,range(8)))
    assert sum(accepted) == 2
    assert network.call_count == 2
