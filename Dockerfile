# ═══════════════════════════════════════════════
#   BEAU CLUB Backend Dockerfile — Production Only
# ═══════════════════════════════════════════════

# ─── Stage 1: Base ───
FROM python:3.12-slim-bookworm as base
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# نصب وابستگی‌های سیستم + GDAL/GEOS برای PostGIS
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libwebp-dev \
    curl \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

# ─── Stage 2: Dependencies ───
FROM base as dependencies
COPY requirements/base.txt requirements/base.txt
COPY requirements/production.txt requirements/environment.txt
RUN pip install --upgrade pip && \
    pip install -r requirements/environment.txt

# ─── Stage 3: Production ───
FROM dependencies as production

# Create non-root user BEFORE copying files
RUN useradd -m -r appuser

# Create necessary directories with correct permissions
RUN mkdir -p /app/logs /app/staticfiles /app/media /app/backups && \
    chown -R appuser:appuser /app

# Copy application code
COPY --chown=appuser:appuser . .

# Collect static files with build-time secret
RUN DJANGO_SETTINGS_MODULE=config.settings.production \
    SECRET_KEY=build-time-secret-key-not-for-production \
    python manage.py collectstatic --noinput

USER appuser

EXPOSE 8000

# ✅ حذف CMD از اینجا — docker-compose command را override می‌کند
CMD ["gunicorn", \
    "--bind", "0.0.0.0:8000", \
    "--workers", "3", \
    "--threads", "2", \
    "--timeout", "120", \
    "--access-logfile", "-", \
    "--error-logfile", "-", \
    "config.wsgi:application"]