# ═══════════════════════════════════════════════
#   BEAU CLUB Backend Dockerfile
# ═══════════════════════════════════════════════

# ─── Stage 1: Base ───
FROM python:3.12-slim as base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# نصب وابستگی‌های سیستم + GDAL/GEOS برای PostGIS
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    libwebp-dev \
    curl \
    gdal-bin \
    libgdal-dev \
    geos \
    libgeos-dev \
    libgeos++-dev \
    proj-bin \
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

RUN python manage.py collectstatic --noinput \
    --settings=config.settings.production || true

RUN useradd -m -r appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--threads", "2", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "config.wsgi:application"]