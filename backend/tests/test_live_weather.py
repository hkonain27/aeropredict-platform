import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services import live_weather  # noqa: E402


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class LiveWeatherServiceTestCase(unittest.TestCase):
    def setUp(self):
        live_weather._METAR_CACHE.clear()

    def tearDown(self):
        live_weather._METAR_CACHE.clear()

    def test_iata_to_icao_adds_us_prefix(self):
        self.assertEqual(live_weather.iata_to_icao("clt"), "KCLT")
        self.assertEqual(live_weather.iata_to_icao("KJFK"), "KJFK")

    def test_score_weather_risk_flags_high_risk_weather(self):
        result = live_weather.score_weather_risk(
            {
                "available": True,
                "flight_category": "IFR",
                "visibility_miles": 2,
                "wind_speed_kt": 26,
                "wind_gust_kt": 35,
                "raw_text": "KCLT 141852Z TS",
            }
        )

        self.assertEqual(result["level"], "High")
        self.assertGreaterEqual(result["score"], 5)
        self.assertTrue(any("Thunderstorms" in driver for driver in result["drivers"]))

    def test_score_weather_risk_handles_unavailable_weather(self):
        result = live_weather.score_weather_risk(
            {
                "available": False,
                "message": "No recent METAR available.",
            }
        )

        self.assertEqual(result["level"], "Unknown")
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["drivers"], ["No recent METAR available."])

    def test_get_live_metar_caches_by_station_for_sixty_seconds(self):
        payload = [
            {
                "rawOb": "KCLT 141852Z 21012KT 10SM FEW040 20/12 A2992",
                "fltCat": "VFR",
                "temp": 20,
                "dewp": 12,
                "wdir": 210,
                "wspd": 12,
                "wgst": None,
                "visib": "10+",
                "altim": 29.92,
                "reportTime": "2026-04-14T18:52:00Z",
            }
        ]

        with patch("services.live_weather.urlopen", return_value=FakeResponse(payload)) as mock_urlopen:
            first = live_weather.get_live_metar("CLT")
            second = live_weather.get_live_metar("CLT")

        self.assertEqual(mock_urlopen.call_count, 1)
        self.assertTrue(first["available"])
        self.assertFalse(first["cached"])
        self.assertTrue(second["cached"])
        self.assertEqual(second["station"], "KCLT")

    def test_get_live_metar_handles_no_content_response(self):
        with patch("services.live_weather.urlopen", return_value=FakeResponse(None, status=204)):
            result = live_weather.get_live_metar("CLT")

        self.assertFalse(result["available"])
        self.assertEqual(result["station"], "KCLT")
        self.assertEqual(result["message"], "No recent METAR available.")


if __name__ == "__main__":
    unittest.main()
