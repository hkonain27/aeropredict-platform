# Deployment and operating plan

Run training separately from the request-serving process. Start with one CPU application instance and a persistent local volume; increase capacity only after measuring real latency and memory use. No live-provider billing assumption is built into the code. API plan limits and actual archive sizes determine your operating cost.

## Local operation

1. Follow `README.md` to install dependencies, prepare historical data, evaluate a candidate, and produce `artifacts/model.joblib`.
2. Keep the model artifact and API state database on persistent storage. The defaults are `artifacts/model.joblib` and `var/api_state.sqlite3`.
3. Configure provider keys and budgets in the process environment. Leave budgets zero while working offline.
4. Use `python predict_live.py` for scheduled single-route predictions, or `python -m backend.app` for the local interface. Neither command starts an unrequested background collector.
5. Run `python -m pytest tests -q` after dependency or source changes. Keep the tested dependency lock with every trained artifact.

The Flask development server is limited to local testing. A deployment uses Gunicorn in the supplied container. The container serves the API only; host `frontend/dist` as static files or use a reverse proxy for the UI.

## Docker on a workstation or one small server

The supplied `Dockerfile` installs the CPU runtime's OpenMP library, runs as an unprivileged user, and starts one Gunicorn worker with two request threads. The Compose configuration maps the API to **localhost only**, mounts the model directory read-only, and uses a named volume for the request counter/cache. It deliberately does not package historical archives or secrets into the image.

From the repository root, after creating a real trained artifact and configuring environment values:

```bash
docker compose build
docker compose up -d
docker compose logs --tail=100 api
```

Check `http://localhost:8000/health`. Configure the frontend's `VITE_API_BASE_URL` to `http://localhost:8000` for local container use, then rebuild the UI.

For remote access, place an HTTPS reverse proxy in front, keep the backend's port private, set a strong `AEROPREDICT_API_TOKEN`, restrict `ALLOWED_ORIGINS`, and apply a small client request rate limit at the proxy. Provider secrets stay in the backend environment. The example token control is suitable for a private installation; add a real identity layer if you need public multi-user access.

