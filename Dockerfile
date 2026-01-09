# syntax=docker/dockerfile:1

FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    FASTMAIL_BASE_URL=https://api.fastmail.com

WORKDIR /app

# System packages needed for optional TCP bridge
RUN apt-get update \
    && apt-get install -y --no-install-recommends socat \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirement files first to leverage Docker layer caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY src ./src
COPY assets ./assets
COPY pytest.ini requirements.in ./
COPY docker ./docker

# Create an unprivileged user to run the service
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

ENTRYPOINT ["/app/docker/entrypoint.sh"]
