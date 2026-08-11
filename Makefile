# ═══════════════════════════════════════════════
#   زیبانو - Makefile
# ═══════════════════════════════════════════════

.PHONY: help run test migrate superuser lint format clean

# ─── Development ───
run: ## اجرای سرور توسعه
	python manage.py runserver 0.0.0.0:8000

shell: ## پوسته جنگو
	python manage.py shell_plus --ipython

# ─── Database ───
migrate: ## اعمال migration ها
	python manage.py migrate

makemigrations: ## ایجاد migration جدید
	python manage.py makemigrations

superuser: ## ایجاد superuser
	python manage.py createsuperuser

seed: ## ایجاد داده‌های اولیه
	python manage.py create_initial_data

# ─── Testing ───
test: ## اجرای همه تست‌ها
	pytest tests/ -v --tb=short

test-cov: ## اجرا با coverage
	pytest tests/ -v --cov=apps --cov-report=html --cov-report=term-missing

test-models: ## فقط تست مدل‌ها
	pytest tests/test_models.py -v

test-api: ## فقط تست API ها
	pytest tests/ -v -k "api" --tb=short

test-failed: ## فقط تست‌های ناموفق قبلی
	pytest tests/ -v --lf

# ─── Code Quality ───
lint: ## بررسی کد با ruff
	ruff check apps/ config/ shared/ tests/

lint-fix: ## رفع خودکار خطاهای ruff
	ruff check apps/ config/ shared/ tests/ --fix

format: ## فرمت کد
	ruff format apps/ config/ shared/ tests/

typecheck: ## بررسی تایپ با mypy
	mypy apps/ --ignore-missing-imports

# ─── Cleanup ───
clean: ## پاک‌سازی فایل‌های موقت
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache htmlcov .coverage

clean-db: ## حذف دیتابیس و migration ها
	rm -f db.sqlite3
	find apps -path "*/migrations/*.py" ! -name "__init__.py" -delete

# ─── Docker ───
docker-up: ## بالا آوردن docker compose
	docker-compose up -d

docker-down: ## پایین آوردن docker compose
	docker-compose down

docker-logs: ## مشاهده لاگ‌ها
	docker-compose logs -f backend

docker-test: ## اجرای تست در docker
	docker-compose exec backend pytest tests/ -v

# ─── Celery ───
celery-worker: ## اجرای Celery Worker
	celery -A config worker -l info -c 4

celery-beat: ## اجرای Celery Beat
	celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# ─── Info ───
urls: ## نمایش URL ها
	python manage.py show_urls 2>/dev/null || echo "django-extensions نصب نیست"

help: ## نمایش راهنما
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'