Docker Compose may read a root `.env` for its own variable interpolation; Python scripts do not. The implementation did not edit or create your real `.env`. Preserve the `api-state` volume when updating containers. `docker compose down` retains named volumes; deleting the volume would erase the counters and invalidate your local spending controls. See [Docker's Compose guide](https://docs.docker.com/compose/gettingstarted/).

This container blueprint still needs to be built and tested on your Docker host. The exact Python lock was verified on Windows; Linux's native wheels and Gunicorn must be exercised by deployment CI. The model must be trained and served with compatible library versions.

## Provider failure and quota behavior

| Condition | Implemented behavior |
| --- | --- |
| Missing key or zero daily/31-day budget | Refuse network access with a configuration/budget error |
| Valid cached response | Return it without a new provider call |
| SerpApi route search | One outbound request, one-way nonstop itinerary search; one-hour cache |
| WeatherAPI forecast | One request per airport forecast query; 15-minute cache |
| Concurrent requests | SQLite `BEGIN IMMEDIATE` serializes budget reservations |
| Timeout or network failure | Count the attempt, report unavailable, apply 60-second cooldown |
| HTTP 401/403/429 | Count the attempt, report unavailable, apply one-hour cooldown |
| Invalid JSON/API error | Report unavailable and apply a cooldown |
| No flights | Return an empty list; never invent a schedule |
| Missing forecast hour or unsupported horizon | Mark that flight unavailable; never substitute tomorrow's weather with current conditions |
| Corrupt/missing model | Fail before a route search can consume budget |

The HTTP timeout is a five-second connect limit plus a 30-second read timeout. No automatic retries, redirects, pagination, paid fallbacks or subscription changes are enabled. A user or scheduler can retry after the cooldown. When a provider gives a longer outage window, wait longer rather than increasing retry traffic.

The local limits count **attempted HTTP calls**, not provider credits, and use rolling 24-hour and 31-day windows. Failed calls count conservatively. Convert your plan's actual allowances to appropriate limits. Requests made by other applications with the same key are not visible here; retain provider-side overage controls. A local budget does not guarantee no charges if a plan bills differently or other consumers use the key.

Every worker on this host shares one database. Do not deploy independently copied databases to multiple replicas or use a disposable serverless `/tmp` directory: each copy would have a fresh budget. Before scaling horizontally, replace the state store with a shared transactional counter and shared cache, such as a database transaction or atomic Redis script, and validate concurrency against that store. This repository intentionally implements the single-host option.

## Logging and monitoring

Python's standard logger reports provider name, failure class/status, validation problems, row counts, and training metrics. Provider request URLs and raw response bodies are not logged because keys appear in query parameters. Cached responses recursively remove key fields and redact literal key values that providers may echo.

Collect process logs with your operating system or container logging driver and configure rotation there. Keep provider dashboards as the source of billing truth. Monitor service latency, unavailable responses, remaining plan allowance, model age, history support, weather-match rate, MAE/RMSE, and baseline comparison. `/health` reports process liveness; `/api/model-status` reports artifact-file presence, not a guarantee of model accuracy or provider readiness.

Back up model artifacts, their reports, and API state. Stop or quiesce writers before copying the SQLite state file, or use SQLite's backup API. Never restore an old request-counter backup to reset a current billing window. Restoring older counts requires leaving API budgets disabled until consumption is reconciled with provider records.

## Retraining and learning over time

1. Add new verified BTS/weather files; keep their reporting period and export provenance. SerpApi schedules cannot supply actual arrival labels.
2. Re-run preparation with the same units and prediction horizon. Review `flights.audit.json`: a reduced match rate or a new outcome-timing assumption can change the effective training population.
3. Train into a new candidate directory, preserving the currently served model.
4. Compare the candidate with the historical-mean baseline and a previously accepted model on the same later time periods. Investigate airline/airport groups with sparse coverage and severe-delay errors. Do not deploy just because the candidate's training fit looks better.
5. When ready, refit on all outcomes known at the chosen cutoff. Keep the test report's provenance; a refitted model has not itself been independently tested by the old split.
6. Copy the approved self-contained `model.joblib` into the serving artifact directory using a temporary file on that filesystem followed by atomic replacement. Keep the previous artifact for rollback. The pipeline's own writer already follows this pattern.

For a local scheduler, set its working directory to the repository and use these commands in sequence, stopping if either exits nonzero:

```bash
python data_prep.py --flights "data/raw/bts/*.csv" --weather "data/weather/*.csv" --weather-units meteostat --horizon-hours 24 --output data/training/flights.csv
python train_model.py --input data/training/flights.csv --output artifacts/candidate --n-jobs 2
```

Windows Task Scheduler can invoke the environment's `python.exe` with these arguments. On Linux, place the sequence in your scheduler's job definition with its working directory and environment set explicitly. Run only when new archives arrive; retraining identical data every hour does not add knowledge. Prevent overlapping preparation/training jobs because their output reports share filenames. No schedule has been installed by this change.

A genuine live evaluation loop needs forecasts saved **at prediction time**, plus later independently verified arrival outcomes joined by carrier, flight number, route, and departure date/time. BTS release delays mean a historical-only deployment may have no observations from the latest 30 days; the historical feature then falls back and the response shows its support count. Retraining does not fabricate fresh outcomes. Add a verified operational outcome source only if you later choose one with a suitable cost and coverage model.

## Serverless alternative

If request volume is very low, a container-based serverless service can host inference, but it is not a drop-in deployment of this SQLite design. Store model artifacts in persistent object storage, initialize the model during instance startup, and move quota/cache state to one shared transactional service before allowing multiple instances. Native XGBoost dependencies, cold-start time, memory limits and maximum request durations need measurement. Train offline; do not train inside a request handler. Keep the current single-host setup until those additional components are justified.
