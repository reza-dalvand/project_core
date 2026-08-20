# ═══════════════════════════════════════════════
#   BEAU CLUB Backend Dockerfile
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

ARG DJANGO_ENV=development
COPY requirements/base.txt requirements/base.txt
COPY requirements/${DJANGO_ENV}.txt requirements/environment.txt

RUN pip install --upgrade pip && \
    pip install -r requirements/environment.txt

# ─── Stage 3: Development ───
FROM dependencies as development

COPY . .
EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ─── Stage 4: Production ───
FROM dependencies as production

COPY . .

# Collect static files
RUN DJANGO_SETTINGS_MODULE=config.settings.production \
    SECRET_KEY=build-secret-key \
    python manage.py collectstatic --noinput 2>/dev/null || true

# Create non-root user
RUN useradd -m -r appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["gunicorn", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--threads", "2", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "config.wsgi:application"]


####