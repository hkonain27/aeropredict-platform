import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import historical_weather  # noqa: E402


class FakeCsvResponse:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self.body.encode("utf-8")


class HistoricalWeatherServiceTestCase(unittest.TestCase):
    def setUp(self):
        historical_weather._HISTORICAL_WEATHER_CACHE.clear()

    def tearDown(self):
        historical_weather._HISTORICAL_WEATHER_CACHE.clear()

    def test_get_historical_weather_context_summarizes_iem_rows_and_caches(self):
        csv_body = "\n".join(
            [
                "station,valid,tmpf,sknt,gust,vsby,p01i,skyc1,skyl1,wxcodes,metar",
                "CLT,2024-07-01 00:00,80,12,,10,0,FEW,5000,,KCLT VFR",
                "CLT,2024-07-01 01:00,78,28,35,2,0.12,BKN,800,TSRA,KCLT TSRA",
                "CLT,2024-07-01 02:00,77,8,,7,0,OVC,600,,KCLT OVC006",
            ]
        )

        with patch("services.historical_weather.urlopen", return_value=FakeCsvResponse(csv_body)) as mock_urlopen:
            first = historical_weather.get_historical_weather_context("CLT", 7)
            second = historical_weather.get_historical_weather_context("CLT", 7)

        self.assertEqual(mock_urlopen.call_count, 1)
        self.assertTrue(first["available"])
        self.assertEqual(first["station"], "CLT")
        self.assertEqual(first["observations"], 3)
        self.assertEqual(first["low_visibility_rate"], 0.3333)
        self.assertEqual(first["low_ceiling_rate"], 0.6667)
        self.assertEqual(first["gusty_wind_rate"], 0.3333)
        self.assertTrue(second["cached"])

    def test_score_historical_weather_context_flags_disruptive_month(self):
        result = historical_weather.score_historical_weather_context(
            {
                "available": True,
                "observations": 700,
                "low_visibility_rate": 0.12,
                "low_ceiling_rate": 0.20,
                "gusty_wind_rate": 0.08,
                "precipitation_rate": 0.18,
                "thunderstorm_rate": 0.03,
                "winter_precip_rate": 0.0,
            }
        )

        self.assertEqual(result["level"], "Moderate")
        self.assertEqual(result["quality"], 1.0)
        self.assertGreater(result["score"], 0)
        self.assertTrue(result["drivers"])

    def test_score_historical_weather_context_handles_unavailable_source(self):
        result = historical_weather.score_historical_weather_context(
            {
                "available": False,
                "message": historical_weather.UNAVAILABLE_MESSAGE,
            }
        )

        self.assertEqual(result["level"], "Unknown")
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["quality"], 0)
        self.assertEqual(result["drivers"], [historical_weather.UNAVAILABLE_MESSAGE])


if __name__ == "__main__":
    unittest.main()
