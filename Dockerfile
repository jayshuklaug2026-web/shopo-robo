# ========================================================
# Shopo Robo — Production Multi-Stage Container Image
# ========================================================
FROM python:3.11-slim

# Environment Configuration
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SHOPO_ENV=production \
    SHOPO_DEBUG=False \
    SHOPO_HOST=0.0.0.0 \
    PORT=5000 \
    SHOPO_DB_PATH=/var/data/shopo_robo.db

WORKDIR /app

# Install system dependencies (sqlite3, curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app

# Create persistent storage directory for SQLite database
RUN mkdir -p /var/data && chmod 777 /var/data

# Declare volume for persistent data
VOLUME ["/var/data"]

EXPOSE 5000

# Container health probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://127.0.0.1:5000/healthz || exit 1

# Production WSGI startup
CMD ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]
