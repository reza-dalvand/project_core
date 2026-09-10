# apps/appointments/migrations/0002_add_performance_indexes.py

"""
فاز ۵: افزودن ایندکس‌های عملکردی
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="appointment",
            index=models.Index(
                fields=["date_key", "status"],
                name="apt_date_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="appointment",
            index=models.Index(
                fields=["business", "status"],
                name="apt_biz_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="appointment",
            index=models.Index(
                fields=["customer", "created_at"],
                name="apt_customer_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="appointment",
            index=models.Index(
                fields=["status", "created_at"],
                name="apt_status_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="appointment",
            index=models.Index(
                fields=["jy", "jm", "jd", "time_slot"],
                name="apt_jalali_datetime_idx",
            ),
        ),
    ]