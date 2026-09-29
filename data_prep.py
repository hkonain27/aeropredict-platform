"""Command-line entry point for offline historical flight/weather preparation."""

from aeropredict.data_prep import create_prediction_pipeline, main


if __name__ == "__main__":
    raise SystemExit(main())
