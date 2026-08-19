# 🚀 دستورالعمل راه‌اندازی پروژه بیو کلاب

## پیش‌نیازها

- Docker & Docker Compose
- Node.js 18+
- Yarn یا npm

---

## ۱. بک‌اند (Django)

```bash
# رفتن به پوشه بک‌اند
cd project_core/

# کپی .env.example به .env
cp .env.example .env

# بالا آوردن سرویس‌ها
docker-compose up -d --build

# بررسی لاگ‌ها
docker-compose logs -f backend

# اجرای migration (خودکار در docker-compose انجام می‌شود)
# اگر نیاز به اجرای دستی:
docker-compose exec backend python manage.py migrate

# ایجاد داده‌های اولیه
docker-compose exec backend python manage.py create_initial_data

# ایجاد superuser
docker-compose exec backend python manage.py createsuperuser
```
