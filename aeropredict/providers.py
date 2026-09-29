"""Small, quota-limited adapters for SerpApi schedules and WeatherAPI weather.

Every attempted HTTP request reserves quota in a SQLite transaction before it is
sent. All worker processes must share this database: copying it per container
would create independent budgets. Defaults are zero, so installing or starting
the application cannot trigger a paid API request.
"""

from __future__ import annotations

import hashlib
from contextlib import contextmanager
import json
import logging
import os
from pathlib import Path
import re
import sqlite3
import time
from typing import Any, Callable

import pandas as pd
import requests

from .airports import US_DOMESTIC_COUNTRIES, resolve_airport

LOGGER = logging.getLogger(__name__)
_ENDPOINTS = {
    "serpapi": "https://serpapi.com/search.json",
    "weatherapi": "https://api.weatherapi.com/v1/forecast.json",
}


class ProviderError(RuntimeError):
    """A provider is unavailable; its raw response is deliberately not exposed."""


class ProviderConfigurationError(ProviderError):
    """Credentials or a local spending control are missing/invalid."""


class RequestBudgetExceeded(ProviderError):
    """An outbound request was refused before any network access."""


def _nonnegative_int(value: Any, name: str) -> int:
    try:
        number = int(str(value))
    except (TypeError, ValueError):
        raise ProviderConfigurationError(f"{name} must be a nonnegative integer.") from None
    if number < 0:
        raise ProviderConfigurationError(f"{name} must be a nonnegative integer.")
    return number


