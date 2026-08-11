#!/bin/bash
# ═══════════════════════════════════════════════════════════
#   زیبانو | ساخت ساختار فایل‌های اپ‌های جدید
#   فقط فایل‌های خالی — بدون کد
# ═══════════════════════════════════════════════════════════

set -e

echo "🚀 شروع ساخت اپ‌های جدید زیبانو..."
echo ""

# ─── تابع: ساخت یک اپ ───
create_app() {
  local APP_NAME="$1"
  local CONFIG_CLASS="$2"
  local VERBOSE_NAME="$3"
  local HAS_SERVICES="$4"   # yes / no

  echo "📦 ساخت اپ: apps/$APP_NAME/"

  # ── پوشه‌ها ──
  mkdir -p "apps/$APP_NAME/views"
  mkdir -p "apps/$APP_NAME/serializers"
  mkdir -p "apps/$APP_NAME/migrations"

  if [ "$HAS_SERVICES" = "yes" ]; then
    mkdir -p "apps/$APP_NAME/services"
    touch "apps/$APP_NAME/services/__init__.py"
  fi

  # ── فایل‌های خالی ──
  touch "apps/$APP_NAME/__init__.py"
  touch "apps/$APP_NAME/models.py"
  touch "apps/$APP_NAME/admin.py"
  touch "apps/$APP_NAME/views/__init__.py"
  touch "apps/$APP_NAME/serializers/__init__.py"
  touch "apps/$APP_NAME/migrations/__init__.py"

  # ── apps.py ──
  cat > "apps/$APP_NAME/apps.py" << EOF
from django.apps import AppConfig


class $CONFIG_CLASS(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.$APP_NAME'
    verbose_name = '$VERBOSE_NAME'
EOF

  # ── urls.py ──
  cat > "apps/$APP_NAME/urls.py" << EOF
from django.urls import path

app_name = '$APP_NAME'

urlpatterns = [
]
EOF

  echo "   ✅ apps/$APP_NAME/ ساخته شد"
}

# ═══════════════════════════════════════════════════════════
#   ساخت ۱۳ اپ جدید
# ═══════════════════════════════════════════════════════════

create_app "categories"     "CategoriesConfig"    "🏷️ دسته‌بندی‌ها"           "no"
create_app "locations"      "LocationsConfig"     "📍 استان و شهر"             "no"
create_app "services"       "ServicesConfig"      "💆 خدمات"                   "yes"
create_app "schedules"      "SchedulesConfig"     "🕐 زمان‌بندی"               "yes"
create_app "appointments"   "AppointmentsConfig"  "📅 نوبت‌ها"                 "yes"
create_app "portfolios"     "PortfoliosConfig"    "🖼️ نمونه‌کارها"             "no"
create_app "ads"            "AdsConfig"           "📢 آگهی‌ها"                  "no"
create_app "explore"        "ExploreConfig"       "🔍 ویترین / اکسپلور"         "no"
create_app "reminders"      "RemindersConfig"     "🔔 یادآوری تمدید"            "yes"
create_app "favorites"      "FavoritesConfig"     "❤️ علاقه‌مندی‌ها"            "no"
create_app "search"         "SearchConfig"        "🔎 جستجو"                    "yes"
create_app "support"        "SupportConfig"       "🎧 پشتیبانی"                 "no"
create_app "ads_management" "AdsManagementConfig" "📊 مدیریت تبلیغات"           "no"

echo ""

# ═══════════════════════════════════════════════════════════
#   ساخت shared/
# ═══════════════════════════════════════════════════════════
echo "📦 ساخت shared/"

mkdir -p shared/sms
mkdir -p shared/payment
mkdir -p shared/storage
mkdir -p shared/national_id

touch shared/__init__.py
touch shared/sms/__init__.py
touch shared/sms/base.py
touch shared/sms/mock.py
touch shared/sms/kavenegar.py

touch shared/payment/__init__.py
touch shared/payment/base.py
touch shared/payment/zibal.py

touch shared/storage/__init__.py
touch shared/storage/arvan.py

touch shared/national_id/__init__.py
touch shared/national_id/base.py
touch shared/national_id/mock.py
touch shared/national_id/api_ir.py

echo "   ✅ shared/ ساخته شد"
echo ""

# ═══════════════════════════════════════════════════════════
#   ساخت requirements/
# ═══════════════════════════════════════════════════════════
echo "📦 ساخت requirements/"

mkdir -p requirements
touch requirements/base.txt
touch requirements/development.txt
touch requirements/production.txt

echo "   ✅ requirements/ ساخته شد"
echo ""

# ═══════════════════════════════════════════════════════════
#   config/celery.py
# ═══════════════════════════════════════════════════════════
echo "📦 ساخت config/celery.py"
touch config/celery.py
echo "   ✅ config/celery.py ساخته شد"
echo ""

# ═══════════════════════════════════════════════════════════
#   خلاصه نهایی
# ═══════════════════════════════════════════════════════════
echo "═══════════════════════════════════════════════════════════"
echo "✅  تمام شد! ساختار نهایی:"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "apps/"
for app in categories locations services schedules appointments \
           portfolios ads explore reminders favorites search \
           support ads_management; do
  echo "├── $app/"
  echo "│   ├── __init__.py"
  echo "│   ├── apps.py"
  echo "│   ├── models.py       (خالی)"
  echo "│   ├── admin.py        (خالی)"
  echo "│   ├── urls.py         (خالی)"
  echo "│   ├── views/"
  echo "│   │   └── __init__.py"
  echo "│   ├── serializers/"
  echo "│   │   └── __init__.py"
  echo "│   └── migrations/"
  echo "│       └── __init__.py"
  if [ -d "apps/$app/services" ]; then
    echo "│   └── services/"
    echo "│       └── __init__.py"
  fi
done
echo ""
echo "shared/"
echo "├── sms/        (base, mock, kavenegar)"
echo "├── payment/    (base, zibal)"
echo "├── storage/    (arvan)"
echo "└── national_id/(base, mock, api_ir)"
echo ""
echo "requirements/"
echo "├── base.txt"
echo "├── development.txt"
echo "└── production.txt"
echo ""
echo "config/celery.py"
echo ""
echo "═══════════════════════════════════════════════════════════"
