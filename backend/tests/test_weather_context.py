import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.weather_context import build_weather_context  # noqa: E402


class WeatherContextServiceTestCase(unittest.TestCase):
    def test_weather_context_returns_expected_shape(self):
        context = build_weather_context("SFO", "JFK", 7, 2586)

        self.assertIn("headline", context)
        self.assertIn("summary", context)
        self.assertIn("drivers", context)
        self.assertIn("disclaimer", context)
        self.assertGreaterEqual(len(context["drivers"]), 1)

    def test_weather_context_marks_storm_prone_late_day_route(self):
        context = build_weather_context("ATL", "MCO", 18, 404)
        labels = {driver["label"] for driver in context["drivers"]}

        self.assertIn("Late-day thunderstorm exposure", labels)


if __name__ == "__main__":
    unittest.main()