class BudgetedClient:
    """Cache JSON and enforce rolling 24-hour and 31-day request limits.

    Failed attempts count too. There are no implicit retries, redirect follows,
    pagination, subscription changes, or calls to other provider endpoints.
    A short persistent cooldown prevents failures from causing a request storm.
    Transport and clock injection allow the safeguards to be tested offline.
    """

    def __init__(
        self,
        provider: str,
        *,
        api_key: str | None = None,
        state_path: str | Path | None = None,
        daily_limit: int | None = None,
        month_limit: int | None = None,
        transport: Callable[..., Any] | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if provider not in _ENDPOINTS:
            raise ProviderConfigurationError("Unsupported API provider.")
        self.provider = provider
        prefix = provider.upper()
        self.api_key = api_key if api_key is not None else os.getenv(f"{prefix}_API_KEY", "")
        self.daily_limit = _nonnegative_int(
            daily_limit if daily_limit is not None else os.getenv(f"{prefix}_DAILY_LIMIT", "0"),
            f"{prefix}_DAILY_LIMIT",
        )
        self.month_limit = _nonnegative_int(
            month_limit if month_limit is not None else os.getenv(f"{prefix}_31DAY_LIMIT", "0"),
            f"{prefix}_31DAY_LIMIT",
        )
        self.path = Path(state_path or os.getenv("API_STATE_PATH", "var/api_state.sqlite3"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.transport = transport or requests.get
        self.clock = clock
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS request_attempts (
                    provider TEXT NOT NULL, attempted_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS ix_request_attempts
                    ON request_attempts(provider, attempted_at);
                CREATE TABLE IF NOT EXISTS response_cache (
                    cache_key TEXT PRIMARY KEY, expires_at REAL NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS provider_cooldown (
                    provider TEXT PRIMARY KEY, until_at REAL NOT NULL
                );
                """
            )

    @contextmanager
    def _connect(self):
        """Commit or roll back and close: sqlite's own context does not close."""
        connection = sqlite3.connect(str(self.path), timeout=10)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _clean_response(self, value: Any) -> Any:
        """Do not persist credentials even if a provider echoes query parameters."""
        if isinstance(value, dict):
            return {
                key: self._clean_response(item)
                for key, item in value.items()
                if key.lower() not in {"api_key", "apikey", "key", "authorization"}
            }
        if isinstance(value, list):
            return [self._clean_response(item) for item in value]
        if isinstance(value, str) and self.api_key:
            return value.replace(self.api_key, "[redacted]")
        return value

    def _cooldown(self, seconds: int) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO provider_cooldown(provider, until_at) VALUES (?, ?) "
                "ON CONFLICT(provider) DO UPDATE SET until_at=MAX(until_at,excluded.until_at)",
                (self.provider, self.clock() + seconds),
            )

    def get_json(self, params: dict[str, Any], *, cache_ttl: int = 900) -> dict[str, Any]:
        """Return fresh cache data or perform exactly one pre-budgeted request."""
        if any(key.lower() in {"key", "api_key", "apikey", "authorization"} for key in params):
            raise ProviderConfigurationError("Pass credentials through the client configuration.")
        cache_ttl = _nonnegative_int(cache_ttl, "cache_ttl")
        canonical = json.dumps([self.provider, params], sort_keys=True, separators=(",", ":"))
        cache_key = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        now = self.clock()
        # BEGIN IMMEDIATE serializes reservations across processes. Quota must be
        # committed before the HTTP request; a crash then errs on the safe side.
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cached = connection.execute(
                "SELECT payload FROM response_cache WHERE cache_key=? AND expires_at>?",
                (cache_key, now),
            ).fetchone()
            if cached:
                return json.loads(cached[0])
            if self.daily_limit == 0 or self.month_limit == 0:
                raise RequestBudgetExceeded(
                    f"{self.provider} requests are disabled. Set both explicit request limits after checking your plan."
                )
            if not self.api_key.strip():
                raise ProviderConfigurationError(f"Set {self.provider.upper()}_API_KEY to enable this provider.")
            cooldown = connection.execute(
                "SELECT until_at FROM provider_cooldown WHERE provider=?", (self.provider,)
            ).fetchone()
            if cooldown and cooldown[0] > now:
                raise ProviderError(f"{self.provider} is temporarily paused after an API failure; try later.")
            day_used, month_used = connection.execute(
                "SELECT COALESCE(SUM(attempted_at>?),0), COUNT(*) FROM request_attempts "
                "WHERE provider=? AND attempted_at>?",
                (now - 86400, self.provider, now - 31 * 86400),
            ).fetchone()
            if day_used >= self.daily_limit or month_used >= self.month_limit:
                raise RequestBudgetExceeded(f"{self.provider} local request budget exhausted; try after the rolling window resets.")
            connection.execute(
                "INSERT INTO request_attempts(provider,attempted_at) VALUES (?,?)", (self.provider, now)
            )
            connection.execute("DELETE FROM request_attempts WHERE attempted_at<=?", (now - 31 * 86400,))
            connection.execute("DELETE FROM response_cache WHERE expires_at<=?", (now,))

        request_params = dict(params)
        request_params["api_key" if self.provider == "serpapi" else "key"] = self.api_key
        try:
            response = self.transport(
                _ENDPOINTS[self.provider], params=request_params,
                timeout=(5, 30), allow_redirects=False,
            )
        except requests.RequestException:
            self._cooldown(60)
            LOGGER.warning("%s request failed: network or timeout", self.provider)
            raise ProviderError(f"{self.provider} could not be reached. No automatic retry was made.") from None
        status = response.status_code
        if status != 200:
            self._cooldown(3600 if status in {401, 403, 429} else 60)
            LOGGER.warning("%s request failed: HTTP %s", self.provider, status)
            raise ProviderError(f"{self.provider} returned HTTP {status}. Check its dashboard; no automatic retry was made.")
        try:
            payload = response.json()
        except (ValueError, TypeError):
            self._cooldown(60)
            raise ProviderError(f"{self.provider} returned invalid JSON.") from None
        if not isinstance(payload, dict) or payload.get("error"):
            self._cooldown(60)
            raise ProviderError(f"{self.provider} returned an API error. Check its dashboard for details.")
        payload = self._clean_response(payload)
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO response_cache(cache_key, expires_at, payload) VALUES (?,?,?) "
                "ON CONFLICT(cache_key) DO UPDATE SET expires_at=excluded.expires_at,payload=excluded.payload",
                (cache_key, self.clock() + cache_ttl, json.dumps(payload, allow_nan=False)),
            )
        return payload


def search_route(
    origin: str,
    destination: str,
    date: str,
    *,
    client: BudgetedClient | None = None,
    now: Any = None,
) -> dict[str, Any]:
    """Search one US domestic route/date; this is a schedule, not actual outcomes."""
    origin_airport, destination_airport = resolve_airport(origin), resolve_airport(destination)
    if any(a.country not in US_DOMESTIC_COUNTRIES for a in (origin_airport, destination_airport)):
        raise ValueError("Only US domestic routes are supported by this model.")
    if origin_airport.iata == destination_airport.iata:
        raise ValueError("Origin and destination must differ.")
    if not isinstance(date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise ValueError("Flight date must use YYYY-MM-DD.")
    try:
        departure_date = pd.Timestamp(date).date()
    except (ValueError, OverflowError):
        raise ValueError("Flight date is invalid.") from None
    reference = pd.Timestamp(now) if now is not None else pd.Timestamp.now(tz="UTC")
    if reference.tzinfo is None:
        raise ValueError("The search reference time must include a timezone.")
    local_today = reference.tz_convert(origin_airport.timezone).date()
    if departure_date < local_today:
        raise ValueError("Google Flights searches require a current or future departure date.")
    horizon = _nonnegative_int(os.getenv('WEATHERAPI_FORECAST_DAYS', '3'), 'WEATHERAPI_FORECAST_DAYS')
    if not 1 <= horizon <= 14:
        raise ProviderConfigurationError('WEATHERAPI_FORECAST_DAYS must be from 1 to 14.')
    if (departure_date-local_today).days >= horizon:
        raise ValueError('Departure date is outside the configured weather forecast window; no search was sent.')
    provider = client or BudgetedClient("serpapi")
    return provider.get_json(
        {
            "engine": "google_flights", "departure_id": origin_airport.iata,
            "arrival_id": destination_airport.iata, "outbound_date": date,
            "type": 2, "stops": 1, "adults": 1, "currency": "USD", "hl": "en", "gl": "us",
        },
        cache_ttl=3600,
    )
