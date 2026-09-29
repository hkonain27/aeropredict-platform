"""Regression checks for timezone matching and leakage, without network calls."""
import pandas as pd
import pytest

from aeropredict.airports import resolve_airport
from aeropredict.data_prep import normalize_flights, normalize_weather, create_prediction_pipeline
from aeropredict.features import RollingHistory, build_history_features, nearest_hour_utc


def raw_flights():
    return pd.DataFrame({'FL_DATE': [20250101, 20250102], 'OP_UNIQUE_CARRIER': ['MX','MX'],
        'OP_CARRIER_FL_NUM': [101,101], 'ORIGIN': ['RDU','RDU'], 'DEST': ['MCO','MCO'],
        'CRS_DEP_TIME': [940,940], 'CRS_ELAPSED_TIME': [120,120], 'ARR_DELAY': [20,-5]})


def test_bts_local_time_integer_dates_and_midnight_rollover():
    raw = raw_flights()
    raw.loc[1, 'CRS_DEP_TIME'] = 2400
    frame, _ = normalize_flights(raw)
    assert frame.scheduled_dep_utc.iloc[0] == pd.Timestamp('2025-01-01T14:40:00Z')
    assert frame.scheduled_dep_utc.iloc[1] == pd.Timestamp('2025-01-03T05:00:00Z')
    assert frame.dep_hour.tolist() == [9,0]
    assert nearest_hour_utc('2025-01-01T23:30Z') == pd.Timestamp('2025-01-02T00:00Z')
    assert resolve_airport('HNL').icao == 'PHNL'


@pytest.mark.parametrize('day,hour', [('2025-03-09',230),('2025-11-02',130)])
def test_dst_ambiguity_and_gaps_are_rejected(day,hour):
    raw = raw_flights().iloc[[0]].copy()
    raw['FL_DATE'] = day
    raw['CRS_DEP_TIME'] = hour
    with pytest.raises(ValueError, match='invalid flight'):
        normalize_flights(raw)


def test_minimal_input_requires_explicit_outcome_timing_assumption():
    raw = raw_flights().drop(columns='CRS_ELAPSED_TIME')
    with pytest.raises(ValueError, match='Outcome availability'):
        normalize_flights(raw)
    frame, audit = normalize_flights(raw, assumed_outcome_lag_hours=48)
    assert 'ASSUMED' in audit['outcome_availability_method']
    assert (frame.outcome_available_utc-frame.scheduled_dep_utc == pd.Timedelta(hours=48)).all()


def test_meteostat_conversion_missing_visibility_and_duplicate_conflict():
    raw = pd.DataFrame({'time':['2025-01-01T15:00:00Z'], 'airport_icao':['KRDU'],
                        'temp':[20], 'wspd':[16.09344], 'prcp':[25.4]})
    weather, audit = normalize_weather(raw, units='meteostat')
    assert weather.temperature_f.iloc[0] == 68
    assert weather.wind_speed_mph.iloc[0] == pytest.approx(10)
    assert weather.precipitation_inches.iloc[0] == pytest.approx(1)
    assert audit['missing_weather_columns'] == ['visibility_miles']
    duplicate = pd.concat([raw,raw], ignore_index=True)
    duplicate.loc[1,'temp'] = 30
    with pytest.raises(ValueError, match='Conflicting weather'):
        normalize_weather(duplicate, units='meteostat')


def test_pending_outcomes_and_airline_collisions_do_not_leak():
    history = pd.DataFrame({
        'flight_key':['AA|123|RDU|MCO','AA|123|RDU|MCO','MX|123|RDU|MCO'],
        'scheduled_dep_utc':pd.to_datetime(['2025-01-01T10:00Z','2025-01-02T10:00Z','2025-01-02T11:00Z']),
        'outcome_available_utc':pd.to_datetime(['2025-01-01T14:00Z','2025-01-04T14:00Z','2025-01-02T14:00Z']),
        'arr_delay_min':[10,900,100]})
    lookup = RollingHistory(history)
    prior = lookup.lookup('AA|123|RDU|MCO','2025-01-03T09:00Z','2025-01-03T10:00Z')
    assert prior['hist_flight_num_delay_avg'] == 10
    assert prior['hist_flight_num_delay_count'] == 1
    queries = history.copy()
    queries['prediction_as_of_utc'] = queries.scheduled_dep_utc
    computed = build_history_features(queries)
    for _, row in computed.iterrows():
        expected = lookup.lookup(row.flight_key,row.prediction_as_of_utc,row.scheduled_dep_utc)
        assert row.hist_flight_num_delay_avg == expected['hist_flight_num_delay_avg']


def test_inner_join_does_not_discard_history_and_reports_coverage(tmp_path):
    flights_path, weather_path = tmp_path/'flights.csv', tmp_path/'weather.csv'
    raw_flights().to_csv(flights_path,index=False)
    pd.DataFrame({'timestamp_utc':['2025-01-02T15:00:00Z'],'airport_icao':['KRDU'],
                  'temperature_f':[65],'wind_speed_mph':[10],'visibility_miles':[10],
                  'precipitation_inches':[0]}).to_csv(weather_path,index=False)
    matrix, audit = create_prediction_pipeline(flights_path,weather_path,output_path=tmp_path/'training.csv')
    assert len(matrix) == 1
    assert matrix.hist_flight_num_delay_avg.iloc[0] == 20
    assert audit['flights_without_weather'] == 1
    assert len(pd.read_csv(tmp_path/'training.history.csv')) == 2


def test_git_lfs_pointer_rejected(tmp_path):
    from aeropredict.data_prep import load_csvs
    pointer = tmp_path/'flights.csv'
    pointer.write_text('version https://git-lfs.github.com/spec/v1\noid sha256:123')
    with pytest.raises(ValueError, match='Git LFS pointer'):
        load_csvs([pointer])
