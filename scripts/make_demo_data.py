"""Create clearly synthetic fixtures for an offline end-to-end demonstration.

The demo measures plumbing, not aviation accuracy. Output is isolated in
var/demo and does not replace user archives or deployment model artifacts.
"""
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aeropredict.airports import resolve_airport
from aeropredict.features import nearest_hour_utc


def make_demo(output='var/demo'):
    destination = Path(output)
    destination.mkdir(parents=True, exist_ok=True)
    random = np.random.default_rng(42)
    flights, weather = [], []
    airport = resolve_airport('RDU')
    for day in pd.date_range('2025-01-01', periods=120, freq='D'):
        for number, hour in [('101', 9), ('102', 15)]:
            scheduled = (day + pd.Timedelta(hours=hour, minutes=40)).tz_localize(airport.timezone).tz_convert('UTC')
            wind = float(random.uniform(0, 30))
            rain = float(random.choice([0, 0, 0, 0.1, 0.3]))
            delay = float(round(0.5*wind+50*rain+random.normal(0, 5)-7, 1))
            flights.append({'carrier': 'MX', 'flight_number': number, 'origin': 'RDU', 'destination': 'MCO',
                            'scheduled_dep_utc': scheduled.isoformat(),
                            'actual_arrival_utc': (scheduled+pd.Timedelta(minutes=120+delay)).isoformat(),
                            'arr_delay_min': delay})
            weather.append({'airport_icao': airport.icao, 'timestamp_utc': nearest_hour_utc(scheduled).isoformat(),
                            'temperature_f': float(random.uniform(40, 85)), 'wind_speed_mph': wind,
                            'visibility_miles': 7 if rain else 10, 'precipitation_inches': rain})
    pd.DataFrame(flights).to_csv(destination/'flights.csv', index=False)
    pd.DataFrame(weather).to_csv(destination/'weather.csv', index=False)
    live = {'best_flights': [{'flights': [{'flight_number': 'MX 101', 'airline': 'Breeze Airways',
            'departure_airport': {'id': 'RDU', 'time': '2025-05-02 09:40'},
            'arrival_airport': {'id': 'MCO', 'time': '2025-05-02 11:40'}}]}], 'other_flights': []}
    forecast = {'location': {'lat': airport.latitude, 'lon': airport.longitude},
                'forecast': {'forecastday': [{'hour': [{'time_epoch': int(pd.Timestamp('2025-05-02T14:00:00Z').timestamp()),
                            'temp_f': 72, 'wind_mph': 16, 'vis_miles': 8, 'precip_in': 0.1}]}]}}
    for name, payload in [('serpapi.json', live), ('weatherapi.json', forecast)]:
        (destination/name).write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(f'Created {len(flights)} SYNTHETIC flights and weather rows in {destination}. Not real training data.')


if __name__ == '__main__':
    make_demo()
