FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt
RUN useradd --create-home --uid 10001 aeropredict
COPY aeropredict ./aeropredict
COPY backend/__init__.py backend/app.py backend/wsgi.py ./backend/
COPY data_prep.py train_model.py predict_live.py ./
RUN mkdir /app/artifacts /app/var && chown -R aeropredict:aeropredict /app
USER aeropredict
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "2", "--timeout", "90", "backend.wsgi:app"]
