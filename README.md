# 🚀 بیو کلاب — Backend

پلتفرم رزرو آنلاین خدمات زیبایی و سلامت

## معماری
- Django 5.1.4 + DRF + PostGIS
- Celery + Redis + PostgreSQL 16
- Docker + Nginx + Gunicorn

## Deploy
```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec backend python manage.py create_initial_data